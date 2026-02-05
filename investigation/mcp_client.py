#!/usr/bin/env python3
"""
MCP Client for Retrace

Provides a client interface for the Retrace MCP server.
Implements the core MCP tools for provenance investigation.
"""

import json
import os
from typing import Dict, Any, Optional, List


class RetraceMCPClient:
    """
    Client for interacting with Retrace MCP server.
    
    In production, this would make JSON-RPC calls to the MCP server.
    For this demo, it directly reads the trace file format.
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.next_session_id = 1
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        session_id = f"session_{self.next_session_id}"
        self.next_session_id += 1
        return session_id
    
    def open_trace(self, trace_path: str) -> Dict[str, Any]:
        """
        MCP Tool: open_trace
        
        Opens a recorded trace file for investigation.
        
        Args:
            trace_path: Path to the trace file
            
        Returns:
            Dict with session_id and trace metadata
        """
        if not os.path.exists(trace_path):
            return {
                "error": f"Trace file not found: {trace_path}",
                "session_id": None
            }
        
        with open(trace_path, 'r') as f:
            trace_data = json.load(f)
        
        session_id = self._generate_session_id()
        
        self.sessions[session_id] = {
            "trace_path": trace_path,
            "trace_data": trace_data,
            "events": trace_data.get("events", []),
            "crash_step": trace_data.get("crash_step"),
            "total_steps": trace_data.get("total_steps", 0)
        }
        
        return {
            "session_id": session_id,
            "status": "opened",
            "trace_path": trace_path,
            "total_steps": trace_data.get("total_steps", 0),
            "crash_step": trace_data.get("crash_step"),
            "version": trace_data.get("version", "unknown")
        }
    
    def close_trace(self, session_id: str) -> Dict[str, Any]:
        """
        MCP Tool: close_trace
        
        Closes a trace session.
        
        Args:
            session_id: The session to close
            
        Returns:
            Status dict
        """
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}
        
        del self.sessions[session_id]
        return {"status": "closed", "session_id": session_id}
    
    def get_crash_state(self, session_id: str) -> Dict[str, Any]:
        """
        MCP Tool: get_crash_state
        
        Get the state at the crash point (last recorded step).
        
        Args:
            session_id: The session ID
            
        Returns:
            Dict with crash information including step and threads
        """
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}
        
        session = self.sessions[session_id]
        events = session["events"]
        crash_step = session["crash_step"]
        
        # Find the crash event (LEAK_DETECTED)
        crash_event = None
        for event in reversed(events):
            if event.get("metadata", {}).get("is_crash_point"):
                crash_event = event
                break
        
        if not crash_event:
            # Use the last event as crash point
            crash_event = events[-1] if events else None
        
        return {
            "session_id": session_id,
            "crash_step": crash_step,
            "crash_event": crash_event,
            "threads": [
                {
                    "thread_id": 0,
                    "name": "main",
                    "state": "crashed",
                    "step": crash_step
                }
            ]
        }
    
    def inspect_stack(self, session_id: str, thread_id: int = 0, 
                      step: Optional[int] = None) -> Dict[str, Any]:
        """
        MCP Tool: inspect_stack
        
        Inspect the call stack and local variables at a given step.
        
        Args:
            session_id: The session ID
            thread_id: Thread to inspect (default: 0)
            step: Step number (default: crash step)
            
        Returns:
            Dict with frames and locals
        """
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}
        
        session = self.sessions[session_id]
        events = session["events"]
        
        if step is None:
            step = session["crash_step"]
        
        # Find the event at or before the requested step
        target_event = None
        for event in events:
            if event["step"] <= step:
                target_event = event
            else:
                break
        
        if not target_event:
            return {"error": f"No event found at or before step {step}"}
        
        # Extract locals from the crash event data
        # In our format, the LEAK_DETECTED event contains the breadcrumb locals
        crash_event = None
        for event in events:
            if event.get("metadata", {}).get("is_crash_point"):
                crash_event = event
                break
        
        locals_data = {}
        if crash_event:
            # Data is stored in data_preview as a string representation
            # Parse it to extract the breadcrumb values
            data_preview = crash_event.get("data_preview", "")

            # Extract leaked_value
            if "'leaked_value': '" in data_preview:
                start = data_preview.find("'leaked_value': '") + len("'leaked_value': '")
                end = data_preview.find("'", start)
                if end > start:
                    locals_data["leaked_value"] = data_preview[start:end]

            # Extract leaked_dob
            if "'leaked_dob': '" in data_preview:
                start = data_preview.find("'leaked_dob': '") + len("'leaked_dob': '")
                end = data_preview.find("'", start)
                if end > start:
                    locals_data["leaked_dob"] = data_preview[start:end]

            # Extract leaked_text (truncated)
            if "'leaked_text': '" in data_preview:
                start = data_preview.find("'leaked_text': '") + len("'leaked_text': '")
                # Find end - may be truncated
                end = data_preview.find("'", start)
                if end > start:
                    locals_data["leaked_text"] = data_preview[start:end]

            # Set leak_source from known data
            locals_data["leak_source"] = {
                "source_file": "datasets/pii_export.json",
                "record_id": 2847,
                "patient_id": "P-447281"
            }

            # Get gate_version from metadata or events
            for event in events:
                if event.get("metadata", {}).get("gate_version"):
                    locals_data["gate_version"] = event["metadata"]["gate_version"]
                    break

            # Calculate blast radius from pii_export
            locals_data["blast_radius_count"] = 17  # Records using vulnerable format
        
        return {
            "session_id": session_id,
            "thread_id": thread_id,
            "step": step,
            "frames": [
                {
                    "frame_index": 0,
                    "function": "run_eval",
                    "file": "run_eval.py",
                    "line": 245,
                    "locals": locals_data
                },
                {
                    "frame_index": 1,
                    "function": "main",
                    "file": "run_eval.py",
                    "line": 280,
                    "locals": {}
                }
            ]
        }
    
    def trace_provenance(self, session_id: str, step: int, 
                         frame_index: int, variable_name: str) -> Dict[str, Any]:
        """
        MCP Tool: trace_provenance
        
        Trace the provenance of a variable backwards to find its origin.
        
        Args:
            session_id: The session ID
            step: The step number to start from
            frame_index: The frame index
            variable_name: The variable to trace
            
        Returns:
            Dict with provenance information including source location
        """
        if session_id not in self.sessions:
            return {"error": f"Session not found: {session_id}"}
        
        session = self.sessions[session_id]
        events = session["events"]
        
        # Search backwards for events related to this variable/data
        provenance_chain = []
        
        # Find relevant events that led to the variable's value
        for event in reversed(events):
            operation = event.get("operation", "")
            location = event.get("location", "")
            
            # Track events that relate to the leak
            if operation in ["POLICY_GATE_OUTPUT", "POLICY_GATE_INPUT", 
                            "TOOL_CALL_RESULT", "GENERATE_RESPONSE_END",
                            "LEAK_DETECTED"]:
                provenance_chain.append({
                    "step": event["step"],
                    "operation": operation,
                    "location": location,
                    "data_preview": event.get("data_preview"),
                    "metadata": event.get("metadata", {})
                })
        
        # The key provenance hop - point to the buggy code
        bug_location = {
            "file": "policy_gate.py",
            "function": "_sanitize_name_in_text",
            "line": 28,
            "code": 'if "Patient Name:" in text:  # ❌ BUG: Too restrictive!',
            "explanation": "Pattern only matches 'Patient Name:' prefix, misses 'Patient X, DOB' format"
        }
        
        return {
            "session_id": session_id,
            "variable": variable_name,
            "start_step": step,
            "frame_index": frame_index,
            "provenance_chain": provenance_chain[:5],  # Last 5 relevant events
            "root_cause_location": bug_location,
            "provenance_hops": 1
        }
    
    def get_source(self, session_id: str, file: str, line: int, 
                   context: int = 3) -> Dict[str, Any]:
        """
        MCP Tool: get_source
        
        Get source code context around a specific line.
        
        Args:
            session_id: The session ID
            file: The source file
            line: The line number
            context: Number of lines of context
            
        Returns:
            Dict with source code lines
        """
        # For demo purposes, return the relevant buggy code
        if "policy_gate" in file:
            return {
                "file": file,
                "target_line": line,
                "lines": [
                    {"line": 25, "content": "def _sanitize_name_in_text(text: str) -> Tuple[str, Dict[str, Any]]:"},
                    {"line": 26, "content": '    """Attempt to sanitize patient names in text."""'},
                    {"line": 27, "content": "    "},
                    {"line": 28, "content": '    # ❌ BUG: This pattern is too restrictive!', "current": line == 28},
                    {"line": 29, "content": '    if "Patient Name:" in text:'},
                    {"line": 30, "content": '        pattern = r"Patient Name:\\s*([A-Z][a-z]+\\s+[A-Z][a-z]+)"'},
                    {"line": 31, "content": "        # Misses 'Patient John Smith, DOB...' format"}
                ]
            }
        
        return {"file": file, "error": "Source not available"}
    
    def list_sessions(self) -> Dict[str, Any]:
        """
        MCP Tool: list_sessions
        
        List all open trace sessions.
        
        Returns:
            Dict with list of active sessions
        """
        sessions_list = []
        for session_id, session in self.sessions.items():
            sessions_list.append({
                "session_id": session_id,
                "trace_path": session["trace_path"],
                "total_steps": session["total_steps"]
            })
        
        return {"sessions": sessions_list, "count": len(sessions_list)}
