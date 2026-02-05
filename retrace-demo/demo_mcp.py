#!/usr/bin/env python3
"""
MCP Server Demo - Shows how an LLM can query provenance via MCP tools
"""

import sys
import json
import time

def slow_print(text, delay=0.02):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def pause(seconds=1):
    time.sleep(seconds)

def section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")
    pause(0.3)

def show_tool_call(tool_name, params):
    """Simulate showing an MCP tool call"""
    print(f"  CLAUDE CALLS: {tool_name}")
    print(f"  PARAMS: {json.dumps(params, indent=4)}")
    pause(0.5)

def show_response(response):
    """Show the MCP response"""
    print(f"  RESPONSE:")
    print(f"  {json.dumps(response, indent=4)}")
    pause(0.8)

def main():
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#   MCP SERVER DEMO: LLM-Powered Debugging                #")
    print("#" + " " * 58 + "#")
    print("#" * 60)

    section("SCENARIO: User Asks Claude to Investigate")

    print('  USER: "Claude, I have a suspicious transaction with a fee')
    print('         of $0.23 when it should be around $230. Can you')
    print('         investigate using the Retrace recording?"')
    pause(1.5)

    slow_print("\n  CLAUDE: I'll use the Retrace MCP tools to investigate.", 0.02)
    slow_print("          Let me trace where the $0.23 came from...", 0.02)
    pause(1)

    section("STEP 1: Claude Opens the Recording")

    show_tool_call("open_trace", {
        "recording_path": "/recordings/transaction_2024_01_15"
    })

    show_response({
        "session_id": "session_1",
        "status": "opened",
        "recording": "/recordings/transaction_2024_01_15",
        "settings": {
            "argv": ["python", "process_transactions.py"],
            "python_version": "3.11.9"
        }
    })

    slow_print("\n  CLAUDE: Recording opened. Now let me search for the", 0.02)
    slow_print("          fee-related variables...", 0.02)
    pause(1)

    section("STEP 2: Claude Searches for Fee Variables")

    show_tool_call("search_variables", {
        "session_id": "session_1",
        "pattern": "fee"
    })

    show_response({
        "pattern": "fee",
        "match_count": 4,
        "matches": [
            {"variable": "base_fee", "instruction": 10, "line": 45},
            {"variable": "fee_after_tier", "instruction": 20, "line": 52},
            {"variable": "final_fee", "instruction": 30, "line": 58},
            {"variable": "final_fee_rounded", "instruction": 36, "line": 61}
        ]
    })

    slow_print("\n  CLAUDE: Found 4 fee-related variables. Let me trace", 0.02)
    slow_print("          the provenance of 'final_fee_rounded'...", 0.02)
    pause(1)

    section("STEP 3: Claude Traces Provenance")

    show_tool_call("trace_provenance", {
        "session_id": "session_1",
        "variable": "final_fee_rounded"
    })

    show_response({
        "variable": "final_fee_rounded",
        "value": 0.23,
        "instruction": 36,
        "sources": [
            {
                "variable": "final_fee",
                "value": 0.2295,
                "instruction": 30,
                "operation": "BINARY_OP (multiply)",
                "sources": [
                    {
                        "variable": "fee_after_tier",
                        "value": 0.27,
                        "instruction": 20
                    },
                    {
                        "variable": "promo_discount",
                        "value": 0.15,
                        "instruction": 28
                    }
                ]
            }
        ]
    })

    slow_print("\n  CLAUDE: I can see the calculation chain. Let me trace", 0.02)
    slow_print("          deeper to find the base fee source...", 0.02)
    pause(1)

    section("STEP 4: Claude Gets the Source Code")

    show_tool_call("get_source", {
        "session_id": "session_1",
        "filename": "process_transactions.py",
        "line": 45,
        "context": 3
    })

    show_response({
        "filename": "process_transactions.py",
        "target_line": 45,
        "lines": [
            {"line": 42, "content": "def calculate_base_fee(amount, txn_type):"},
            {"line": 43, "content": "    rate = rates.get(txn_type, 0.02)"},
            {"line": 44, "content": "    # Base fee calculation"},
            {"line": 45, "content": "    base_fee = amount * rate  # <-- HERE", "current": True},
            {"line": 46, "content": "    return base_fee"},
            {"line": 47, "content": ""}
        ]
    })

    slow_print("\n  CLAUDE: Found it! base_fee = amount * rate", 0.02)
    slow_print("          Let me check what 'amount' was...", 0.02)
    pause(1)

    section("STEP 5: Claude Finds the Root Cause")

    show_tool_call("get_provenance", {
        "session_id": "session_1",
        "variable": "amount"
    })

    show_response({
        "variable": "amount",
        "provenance": [
            {
                "variable": "amount",
                "value": 30,
                "instruction": 2,
                "line": 83,
                "file": "process_transactions.py",
                "operation": "LOAD_CONST"
            }
        ]
    })

    print("\n  " + "!" * 56)
    print("  !                                                      !")
    print("  !  ROOT CAUSE FOUND: amount = 30 (should be 30000)     !")
    print("  !                                                      !")
    print("  " + "!" * 56)

    pause(1.5)

    section("STEP 6: Claude Reports to User")

    print("  CLAUDE's RESPONSE TO USER:")
    print("  " + "-" * 50)
    print('''
  I investigated the suspicious $0.23 fee using the
  Retrace recording. Here's what I found:

  ROOT CAUSE: Data entry error
  - The transaction amount was entered as $30
  - It should have been $30,000 (missing 3 zeros)

  CALCULATION TRACE:
  1. base_fee = $30 × 0.01 = $0.30
  2. After 10% tier discount: $0.27
  3. After 15% promo discount: $0.2295
  4. Rounded: $0.23

  RECOMMENDATION:
  - Correct this transaction's amount to $30,000
  - Add input validation for unusually small amounts
  - Consider a confirmation step for amounts under $100
''')

    pause(1)

    section("THE VALUE OF MCP + RETRACE")

    print('''
  Without MCP Server:
  -------------------
  - User manually searches through logs
  - Tries to reproduce the issue
  - Adds print statements, redeploys
  - Hours of back-and-forth investigation

  With MCP Server + Claude:
  -------------------------
  - User asks Claude to investigate
  - Claude queries the recording directly
  - Full root cause analysis in seconds
  - Actionable recommendations provided

  KEY INSIGHT:
  ------------
  The MCP server lets LLMs like Claude become
  AUTOMATED DEBUGGERS that can investigate issues
  on behalf of users without manual intervention.
''')

    section("DEMO COMPLETE")

    print("  MCP Server enables LLM-powered debugging:")
    print("  - Claude can open and query recordings")
    print("  - Trace provenance programmatically")
    print("  - Find root causes automatically")
    print("  - Report findings in plain English")
    print()

if __name__ == '__main__':
    main()
