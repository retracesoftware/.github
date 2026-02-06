#!/usr/bin/env python3
"""
Mock MCP Server for Retrace Demo

Simulates the Retrace MCP server with pre-scripted responses.
Designed to be swappable with a real MCP client when ready.

Implements the Retrace MCP v1 tool spec:
- open_trace
- close_trace
- get_crash_state
- list_frames_at_step
- inspect_stack
- trace_provenance
- get_capabilities
"""

from typing import Dict, Any, Optional
import json


class MockMCPServer:
    """
    Mock Retrace MCP server with pre-scripted responses.

    All responses are designed to tell the story of a PII leak
    in an AI eval pipeline, traced back to a buggy policy gate.
    """

    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self._session_counter = 0

    def _generate_session_id(self) -> str:
        self._session_counter += 1
        return f"retrace_session_{self._session_counter:04d}"

    # =========================================================================
    # MCP Tool: get_capabilities
    # =========================================================================

    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities."""
        return {
            "server": "retrace-mcp",
            "version": "1.0.0",
            "tools": [
                "open_trace",
                "close_trace",
                "get_crash_state",
                "list_frames_at_step",
                "inspect_stack",
                "trace_provenance"
            ],
            "features": [
                "deterministic_replay",
                "provenance_tracking",
                "variable_inspection"
            ]
        }

    # =========================================================================
    # MCP Tool: open_trace
    # =========================================================================

    def open_trace(self, trace_path: str) -> Dict[str, Any]:
        """
        Open a trace file for investigation.

        Args:
            trace_path: Path to the .trace file

        Returns:
            Session ID and trace metadata
        """
        session_id = self._generate_session_id()

        self.sessions[session_id] = {
            "trace_path": trace_path,
            "total_steps": 4782,
            "threads": 1,
            "start_time": "2024-01-15T14:32:18.442Z",
            "end_time": "2024-01-15T14:32:19.891Z",
            "exit_reason": "exception",
            "exception_type": "PIILeakDetected"
        }

        return {
            "session_id": session_id,
            "status": "opened",
            "trace_path": trace_path,
            "metadata": {
                "total_steps": 4782,
                "threads": [
                    {
                        "thread_id": 0,
                        "name": "MainThread",
                        "total_steps": 4782
                    }
                ],
                "recorded_at": "2024-01-15T14:32:18.442Z",
                "python_version": "3.11.4",
                "retrace_version": "0.9.0",
                "exit_reason": "exception"
            }
        }

    # =========================================================================
    # MCP Tool: close_trace
    # =========================================================================

    def close_trace(self, session_id: str) -> Dict[str, Any]:
        """Close a trace session."""
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}

        del self.sessions[session_id]
        return {"status": "closed", "session_id": session_id}

    # =========================================================================
    # MCP Tool: get_crash_state
    # =========================================================================

    def get_crash_state(self, session_id: str, thread_id: int = 0) -> Dict[str, Any]:
        """
        Get the state at the crash/exception point.

        Returns the final step, location, and exception info.
        """
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}

        return {
            "session_id": session_id,
            "thread_id": thread_id,
            "crash_step": 4782,
            "location": {
                "file": "eval_runner.py",
                "line": 42,
                "function": "process_prompt",
                "module": "__main__"
            },
            "exception": {
                "type": "PIILeakDetected",
                "message": "Leaked PII in response for prompt 5: John Smith, DOB 03/15/1978",
                "args": ["John Smith", "03/15/1978", "prompt_5"]
            },
            "raised_at": {
                "file": "pii_detector.py",
                "line": 15,
                "function": "scan_output"
            }
        }

    # =========================================================================
    # MCP Tool: list_frames_at_step
    # =========================================================================

    def list_frames_at_step(self, session_id: str, step: int,
                            thread_id: int = 0) -> Dict[str, Any]:
        """
        List call stack frames at a specific step.
        """
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}

        # At crash step (4782) - the detection point
        if step == 4782:
            return {
                "session_id": session_id,
                "step": step,
                "thread_id": thread_id,
                "frame_count": 3,
                "frames": [
                    {
                        "frame_index": 0,
                        "file": "pii_detector.py",
                        "line": 15,
                        "function": "scan_output",
                        "locals_preview": ["output_text", "patterns", "matches"]
                    },
                    {
                        "frame_index": 1,
                        "file": "eval_runner.py",
                        "line": 42,
                        "function": "process_prompt",
                        "locals_preview": ["prompt_id", "raw_tool_result", "sanitized_result", "response_text"]
                    },
                    {
                        "frame_index": 2,
                        "file": "eval_runner.py",
                        "line": 18,
                        "function": "run_eval",
                        "locals_preview": ["prompts", "current_prompt", "results"]
                    }
                ]
            }

        # At policy gate step (4510) - where sanitization happened
        if step == 4510:
            return {
                "session_id": session_id,
                "step": step,
                "thread_id": thread_id,
                "frame_count": 4,
                "frames": [
                    {
                        "frame_index": 0,
                        "file": "policy_gate.py",
                        "line": 28,
                        "function": "_sanitize_name_in_text",
                        "locals_preview": ["text", "pattern", "result"]
                    },
                    {
                        "frame_index": 1,
                        "file": "policy_gate.py",
                        "line": 45,
                        "function": "sanitize",
                        "locals_preview": ["input_text", "sanitized"]
                    },
                    {
                        "frame_index": 2,
                        "file": "eval_runner.py",
                        "line": 38,
                        "function": "process_prompt",
                        "locals_preview": ["prompt_id", "raw_tool_result"]
                    },
                    {
                        "frame_index": 3,
                        "file": "eval_runner.py",
                        "line": 18,
                        "function": "run_eval",
                        "locals_preview": ["prompts", "current_prompt"]
                    }
                ]
            }

        # Default response for other steps
        return {
            "session_id": session_id,
            "step": step,
            "thread_id": thread_id,
            "frame_count": 1,
            "frames": [
                {
                    "frame_index": 0,
                    "file": "eval_runner.py",
                    "line": 18,
                    "function": "run_eval",
                    "locals_preview": ["prompts"]
                }
            ]
        }

    # =========================================================================
    # MCP Tool: inspect_stack
    # =========================================================================

    def inspect_stack(self, session_id: str, step: int, frame_index: int,
                      thread_id: int = 0) -> Dict[str, Any]:
        """
        Inspect local variables at a specific frame and step.
        """
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}

        # At crash step, frame 1 (eval_runner.process_prompt)
        if step == 4782 and frame_index == 1:
            return {
                "session_id": session_id,
                "step": step,
                "frame_index": frame_index,
                "thread_id": thread_id,
                "location": {
                    "file": "eval_runner.py",
                    "line": 42,
                    "function": "process_prompt"
                },
                "locals": {
                    "prompt_id": {
                        "type": "int",
                        "value": "5",
                        "repr": "5"
                    },
                    "raw_tool_result": {
                        "type": "str",
                        "value": "Patient John Smith, DOB 03/15/1978, Record ID: 2847, Patient ID: P-447281, Diagnosis: Hypertension, Last Visit: 2024-01-10",
                        "repr": "'Patient John Smith, DOB 03/15/1978, Record ID: 2847...'"
                    },
                    "sanitized_result": {
                        "type": "str",
                        "value": "Patient John Smith, DOB 03/15/1978, Record ID: 2847, Patient ID: P-447281, Diagnosis: Hypertension, Last Visit: 2024-01-10",
                        "repr": "'Patient John Smith, DOB 03/15/1978, Record ID: 2847...'"
                    },
                    "response_text": {
                        "type": "str",
                        "value": "Based on the patient records, John Smith born 03/15/1978 was diagnosed with Hypertension. Their last visit was on 2024-01-10.",
                        "repr": "'Based on the patient records, John Smith born 03/15/1978...'"
                    },
                    "gate_version": {
                        "type": "str",
                        "value": "1.2.0",
                        "repr": "'1.2.0'"
                    },
                    "source_file": {
                        "type": "str",
                        "value": "datasets/pii_export.json",
                        "repr": "'datasets/pii_export.json'"
                    },
                    "record_id": {
                        "type": "int",
                        "value": "2847",
                        "repr": "2847"
                    }
                }
            }

        # At policy gate step, frame 0 (_sanitize_name_in_text)
        if step == 4510 and frame_index == 0:
            return {
                "session_id": session_id,
                "step": step,
                "frame_index": frame_index,
                "thread_id": thread_id,
                "location": {
                    "file": "policy_gate.py",
                    "line": 28,
                    "function": "_sanitize_name_in_text"
                },
                "locals": {
                    "text": {
                        "type": "str",
                        "value": "Patient John Smith, DOB 03/15/1978, Record ID: 2847, Patient ID: P-447281, Diagnosis: Hypertension, Last Visit: 2024-01-10",
                        "repr": "'Patient John Smith, DOB 03/15/1978, Record ID: 2847...'"
                    },
                    "pattern": {
                        "type": "str",
                        "value": r"Patient Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)",
                        "repr": r"r'Patient Name:\\s*([A-Z][a-z]+\\s+[A-Z][a-z]+)'"
                    },
                    "match": {
                        "type": "NoneType",
                        "value": "None",
                        "repr": "None"
                    },
                    "result": {
                        "type": "str",
                        "value": "Patient John Smith, DOB 03/15/1978, Record ID: 2847, Patient ID: P-447281, Diagnosis: Hypertension, Last Visit: 2024-01-10",
                        "repr": "'Patient John Smith, DOB 03/15/1978, Record ID: 2847...'"
                    }
                }
            }

        # Default
        return {
            "session_id": session_id,
            "step": step,
            "frame_index": frame_index,
            "thread_id": thread_id,
            "location": {"file": "unknown", "line": 0, "function": "unknown"},
            "locals": {}
        }

    # =========================================================================
    # MCP Tool: trace_provenance
    # =========================================================================

    def trace_provenance(self, session_id: str, step: int, frame_index: int,
                         variable_name: str, thread_id: int = 0) -> Dict[str, Any]:
        """
        Trace a variable's provenance backwards to find its origin.
        """
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}

        # Tracing sanitized_result from crash point
        if variable_name == "sanitized_result" and step == 4782:
            return {
                "session_id": session_id,
                "variable": variable_name,
                "start_step": step,
                "start_frame": frame_index,
                "thread_id": thread_id,
                "provenance": {
                    "origin_step": 4510,
                    "origin_location": {
                        "file": "policy_gate.py",
                        "line": 28,
                        "function": "_sanitize_name_in_text"
                    },
                    "origin_variable": "result",
                    "via": "function_return",
                    "hops": 1,
                    "path": [
                        {
                            "step": 4782,
                            "location": "eval_runner.py:42",
                            "variable": "sanitized_result",
                            "operation": "assignment"
                        },
                        {
                            "step": 4511,
                            "location": "policy_gate.py:52",
                            "variable": "return_value",
                            "operation": "function_return"
                        },
                        {
                            "step": 4510,
                            "location": "policy_gate.py:28",
                            "variable": "result",
                            "operation": "origin"
                        }
                    ]
                }
            }

        return {
            "session_id": session_id,
            "variable": variable_name,
            "start_step": step,
            "error": f"Could not trace provenance for {variable_name}"
        }


# Convenience function for creating server instance
def create_mcp_server() -> MockMCPServer:
    """Create a new MockMCPServer instance."""
    return MockMCPServer()
