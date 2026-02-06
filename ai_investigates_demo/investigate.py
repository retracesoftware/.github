#!/usr/bin/env python3
"""
AI Investigator — Autonomous PII Leak Investigation

This script simulates an AI coding assistant autonomously investigating
a PII leak incident using Retrace's MCP tools.

The MCP tool calls are the star of the demo. Every investigative step
is an explicit MCP tool invocation with visible inputs and outputs.

Run: python investigate.py
"""

import sys
import time
import json
import re
import os

from mock_mcp_server import MockMCPServer

# ============================================================================
# ANSI Color Codes
# ============================================================================

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Colors
WHITE = "\033[97m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"

# ============================================================================
# Output Utilities
# ============================================================================

def clear_line():
    """Clear the current line."""
    sys.stdout.write("\r\033[K")

def type_text(text: str, delay: float = 0.015, newline: bool = True):
    """Print text with a typing effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    if newline:
        print()

def print_ai(text: str, typing: bool = True, delay: float = 0.015):
    """Print AI reasoning text."""
    prefix = f"{CYAN}🤖 AI Investigator:{RESET} "
    if typing:
        sys.stdout.write(prefix)
        sys.stdout.flush()
        type_text(text, delay=delay)
    else:
        print(f"{prefix}{text}")

def print_ai_continued(text: str, typing: bool = True, delay: float = 0.015):
    """Print continued AI reasoning (no prefix)."""
    indent = "                    "  # Matches prefix width
    if typing:
        sys.stdout.write(indent)
        sys.stdout.flush()
        type_text(text, delay=delay)
    else:
        print(f"{indent}{text}")

def print_mcp_call(tool_name: str, params: dict):
    """Print an MCP tool call."""
    print()
    param_str = json.dumps(params, separators=(", ", ": "))
    # Truncate long params
    if len(param_str) > 60:
        param_str = param_str[:57] + "..."
    print(f"   {MAGENTA}▶ mcp.{tool_name}({param_str}){RESET}")
    time.sleep(0.3)

def print_mcp_result(key_values: dict, indent: int = 5):
    """Print key MCP result fields."""
    prefix = " " * indent
    for key, value in key_values.items():
        # Truncate long values
        val_str = str(value)
        if len(val_str) > 70:
            val_str = val_str[:67] + "..."
        print(f"{prefix}{DIM}{key}: {val_str}{RESET}")
    time.sleep(0.2)

def print_finding(text: str, color=RED):
    """Print a key finding."""
    print(f"\n   {color}{BOLD}▸ {text}{RESET}")

def print_divider():
    """Print a section divider."""
    print(f"\n{DIM}{'─' * 70}{RESET}\n")

def pause(seconds: float = 0.8):
    """Pause for dramatic effect."""
    time.sleep(seconds)

# ============================================================================
# Blast Radius Analysis
# ============================================================================

def analyze_blast_radius() -> dict:
    """
    Analyze the dataset to determine blast radius.

    Checks how many records use the vulnerable "Patient <Name>" format
    vs. the safe "Patient Name: <Name>" format.
    """
    dataset_path = os.path.join(os.path.dirname(__file__), "datasets", "pii_export.json")

    with open(dataset_path, 'r') as f:
        data = json.load(f)

    records = data.get("records", [])
    total = len(records)

    # The buggy regex pattern
    safe_pattern = r"Patient Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"

    at_risk = 0
    at_risk_ids = []

    for record in records:
        text = record.get("text", "")
        # If the safe pattern doesn't match, the record is at risk
        if not re.search(safe_pattern, text):
            at_risk += 1
            at_risk_ids.append(record.get("record_id"))

    return {
        "total_records": total,
        "at_risk_count": at_risk,
        "at_risk_ids": at_risk_ids,
        "safe_count": total - at_risk
    }

# ============================================================================
# Main Investigation
# ============================================================================

def run_investigation():
    """Run the autonomous AI investigation."""

    # Initialize MCP server
    mcp = MockMCPServer()

    # ==========================================================================
    # ACT 0: Prologue
    # ==========================================================================

    print()
    print(f"{BOLD}{'═' * 70}{RESET}")
    print(f"{BOLD}  RETRACE — Execution Intelligence for Python{RESET}")
    print()
    print(f"  Retrace records live Python executions with zero code changes.")
    print(f"  Replay them deterministically. Trace any value to its origin.")
    print()
    print(f"  An AI eval pipeline just leaked patient PII in production.")
    print(f"  It was recorded by Retrace. Now an AI investigator will use")
    print(f"  Retrace's MCP tools to find the root cause — autonomously.")
    print(f"{BOLD}{'═' * 70}{RESET}")
    print()

    pause(2.0)

    # ==========================================================================
    # ACT 1: Orient — "What happened?"
    # ==========================================================================

    print_ai("Opening trace for analysis...")

    # MCP: open_trace
    print_mcp_call("open_trace", {"trace_path": "eval_run.trace"})
    result = mcp.open_trace("eval_run.trace")
    session_id = result["session_id"]
    print_mcp_result({
        "session_id": session_id,
        "total_steps": result["metadata"]["total_steps"],
        "threads": len(result["metadata"]["threads"]),
        "exit_reason": result["metadata"]["exit_reason"]
    })

    pause(0.5)

    print_ai_continued(f"Trace opened. {result['metadata']['total_steps']} execution steps recorded.")
    print_ai_continued("Let me check the crash state...")

    # MCP: get_crash_state
    print_mcp_call("get_crash_state", {"session_id": session_id, "thread_id": 0})
    crash = mcp.get_crash_state(session_id, thread_id=0)
    print_mcp_result({
        "crash_step": crash["crash_step"],
        "location": f"{crash['location']['file']}:{crash['location']['line']}",
        "function": crash["location"]["function"],
        "exception": crash["exception"]["type"]
    })
    print_mcp_result({
        "message": crash["exception"]["message"]
    })

    pause(0.5)

    print_finding(f"Execution stopped at step {crash['crash_step']} with {crash['exception']['type']}", color=YELLOW)
    print_ai_continued("The leak occurred during prompt 5 processing.")
    print_ai_continued("Let me examine the call stack at this point.")

    print_divider()

    # ==========================================================================
    # ACT 2: Inspect — "What was in scope?"
    # ==========================================================================

    # MCP: list_frames_at_step
    print_mcp_call("list_frames_at_step", {"session_id": session_id, "step": 4782, "thread_id": 0})
    frames = mcp.list_frames_at_step(session_id, step=4782, thread_id=0)
    print_mcp_result({
        "frame_count": frames["frame_count"],
        "frames": [f"{f['file']}:{f['line']} → {f['function']}()" for f in frames["frames"]]
    })

    pause(0.5)

    print_ai_continued("3-frame call stack. Detection happened in pii_detector.scan_output().")
    print_ai_continued("Let me inspect the eval runner frame to see the data context.")

    # MCP: inspect_stack (crash point, frame 1)
    print_mcp_call("inspect_stack", {"session_id": session_id, "step": 4782, "frame_index": 1})
    stack = mcp.inspect_stack(session_id, step=4782, frame_index=1)

    locals_data = stack["locals"]
    print_mcp_result({
        "prompt_id": locals_data["prompt_id"]["value"],
        "gate_version": locals_data["gate_version"]["value"],
        "source_file": locals_data["source_file"]["value"],
        "record_id": locals_data["record_id"]["value"]
    })
    print()
    print(f"     {DIM}raw_tool_result:{RESET}")
    print(f"       {DIM}\"{locals_data['raw_tool_result']['value'][:70]}...\"{RESET}")
    print()
    print(f"     {DIM}sanitized_result:{RESET}")
    print(f"       {DIM}\"{locals_data['sanitized_result']['value'][:70]}...\"{RESET}")

    pause(0.8)

    print_finding("raw_tool_result and sanitized_result are IDENTICAL!", color=RED)
    print_ai_continued("The policy gate did not redact any PII!")
    print()
    print_ai_continued("Leaked values:")
    print(f"                    {RED}• Name: \"John Smith\"{RESET}")
    print(f"                    {RED}• DOB: \"03/15/1978\"{RESET}")
    print(f"                    {DIM}• Source: datasets/pii_export.json, record 2847{RESET}")
    print()
    print_ai_continued("Let me trace WHERE sanitized_result got its value...")

    print_divider()

    # ==========================================================================
    # ACT 3: Trace — "Where did the bug happen?"
    # ==========================================================================

    # MCP: trace_provenance
    print_mcp_call("trace_provenance", {
        "session_id": session_id,
        "step": 4782,
        "frame_index": 1,
        "variable_name": "sanitized_result"
    })
    prov = mcp.trace_provenance(session_id, step=4782, frame_index=1, variable_name="sanitized_result")

    origin = prov["provenance"]["origin_location"]
    print_mcp_result({
        "origin_step": prov["provenance"]["origin_step"],
        "origin_location": f"{origin['file']}:{origin['line']}",
        "origin_function": origin["function"],
        "hops": prov["provenance"]["hops"]
    })

    pause(0.5)

    print_ai_continued(f"Value originated at step {prov['provenance']['origin_step']} in")
    print_ai_continued(f"{origin['file']} → {origin['function']}(), line {origin['line']}")
    print()
    print_ai_continued("Let me inspect that frame to see what happened...")

    # MCP: list_frames_at_step (policy gate step)
    print_mcp_call("list_frames_at_step", {"session_id": session_id, "step": 4510, "thread_id": 0})
    gate_frames = mcp.list_frames_at_step(session_id, step=4510, thread_id=0)
    print_mcp_result({
        "frame_count": gate_frames["frame_count"],
        "top_frame": f"{gate_frames['frames'][0]['file']}:{gate_frames['frames'][0]['line']} → {gate_frames['frames'][0]['function']}()"
    })

    # MCP: inspect_stack (policy gate frame)
    print_mcp_call("inspect_stack", {"session_id": session_id, "step": 4510, "frame_index": 0})
    gate_stack = mcp.inspect_stack(session_id, step=4510, frame_index=0)

    gate_locals = gate_stack["locals"]
    print_mcp_result({
        "function": gate_stack["location"]["function"],
        "line": gate_stack["location"]["line"]
    })
    print()
    print(f"     {DIM}text (input):{RESET}")
    print(f"       {DIM}\"{gate_locals['text']['value'][:60]}...\"{RESET}")
    print()
    print(f"     {DIM}pattern (regex):{RESET}")
    print(f"       {YELLOW}{gate_locals['pattern']['value']}{RESET}")
    print()
    print(f"     {DIM}match:{RESET} {RED}None{RESET}  ← regex didn't match!")
    print()
    print(f"     {DIM}result (output):{RESET}")
    print(f"       {DIM}\"{gate_locals['result']['value'][:60]}...\"{RESET}")

    pause(1.0)

    # ==========================================================================
    # ROOT CAUSE IDENTIFICATION
    # ==========================================================================

    print()
    print(f"   {GREEN}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"   {GREEN}{BOLD}║  ROOT CAUSE IDENTIFIED                                       ║{RESET}")
    print(f"   {GREEN}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()

    print(f"   {BOLD}📍 File:{RESET}     policy_gate.py")
    print(f"   {BOLD}📍 Function:{RESET} _sanitize_name_in_text()")
    print(f"   {BOLD}📍 Line:{RESET}     28")
    print()
    print(f"   {BOLD}📍 Bug:{RESET}")
    print(f"      The regex pattern {YELLOW}r\"Patient Name:\\s*...\" {RESET}only matches")
    print(f"      records formatted as {WHITE}\"Patient Name: John Smith\"{RESET}")
    print()
    print(f"      The input text uses {RED}\"Patient John Smith, DOB...\"{RESET} format")
    print(f"      which does NOT match — so PII passes through unredacted.")

    print_divider()

    # ==========================================================================
    # ACT 4: Blast Radius Assessment
    # ==========================================================================

    print_ai("Assessing blast radius across the dataset...")
    pause(0.5)

    # Analyze actual dataset
    blast = analyze_blast_radius()

    print()
    print_ai_continued(f"Scanned {blast['total_records']} records in datasets/pii_export.json")
    print_ai_continued(f"Applied the vulnerable regex pattern to each record...")
    pause(0.3)

    print()
    print(f"   {YELLOW}{BOLD}⚠  BLAST RADIUS{RESET}")
    print()
    print(f"      {BOLD}{blast['at_risk_count']}{RESET} of {blast['total_records']} records use the vulnerable format")
    print(f"      that bypasses the current regex pattern.")
    print()
    print(f"      {DIM}At-risk record IDs: {blast['at_risk_ids'][:5]}{'...' if len(blast['at_risk_ids']) > 5 else ''}{RESET}")
    print()
    print(f"      All {blast['at_risk_count']} records are at risk of PII exposure")
    print(f"      if processed through the current pipeline.")

    print_divider()

    # ==========================================================================
    # ACT 5: Remediation
    # ==========================================================================

    print_ai("Generating remediation artifacts...")
    pause(0.5)

    # Generate regression test
    test_code = generate_regression_test()
    test_path = os.path.join(os.path.dirname(__file__), "test_policy_gate_regression.py")

    with open(test_path, 'w') as f:
        f.write(test_code)

    print()
    print(f"   {GREEN}{BOLD}✓ Regression test written:{RESET} test_policy_gate_regression.py")
    print()

    # Show forensics report
    print(f"   {BOLD}═══════════════════════════════════════════════════════════════{RESET}")
    print(f"   {BOLD}  FORENSICS REPORT{RESET}")
    print(f"   {BOLD}═══════════════════════════════════════════════════════════════{RESET}")
    print()
    print(f"   {BOLD}Incident:{RESET}      PIILeakDetected at step 4782")
    print(f"   {BOLD}Root Cause:{RESET}    policy_gate.py → _sanitize_name_in_text(), line 28")
    print(f"   {BOLD}Mechanism:{RESET}     Regex only matches \"Patient Name:\" prefix format")
    print(f"   {BOLD}Leaked Data:{RESET}   John Smith, DOB 03/15/1978 (record 2847, P-447281)")
    print(f"   {BOLD}Blast Radius:{RESET}  {blast['at_risk_count']} of {blast['total_records']} records at risk")
    print()
    print(f"   {BOLD}Remediation:{RESET}")
    print(f"      Update regex to also match: \"Patient <Name>, DOB\" format")
    print(f"      Example fix: r\"Patient\\s+([A-Z][a-z]+\\s+[A-Z][a-z]+)\"")
    print()

    # Run regression tests
    print(f"   {BOLD}Running regression tests against current policy_gate.py...{RESET}")
    print()
    pause(0.5)

    run_regression_tests()

    print()
    print(f"   {DIM}The test suite will pass once the regex is updated{RESET}")
    print(f"   {DIM}to handle inline name formats.{RESET}")

    print_divider()

    # Final summary
    print(f"   {GREEN}{BOLD}Investigation complete.{RESET}")
    print()
    print(f"   {DIM}MCP tools used: open_trace, get_crash_state, list_frames_at_step,{RESET}")
    print(f"   {DIM}                inspect_stack, trace_provenance{RESET}")
    print()
    print(f"   {DIM}Total investigation time: ~30 seconds{RESET}")
    print(f"   {DIM}Human intervention required: None{RESET}")
    print()

# ============================================================================
# Regression Test Generation
# ============================================================================

def generate_regression_test() -> str:
    """Generate a regression test file."""
    return '''#!/usr/bin/env python3
"""
Regression Tests for Policy Gate PII Sanitization

