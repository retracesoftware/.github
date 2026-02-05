#!/usr/bin/env python3
"""
AI-Driven Investigation Demo

Simulates an AI coding assistant (like Cursor, Copilot, etc.)
autonomously investigating a PII leak using Retrace MCP tools.

This is the "this is what your product could do" moment.
"""

import sys
import time
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investigation.mcp_client import RetraceMCPClient

# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
MAGENTA = "\033[95m"


def type_text(text: str, delay: float = 0.008, newline: bool = True):
    """Simulate typing effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    if newline:
        print()


def ai_think(text: str):
    """Show AI thinking."""
    print(f"{DIM}   {text}{RESET}")
    time.sleep(0.3)


def ai_speak(text: str, typing: bool = True):
    """Show AI speaking."""
    if typing:
        type_text(f"{CYAN}   {text}{RESET}", delay=0.012)
    else:
        print(f"{CYAN}   {text}{RESET}")


def tool_call(name: str, args: str = ""):
    """Show MCP tool call."""
    print()
    print(f"{MAGENTA}   > mcp.{name}({args}){RESET}")
    time.sleep(0.4)


def tool_result(text: str):
    """Show tool result (abbreviated)."""
    print(f"{DIM}   {text}{RESET}")
    time.sleep(0.2)


def run_ai_investigation():
    """Run the AI-driven investigation demo."""

    # Initialize MCP client
    client = RetraceMCPClient()
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    trace_path = os.path.join(script_dir, "eval_run.trace")

    print()
    print(f"{BOLD}   Cursor AI Assistant{RESET}")
    print(f"{DIM}   ─────────────────────────────────────{RESET}")
    print()

    time.sleep(0.5)

    # AI starts investigating
    ai_speak("I see your eval crashed with a PII leak. Let me investigate using Retrace.")
    print()
    time.sleep(0.3)

    # Step 1: Open trace
    ai_think("Opening the trace file...")
    tool_call("open_trace", '"eval_run.trace"')
    result = client.open_trace(trace_path)
    tool_result(f"session: {result['session_id']}, steps: {result['total_steps']}, crash_step: {result['crash_step']}")

    session_id = result['session_id']

    # Step 2: Get crash state
    ai_think("Finding where the leak was detected...")
    tool_call("get_crash_state", f'"{session_id}"')
    result = client.get_crash_state(session_id)
    tool_result(f"crash at step {result['crash_step']}: LEAK_DETECTED")

    # Step 3: Inspect stack
    ai_think("Extracting the leaked values...")
    tool_call("inspect_stack", f'"{session_id}"')
    result = client.inspect_stack(session_id)
    locals_data = result['frames'][0]['locals']
    tool_result(f'leaked_value: "{locals_data.get("leaked_value", "John Smith")}"')
    tool_result(f'leaked_dob: "{locals_data.get("leaked_dob", "03/15/1978")}"')

    # Step 4: Trace provenance
    ai_think("Tracing back to the root cause...")
    tool_call("trace_provenance", f'"{session_id}", "leaked_value"')
    result = client.trace_provenance(session_id, 15, 0, "leaked_value")
    bug = result['root_cause_location']
    print()

    # AI delivers the verdict
    print(f"{GREEN}   {BOLD}Found it!{RESET}")
    print()
    ai_speak(f"The bug is in {BOLD}{bug['file']}:{bug['line']}{RESET}{CYAN} in `{bug['function']}`", typing=False)
    print()
    ai_speak(f"The regex only matches 'Patient Name:' format but your data", typing=False)
    ai_speak(f"uses 'Patient John Smith, DOB...' format. That's why PII leaked.", typing=False)
    print()

    print(f"{YELLOW}   {BOLD}Suggested fix:{RESET}")
    print(f"{DIM}   Update the pattern to also match: Patient <Name>, DOB{RESET}")
    print()

    time.sleep(0.3)

    print(f"{DIM}   ─────────────────────────────────────{RESET}")
    print(f"{BOLD}   Investigation complete in 4 MCP calls{RESET}")
    print()


if __name__ == "__main__":
    run_ai_investigation()
