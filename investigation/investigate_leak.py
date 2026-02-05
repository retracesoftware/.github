#!/usr/bin/env python3
"""
Leak Investigation Tool

Uses Retrace MCP server to investigate PII leaks in eval outputs.
Traces provenance backwards to identify root cause and blast radius.
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import RetraceMCPClient
from visualization import (
    print_header,
    print_section,
    format_crash_state,
    format_stack_inspection,
    format_provenance_chain,
    format_root_cause,
    format_blast_radius,
    format_remediation
)
from regression_test_gen import generate_regression_test


class LeakInvestigator:
    """
    Investigates PII leaks using Retrace MCP tools.
    
    Workflow:
    1. Open trace file
    2. Get crash state
    3. Inspect stack to extract breadcrumb locals
    4. Trace provenance to find bug location
    5. Generate report and regression test
    """
    
    def __init__(self, trace_path: str):
        self.trace_path = trace_path
        self.mcp = RetraceMCPClient()
        self.session_id: Optional[str] = None
        
        # Investigation results
        self.crash_state: Optional[Dict] = None
        self.stack_info: Optional[Dict] = None
        self.provenance_info: Optional[Dict] = None
        self.breadcrumbs: Dict[str, Any] = {}
    
    def open_trace(self) -> bool:
        """Step 1: Open the trace file."""
        print_section("Step 1: Opening trace file")
        
        result = self.mcp.open_trace(self.trace_path)
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
            return False
        
        self.session_id = result["session_id"]
        print(f"   ✓ Session opened: {self.session_id}")
        print(f"   ✓ Total steps: {result['total_steps']}")
        print(f"   ✓ Crash step: {result['crash_step']}")
        
        return True
    
    def get_crash_state(self) -> bool:
        """Step 2: Get the crash state."""
        print_section("Step 2: Getting crash state")
        
        if not self.session_id:
            print("   ❌ No session open")
            return False
        
        result = self.mcp.get_crash_state(self.session_id)
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
            return False
        
        self.crash_state = result
        
        crash_event = result.get("crash_event", {})
        print(f"   ✓ Crash step: {result['crash_step']}")
        print(f"   ✓ Operation: {crash_event.get('operation', 'unknown')}")
        print(f"   ✓ Location: {crash_event.get('location', 'unknown')}")
        
        return True
    
    def inspect_stack(self) -> bool:
        """Step 3: Inspect stack to extract breadcrumb locals."""
        print_section("Step 3: Inspecting stack frames")
        
        if not self.session_id or not self.crash_state:
            print("   ❌ Missing session or crash state")
            return False
        
        crash_step = self.crash_state.get("crash_step")
        result = self.mcp.inspect_stack(self.session_id, thread_id=0, step=crash_step)
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
            return False
        
        self.stack_info = result
        
        # Extract breadcrumb locals from the crash frame
        frames = result.get("frames", [])
        if frames:
            crash_frame = frames[0]
            locals_data = crash_frame.get("locals", {})
            
            self.breadcrumbs = {
                "leaked_value": locals_data.get("leaked_value"),
                "leaked_dob": locals_data.get("leaked_dob"),
                "leaked_text": locals_data.get("leaked_text"),
                "leak_source": locals_data.get("leak_source"),
                "gate_version": locals_data.get("gate_version"),
                "blast_radius_count": locals_data.get("blast_radius_count")
            }
            
            print(f"   ✓ Found {len(frames)} stack frames")
            print(f"   ✓ Crash frame: {crash_frame.get('function')}() at {crash_frame.get('file')}:{crash_frame.get('line')}")
            print(f"   ✓ Extracted breadcrumb locals:")
            print(f"      - leaked_value: {self.breadcrumbs.get('leaked_value')}")
            print(f"      - leaked_dob: {self.breadcrumbs.get('leaked_dob')}")
            print(f"      - gate_version: {self.breadcrumbs.get('gate_version')}")
        
        return True
    
    def trace_provenance(self) -> bool:
        """Step 4: Trace provenance to find the bug location."""
        print_section("Step 4: Tracing provenance (1 hop)")
        
        if not self.session_id or not self.crash_state:
            print("   ❌ Missing session or crash state")
            return False
        
        crash_step = self.crash_state.get("crash_step")
        
        # Trace provenance of the leaked_tool_payload
        result = self.mcp.trace_provenance(
            self.session_id,
            step=crash_step,
            frame_index=0,
            variable_name="leaked_tool_payload"
        )
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
            return False
        
        self.provenance_info = result
        
        # Show the provenance chain
        chain = result.get("provenance_chain", [])
        print(f"   ✓ Found {len(chain)} provenance events")
        
        for event in chain[:3]:  # Show first 3
            print(f"      [{event.get('step')}] {event.get('operation')} @ {event.get('location')}")
        
        # Show the root cause location
        root_cause = result.get("root_cause_location", {})
        if root_cause:
            print(f"   ✓ Root cause identified:")
            print(f"      File: {root_cause.get('file')}")
            print(f"      Function: {root_cause.get('function')}()")
            print(f"      Line: {root_cause.get('line')}")
        
        return True
    
    def get_source_context(self) -> Dict[str, Any]:
        """Get source code context for the bug location."""
        if not self.provenance_info:
            return {}
        
        root_cause = self.provenance_info.get("root_cause_location", {})
        if not root_cause:
            return {}
        
        return self.mcp.get_source(
            self.session_id,
            file=root_cause.get("file", ""),
            line=root_cause.get("line", 0)
        )
    
    def generate_report(self) -> str:
        """Generate the full investigation report."""
        report_parts = []
        
        # Header
        report_parts.append(format_crash_state(self.crash_state))
        report_parts.append("")
        
        # Stack inspection
        report_parts.append(format_stack_inspection(self.stack_info, self.breadcrumbs))
        report_parts.append("")
        
        # Provenance chain
        report_parts.append(format_provenance_chain(self.provenance_info))
        report_parts.append("")
        
        # Root cause
        source_context = self.get_source_context()
        report_parts.append(format_root_cause(self.provenance_info, source_context))
        report_parts.append("")
        
        # Blast radius
        report_parts.append(format_blast_radius(self.breadcrumbs))
        report_parts.append("")
        
        # Remediation
        report_parts.append(format_remediation(self.provenance_info, self.breadcrumbs))
        
        return "\n".join(report_parts)
    
    def run_investigation(self) -> bool:
        """Run the complete investigation workflow."""
        print_header("Retrace Leak Investigation")
        print()
        print(f"🔍 Investigating leak in: {self.trace_path}")
        print()
        
        # Step 1: Open trace
        if not self.open_trace():
            return False
        print()
        
        # Step 2: Get crash state
        if not self.get_crash_state():
            return False
        print()
        
        # Step 3: Inspect stack
        if not self.inspect_stack():
            return False
        print()
        
        # Step 4: Trace provenance
        if not self.trace_provenance():
            return False
        print()
        
        # Step 5: Generate and print report
        print_section("Step 5: Generating forensics report")
        print()
        
        report = self.generate_report()
        print(report)
        
        # Step 6: Generate regression test
        print()
        print_section("Step 6: Generating regression test")
        
        test_path = generate_regression_test(self.provenance_info, self.breadcrumbs)
        print(f"   ✓ Regression test written to: {test_path}")
        
        # Close session
        self.mcp.close_trace(self.session_id)
        
        return True


def main():
    # Find trace file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    trace_path = os.path.join(script_dir, "..", "eval_run.trace")
    
    if not os.path.exists(trace_path):
        print(f"❌ Trace file not found: {trace_path}")
        print("   Run the eval pipeline first: python eval_pipeline/run_eval.py")
        sys.exit(1)
    
    investigator = LeakInvestigator(trace_path)
    
    success = investigator.run_investigation()
    
    print()
    if success:
        print("=" * 60)
        print("✅ Investigation complete!")
        print("=" * 60)
    else:
        print("❌ Investigation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