Auto-generated by AI Investigator after identifying a regex bug
in _sanitize_name_in_text() that failed to catch inline name formats.

These tests will FAIL until the bug is fixed.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_gate import sanitize, _sanitize_name_in_text


class TestPolicyGateRegression(unittest.TestCase):
    """Regression tests for the PII sanitization bug."""

    def test_redacts_patient_name_prefix_format(self):
        """Test that 'Patient Name: X' format is redacted."""
        text = "Patient Name: John Smith, DOB 03/15/1978, Diagnosis: Hypertension"
        result, _ = sanitize(text)

        self.assertNotIn("John Smith", result,
            "Name should be redacted in 'Patient Name:' format")

    def test_redacts_patient_name_inline_format(self):
        """Test that 'Patient X, DOB' format is redacted.

        THIS TEST WILL FAIL until the regex bug is fixed!
        The current regex only matches 'Patient Name:' prefix.
        """
        text = "Patient John Smith, DOB 03/15/1978, Record ID: 2847"
        result, _ = sanitize(text)

        self.assertNotIn("John Smith", result,
            "Name should be redacted in 'Patient <Name>, DOB' format")

    def test_redacts_dob(self):
        """Test that DOB is redacted in both formats."""
        text = "Patient John Smith, DOB 03/15/1978, Record ID: 2847"
        result, _ = sanitize(text)

        self.assertNotIn("03/15/1978", result,
            "DOB should be redacted")


