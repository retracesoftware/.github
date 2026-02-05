#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for Retrace Interpreter.

Exposes the provenance interpreter API via MCP for LLM tool integration.

Usage:
    python mcp_server.py

The server communicates via JSON-RPC over stdin/stdout.
"""

import sys
import os
import json
import traceback
from typing import Any, Dict, List, Optional
from pathlib import Path

# Add this directory to path
_module_dir = os.path.dirname(os.path.abspath(__file__))
if _module_dir not in sys.path:
    sys.path.insert(0, _module_dir)

# Add parent for retrace_provenance
_parent_dir = os.path.dirname(_module_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


class RetraceSession:
    """Manages an active retrace debugging session."""

    def __init__(self, recording_path: str):
        self.recording_path = Path(recording_path)
        self.session = None
        self.current_instruction = 0
        self.provenance_tracker = None
        self.is_running = False
        self.result = None
        self.frames_at_step = {}  # Cache of frame info at instruction counts

    def open(self):
        """Open the recording and set up replay."""
        from retrace_provenance import ProvenanceSession

        self.session = ProvenanceSession(self.recording_path)
        self.session.load()
        self.session.setup_replay()
        return {
            'status': 'opened',
            'recording': str(self.recording_path),
            'settings': {
                'argv': self.session.settings.get('argv', []),
                'cwd': self.session.settings.get('cwd', ''),
                'python_version': self.session.settings.get('python_version', ''),
            }
        }

    def close(self):
        """Close the session and clean up."""
        if self.session:
            self.session.cleanup()
            self.session = None
        return {'status': 'closed'}

    def run_to_instruction(self, target_instruction: int):
        """Run execution up to a specific instruction count."""
        import retraceinterpreter
        from retracesoftware.run import run_with_retrace

        if not self.session:
            raise RuntimeError("No session open. Call open_trace first.")

        captured_frames = []
        captured_state = {}

        def capture_callback(state):
            nonlocal captured_frames, captured_state
            self.current_instruction = state.counter

            # Capture frame information
            if state.frame:
                frame_info = {
                    'filename': state.frame.f_code.co_filename,
                    'function': state.frame.f_code.co_name,
                    'lineno': state.frame.f_lineno,
                    'locals': {k: repr(v)[:100] for k, v in state.frame.f_locals.items()},
                }
                captured_frames.append(frame_info)

            # Capture provenance
            if state.provenance:
                self.provenance_tracker = state.provenance

            captured_state = {
                'instruction': state.counter,
                'frame_counter': state.frame_counter,
            }

            if state.counter >= target_instruction:
                return None  # Stop
            return target_instruction  # Continue to target

        def target():
            run_with_retrace(
                self.session.system,
                self.session.settings['argv'],
                self.session.settings.get('trace_shutdown', False)
            )

        try:
            self.result = retraceinterpreter.run(
                target=target,
                callback=capture_callback,
                use_subinterpreter=False,
                track_provenance=True,
                callback_at=1
            )

            # Handle tuple return when provenance tracking is enabled
            if isinstance(self.result, tuple):
                self.result, self.provenance_tracker = self.result

        except Exception as e:
            captured_state['error'] = str(e)
            captured_state['traceback'] = traceback.format_exc()

        self.frames_at_step[target_instruction] = captured_frames

        return {
            'stopped_at': self.current_instruction,
            'target_instruction': target_instruction,
            'frame_count': len(captured_frames),
            'state': captured_state,
        }

    def get_frames_at_step(self, instruction: int) -> List[Dict]:
        """Get call stack frames at a specific instruction."""
        return self.frames_at_step.get(instruction, [])

    def get_provenance(self, variable_name: Optional[str] = None) -> Dict:
        """Get provenance information."""
        if not self.provenance_tracker:
            return {'error': 'No provenance data available. Run with track_provenance=True.'}

        if variable_name:
            # Find provenance for specific variable
            all_prov = self.provenance_tracker.get_all_provenance()
            matches = []
            for (fid, var), prov in all_prov.items():
                if var == variable_name:
                    matches.append({
                        'variable': var,
                        'instruction': prov.instruction_counter,
                        'line': prov.lineno,
                        'file': prov.filename,
                        'operation': prov.opname,
                        'sources': [s.variable_name for s in prov.sources],
                    })
            return {'variable': variable_name, 'provenance': matches}
        else:
            # Return all provenance
            history = self.provenance_tracker.get_history()
            return {
                'total_events': len(history),
                'recent': [
                    {
                        'variable': p.variable_name,
                        'instruction': p.instruction_counter,
                        'line': p.lineno,
                        'operation': p.opname,
                    }
                    for p in history[-20:]  # Last 20 events
                ]
            }

    def trace_value_origin(self, variable_name: str) -> Dict:
        """Trace the origin of a value recursively."""
        if not self.provenance_tracker:
            return {'error': 'No provenance data available.'}

        all_prov = self.provenance_tracker.get_all_provenance()
        for (fid, var), prov in all_prov.items():
            if var == variable_name:
                return self.provenance_tracker.trace_value_origin(prov) or {}

        return {'error': f'Variable {variable_name!r} not found in provenance data.'}

    def get_source(self, filename: str, line: int, context: int = 5) -> Dict:
        """Get source code around a specific line."""
        try:
            filepath = Path(filename)
            if not filepath.is_absolute():
                # Try relative to recording's cwd
                if self.session and self.session.settings:
                    filepath = Path(self.session.settings.get('cwd', '')) / filename

            if not filepath.exists():
                return {'error': f'File not found: {filename}'}

            with open(filepath, 'r') as f:
                lines = f.readlines()

            start = max(0, line - context - 1)
            end = min(len(lines), line + context)

            source_lines = []
            for i in range(start, end):
                source_lines.append({
                    'line': i + 1,
                    'content': lines[i].rstrip(),
                    'current': (i + 1) == line
                })

            return {
                'filename': str(filepath),
                'target_line': line,
                'lines': source_lines
            }
        except Exception as e:
            return {'error': str(e)}

    def search_variables(self, pattern: str) -> List[Dict]:
        """Search for variables matching a pattern."""
        if not self.provenance_tracker:
            return []

        import re
        regex = re.compile(pattern, re.IGNORECASE)

        matches = []
        for (fid, var), prov in self.provenance_tracker.get_all_provenance().items():
            if regex.search(var):
                matches.append({
                    'variable': var,
                    'instruction': prov.instruction_counter,
                    'line': prov.lineno,
                    'file': prov.filename,
                    'operation': prov.opname,
                })

        return matches

    def get_execution_summary(self) -> Dict:
        """Get a summary of the execution state."""
        summary = {
            'recording': str(self.recording_path),
            'current_instruction': self.current_instruction,
            'has_provenance': self.provenance_tracker is not None,
        }

        if self.session and self.session.settings:
            summary['settings'] = {
                'argv': self.session.settings.get('argv', []),
                'cwd': self.session.settings.get('cwd', ''),
                'python_version': self.session.settings.get('python_version', ''),
            }

        if self.provenance_tracker:
            all_prov = self.provenance_tracker.get_all_provenance()
            history = self.provenance_tracker.get_history()
            summary['provenance'] = {
                'tracked_variables': len(all_prov),
                'total_events': len(history),
            }

        return summary


class MCPServer:
    """MCP Server for Retrace Interpreter."""

    def __init__(self):
        self.sessions: Dict[str, RetraceSession] = {}
        self.next_session_id = 1

    def get_capabilities(self) -> Dict:
        """Return server capabilities."""
        return {
            'name': 'retrace-interpreter',
            'version': '0.1.0',
            'tools': [
                {
                    'name': 'open_trace',
                    'description': 'Open a retrace recording for analysis',
                    'parameters': {
                        'recording_path': {
                            'type': 'string',
                            'description': 'Path to the recording directory',
                            'required': True,
                        }
                    }
                },
                {
                    'name': 'close_trace',
                    'description': 'Close an open trace session',
                    'parameters': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Session ID from open_trace',
                            'required': True,
                        }
                    }
                },
                {
                    'name': 'run_to_instruction',
                    'description': 'Run execution to a specific instruction count',
                    'parameters': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Session ID',
                            'required': True,
                        },
                        'instruction': {
                            'type': 'integer',
                            'description': 'Target instruction count to stop at',
                            'required': True,
                        }
                    }
                },
                {
                    'name': 'list_frames_at_step',
                    'description': 'Get call stack frames at a specific instruction',
                    'parameters': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Session ID',
                            'required': True,
                        },
                        'instruction': {
                            'type': 'integer',
                            'description': 'Instruction count',
                            'required': True,
                        }
                    }
                },
                {
                    'name': 'get_provenance',
                    'description': 'Get provenance information for tracked values',
                    'parameters': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Session ID',
                            'required': True,
                        },
                        'variable': {
                            'type': 'string',
                            'description': 'Optional variable name to query',
                            'required': False,
                        }
                    }
                },
                {
                    'name': 'trace_provenance',
                    'description': 'Trace the origin of a value recursively',
                    'parameters': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Session ID',
                            'required': True,
                        },
                        'variable': {
                            'type': 'string',
                            'description': 'Variable name to trace',
                            'required': True,
                        }
                    }
                },
                {
                    'name': 'get_source',
                    'description': 'Get source code around a specific line',
                    'parameters': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Session ID',
                            'required': True,
                        },
                        'filename': {
                            'type': 'string',
                            'description': 'Source file path',
                            'required': True,
                        },
                        'line': {
                            'type': 'integer',
                            'description': 'Line number to center on',
                            'required': True,
                        },
                        'context': {
                            'type': 'integer',
                            'description': 'Number of lines of context (default: 5)',
                            'required': False,
                        }
                    }
                },
                {
                    'name': 'search_variables',
                    'description': 'Search for variables by name pattern (regex)',
                    'parameters': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Session ID',
                            'required': True,
                        },
                        'pattern': {
                            'type': 'string',
                            'description': 'Regex pattern to match variable names',
                            'required': True,
                        }
                    }
                },
                {
                    'name': 'get_execution_summary',
                    'description': 'Get a summary of the execution state',
                    'parameters': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Session ID',
                            'required': True,
                        }
                    }
                },
                {
                    'name': 'list_sessions',
                    'description': 'List all open sessions',
                    'parameters': {}
                },
            ]
        }

    def handle_tool_call(self, tool_name: str, params: Dict) -> Dict:
        """Handle a tool call."""
        try:
            if tool_name == 'open_trace':
                return self._open_trace(params['recording_path'])

            elif tool_name == 'close_trace':
                return self._close_trace(params['session_id'])

            elif tool_name == 'run_to_instruction':
                return self._run_to_instruction(
                    params['session_id'],
                    params['instruction']
                )

            elif tool_name == 'list_frames_at_step':
                return self._list_frames(
                    params['session_id'],
                    params['instruction']
                )

            elif tool_name == 'get_provenance':
                return self._get_provenance(
                    params['session_id'],
                    params.get('variable')
                )

            elif tool_name == 'trace_provenance':
                return self._trace_provenance(
                    params['session_id'],
                    params['variable']
                )

            elif tool_name == 'get_source':
                return self._get_source(
                    params['session_id'],
                    params['filename'],
                    params['line'],
                    params.get('context', 5)
                )

            elif tool_name == 'search_variables':
                return self._search_variables(
                    params['session_id'],
                    params['pattern']
                )

            elif tool_name == 'get_execution_summary':
                return self._get_execution_summary(params['session_id'])

            elif tool_name == 'list_sessions':
                return self._list_sessions()

            else:
                return {'error': f'Unknown tool: {tool_name}'}

        except Exception as e:
            return {
                'error': str(e),
                'traceback': traceback.format_exc()
            }

    def _open_trace(self, recording_path: str) -> Dict:
        """Open a trace recording."""
        session_id = f"session_{self.next_session_id}"
        self.next_session_id += 1

        session = RetraceSession(recording_path)
        result = session.open()

        self.sessions[session_id] = session

        return {
            'session_id': session_id,
            **result
        }

    def _close_trace(self, session_id: str) -> Dict:
        """Close a trace session."""
        if session_id not in self.sessions:
            return {'error': f'Unknown session: {session_id}'}

        session = self.sessions.pop(session_id)
        return session.close()

    def _run_to_instruction(self, session_id: str, instruction: int) -> Dict:
        """Run to a specific instruction."""
        if session_id not in self.sessions:
            return {'error': f'Unknown session: {session_id}'}

        return self.sessions[session_id].run_to_instruction(instruction)

    def _list_frames(self, session_id: str, instruction: int) -> Dict:
        """List frames at instruction."""
        if session_id not in self.sessions:
            return {'error': f'Unknown session: {session_id}'}

        frames = self.sessions[session_id].get_frames_at_step(instruction)
        return {
            'instruction': instruction,
            'frame_count': len(frames),
            'frames': frames
        }

    def _get_provenance(self, session_id: str, variable: Optional[str]) -> Dict:
        """Get provenance information."""
        if session_id not in self.sessions:
            return {'error': f'Unknown session: {session_id}'}

        return self.sessions[session_id].get_provenance(variable)

    def _trace_provenance(self, session_id: str, variable: str) -> Dict:
        """Trace value origin."""
        if session_id not in self.sessions:
            return {'error': f'Unknown session: {session_id}'}

        return self.sessions[session_id].trace_value_origin(variable)

    def _get_source(self, session_id: str, filename: str, line: int, context: int) -> Dict:
        """Get source code."""
        if session_id not in self.sessions:
            return {'error': f'Unknown session: {session_id}'}

        return self.sessions[session_id].get_source(filename, line, context)

    def _search_variables(self, session_id: str, pattern: str) -> Dict:
        """Search variables by pattern."""
        if session_id not in self.sessions:
            return {'error': f'Unknown session: {session_id}'}

        matches = self.sessions[session_id].search_variables(pattern)
        return {
            'pattern': pattern,
            'match_count': len(matches),
            'matches': matches
        }

    def _get_execution_summary(self, session_id: str) -> Dict:
        """Get execution summary."""
        if session_id not in self.sessions:
            return {'error': f'Unknown session: {session_id}'}

        return self.sessions[session_id].get_execution_summary()

    def _list_sessions(self) -> Dict:
        """List all open sessions."""
        sessions = []
        for session_id, session in self.sessions.items():
            sessions.append({
                'session_id': session_id,
                'recording': str(session.recording_path),
                'current_instruction': session.current_instruction,
                'is_running': session.is_running,
            })
        return {
            'session_count': len(sessions),
            'sessions': sessions
        }


def handle_jsonrpc_request(server: MCPServer, request: Dict) -> Dict:
    """Handle a JSON-RPC 2.0 request."""
    request_id = request.get('id')
    method = request.get('method', '')
    params = request.get('params', {})

    try:
        if method == 'initialize':
            result = server.get_capabilities()
        elif method == 'tools/list':
            result = {'tools': server.get_capabilities()['tools']}
        elif method == 'tools/call':
            tool_name = params.get('name', '')
            tool_params = params.get('arguments', {})
            result = server.handle_tool_call(tool_name, tool_params)
        else:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32601, 'message': f'Method not found: {method}'}
            }

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result
        }

    except Exception as e:
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {'code': -32000, 'message': str(e)}
        }


def run_stdio_server():
    """Run the MCP server using stdio transport."""
    server = MCPServer()

    # Print capabilities on startup (for discovery)
    print(json.dumps({
        'jsonrpc': '2.0',
        'method': 'ready',
        'params': server.get_capabilities()
    }), file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = handle_jsonrpc_request(server, request)
            print(json.dumps(response))
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            error_response = {
                'jsonrpc': '2.0',
                'id': None,
                'error': {'code': -32700, 'message': f'Parse error: {e}'}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Retrace MCP Server')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--recording', type=str, help='Recording path for test mode')
    args = parser.parse_args()

    if args.test:
        # Test mode - demonstrate API usage
        server = MCPServer()
        print("=== MCP Server Test Mode ===")
        print("\nCapabilities:")
        caps = server.get_capabilities()
        print(f"  Name: {caps['name']}")
        print(f"  Version: {caps['version']}")
        print(f"  Tools: {[t['name'] for t in caps['tools']]}")

        if args.recording:
            print(f"\nOpening recording: {args.recording}")
            result = server.handle_tool_call('open_trace', {'recording_path': args.recording})
            print(f"  Result: {result}")

            if 'session_id' in result:
                session_id = result['session_id']

                print(f"\nRunning to instruction 100...")
                result = server.handle_tool_call('run_to_instruction', {
                    'session_id': session_id,
                    'instruction': 100
                })
                print(f"  Stopped at: {result.get('stopped_at')}")

                print(f"\nGetting provenance...")
                result = server.handle_tool_call('get_provenance', {
                    'session_id': session_id
                })
                print(f"  Total events: {result.get('total_events', 0)}")

                print(f"\nClosing session...")
                result = server.handle_tool_call('close_trace', {
                    'session_id': session_id
                })
                print(f"  Result: {result}")
    else:
        # Normal mode - run stdio server
        run_stdio_server()


if __name__ == '__main__':
    main()