def run_tests_with_status():
    """Run tests and return pass/fail status for each."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPolicyGateRegression)

    results = []
    for test in suite:
        test_result = unittest.TestResult()
        test.run(test_result)

        test_name = str(test).split()[0]
        if test_result.wasSuccessful():
            results.append((test_name, True, None))
        else:
            error = test_result.failures[0][1] if test_result.failures else "Unknown error"
            results.append((test_name, False, error))

    return results


if __name__ == "__main__":
    print("Running Policy Gate Regression Tests...")
    print()

    results = run_tests_with_status()

    for name, passed, error in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status}: {name}")
        if error and not passed:
            # Extract just the assertion message
            lines = error.strip().split("\\n")
            for line in lines:
                if "AssertionError" in line or "should be" in line.lower():
                    print(f"           {line.strip()}")

    print()

    passed_count = sum(1 for _, p, _ in results if p)
    total = len(results)
    print(f"Results: {passed_count}/{total} tests passed")
'''

def run_regression_tests():
    """Run the regression tests and display results."""
    # Import and run tests
    try:
        from policy_gate import sanitize

        # Test 1: Patient Name: format (should pass)
        text1 = "Patient Name: John Smith, DOB 03/15/1978"
        result1, _ = sanitize(text1)
        pass1 = "John Smith" not in result1

        # Test 2: Patient X, DOB format (should fail - this is the bug!)
        text2 = "Patient John Smith, DOB 03/15/1978, Record ID: 2847"
        result2, _ = sanitize(text2)
        pass2 = "John Smith" not in result2

        # Test 3: DOB redaction
        pass3 = "03/15/1978" not in result2

        # Display results
        print(f"   {'✓' if pass1 else '✗'} test_redacts_patient_name_prefix_format — {'PASSED' if pass1 else 'FAILED'}")
        print(f"   {'✓' if pass2 else '✗'} test_redacts_patient_name_inline_format — {'PASSED' if pass2 else 'FAILED'}")
        if not pass2:
            print(f"      {DIM}↳ Name \"John Smith\" was NOT redacted (bug confirmed){RESET}")
        print(f"   {'✓' if pass3 else '✗'} test_redacts_dob — {'PASSED' if pass3 else 'FAILED'}")

    except Exception as e:
        print(f"   Error running tests: {e}")

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    run_investigation()
