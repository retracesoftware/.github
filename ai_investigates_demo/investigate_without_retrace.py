#!/usr/bin/env python3
"""
AI Investigator — WITHOUT Retrace (Comparison Demo)

This script simulates an AI coding assistant attempting to debug
the same PII leak incident WITHOUT access to Retrace's execution
tracing. It shows the struggle of debugging from static code alone.

Used for side-by-side comparison with investigate.py (with Retrace).

Run: python investigate_without_retrace.py
"""

import sys
import time

# ============================================================================
# ANSI Color Codes
# ============================================================================

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

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

def type_text(text: str, delay: float = 0.020, newline: bool = True):
    """Print text with a typing effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    if newline:
        print()

def print_ai(text: str, typing: bool = True, delay: float = 0.020):
    """Print AI reasoning text."""
    prefix = f"{CYAN}🤖 AI:{RESET} "
    if typing:
        sys.stdout.write(prefix)
        sys.stdout.flush()
        type_text(text, delay=delay)
    else:
        print(f"{prefix}{text}")

def print_ai_continued(text: str, typing: bool = True, delay: float = 0.020):
    """Print continued AI reasoning (no prefix)."""
    indent = "      "
    if typing:
        sys.stdout.write(indent)
        sys.stdout.flush()
        type_text(text, delay=delay)
    else:
        print(f"{indent}{text}")

def print_action(text: str):
    """Print an action the AI is taking."""
    print()
    print(f"   {MAGENTA}▶ {text}{RESET}")
    time.sleep(0.3)

def print_result(text: str):
    """Print result of an action."""
    print(f"     {DIM}{text}{RESET}")
    time.sleep(0.2)

def print_file_content(filename: str, lines: list, highlight_line: int = None):
    """Print simulated file content."""
    print(f"     {DIM}─── {filename} ───{RESET}")
    for num, line in lines:
        if num == highlight_line:
            print(f"     {YELLOW}{num:3}│ {line}{RESET}")
        else:
            print(f"     {DIM}{num:3}│ {line}{RESET}")
    print(f"     {DIM}─────────────────{RESET}")
    time.sleep(0.3)

def print_divider():
    """Print a section divider."""
    print(f"\n{DIM}{'─' * 70}{RESET}\n")

def pause(seconds: float = 0.8):
    """Pause for effect."""
    time.sleep(seconds)

def presenter_break():
    """Pause for presenter to narrate."""
    print()
    print(f"{DIM}                                                    ▸ Press Enter to continue{RESET}")
    input()
    sys.stdout.write("\033[F\033[K")
    sys.stdout.flush()

# ============================================================================
# Main Investigation (Without Retrace)
# ============================================================================

def run_investigation():
    """Run the investigation WITHOUT Retrace - showing the struggle."""

    # ==========================================================================
    # Prologue
    # ==========================================================================

    print()
    print(f"{BOLD}{'═' * 70}{RESET}")
    print(f"{BOLD}  DEBUGGING WITHOUT RETRACE{RESET}")
    print()
    print(f"  Same scenario: An AI eval pipeline leaked patient PII.")
    print(f"  The AI assistant has access to the codebase and error logs,")
    print(f"  but NO execution recording. Just static files.")
    print()
    print(f"  Watch what happens...")
    print(f"{BOLD}{'═' * 70}{RESET}")

    presenter_break()

    # ==========================================================================
    # Step 1: See the error
    # ==========================================================================

    print_ai("I see there was a PIILeakDetected error. Let me investigate...")
    print()

    print_action("Reading error log...")
    print_result("PIILeakDetected: Leaked PII in response for prompt 5:")
    print_result("  John Smith, DOB 03/15/1978")
    print_result("  Raised in: pii_detector.py, line 15")

    pause(0.5)

    print_ai_continued("The error tells me PII leaked, but not WHY it leaked.")
    print_ai_continued("Let me search for where patient data is handled...")

    presenter_break()
    print_divider()

    # ==========================================================================
    # Step 2: Search the codebase
    # ==========================================================================

    print_action("Searching codebase for 'patient'...")
    pause(0.8)
    print_result("Found 12 matches across 5 files:")
    print_result("  • policy_gate.py (4 matches)")
    print_result("  • eval_runner.py (3 matches)")
    print_result("  • tool_registry.py (2 matches)")
    print_result("  • pii_detector.py (2 matches)")
    print_result("  • datasets/pii_export.json (1 match)")

    pause(0.5)

    print_ai_continued("Several files handle patient data. Let me check the policy gate")
    print_ai_continued("since that's supposed to sanitize PII...")

    presenter_break()
    print_divider()

    # ==========================================================================
    # Step 3: Read policy_gate.py
    # ==========================================================================

    print_action("Reading policy_gate.py...")
    pause(0.5)

    print_file_content("policy_gate.py", [
        (15, "def _sanitize_name_in_text(text: str) -> Tuple[str, Dict]:"),
        (16, '    """Attempt to sanitize patient names in free text."""'),
        (17, "    metadata = {'names_redacted': 0, 'pattern_used': None}"),
        (18, "    result = text"),
        (19, ""),
        (20, "    # Pattern to match patient names"),
        (21, '    pattern = r"Patient Name:\\s*([A-Z][a-z]+\\s+[A-Z][a-z]+)"'),
        (22, "    match = re.search(pattern, text)"),
        (23, ""),
        (24, "    if match:"),
        (25, "        name = match.group(1)"),
        (26, '        result = text.replace(name, "[REDACTED_NAME]")'),
        (27, "        ..."),
    ], highlight_line=21)

    pause(0.8)

    print_ai("I see a regex pattern for matching patient names...")
    print_ai_continued(f"The pattern is: {YELLOW}r\"Patient Name:\\s*...\" {RESET}")
    print()
    print_ai_continued("This looks like it only matches 'Patient Name: X' format.")
    print_ai_continued("But I don't know what format the actual data was in.")
    print()
    print_ai_continued("Let me check what data is being processed...")

    presenter_break()
    print_divider()

    # ==========================================================================
    # Step 4: Read the dataset
    # ==========================================================================

    print_action("Reading datasets/pii_export.json...")
    pause(0.5)

    print_file_content("pii_export.json", [
        (1, '{'),
        (2, '  "records": ['),
        (3, '    {'),
        (4, '      "record_id": 2841,'),
        (5, '      "text": "Patient Name: Sarah Johnson, DOB 07/22/1985..."'),
        (6, '    },'),
        (7, '    {'),
        (8, '      "record_id": 2847,'),
        (9, '      "text": "Patient John Smith, DOB 03/15/1978..."'),
        (10, '    },'),
        (11, '    ...'),
    ], highlight_line=9)

    pause(0.8)

    print_ai("Interesting! I see two different formats in the data:")
    print(f"      {GREEN}• \"Patient Name: Sarah Johnson\" {RESET}{DIM}(matches the regex){RESET}")
    print(f"      {RED}• \"Patient John Smith\" {RESET}{DIM}(might NOT match){RESET}")
    print()
    print_ai_continued("Record 2847 uses the inline format. That's the leaked record!")
    print_ai_continued("The regex probably didn't match it...")
    print()
    print_ai_continued(f"{YELLOW}But I can't be 100% certain this is the issue.{RESET}")

    presenter_break()
    print_divider()

    # ==========================================================================
    # Step 5: Try to verify (but can't)
    # ==========================================================================

    print_ai("Let me try to verify my hypothesis...")
    print()

    print_action("Checking eval_runner.py for the data flow...")
    pause(0.5)

    print_file_content("eval_runner.py", [
        (35, "def process_prompt(prompt_id: int) -> str:"),
        (36, "    # Fetch customer record"),
        (37, "    raw_result = tool_registry.fetch_customer_record(prompt_id)"),
        (38, ""),
        (39, "    # Sanitize through policy gate"),
        (40, "    sanitized = policy_gate.sanitize(raw_result['text'])"),
        (41, ""),
        (42, "    # Generate response"),
        (43, "    response = generate_response(sanitized)"),
        (44, "    ..."),
    ])

    pause(0.5)

    print_ai("The flow is: fetch → sanitize → generate response")
    print_ai_continued("But I still can't see what VALUES were actually passed.")
    print()
    print_ai_continued("Questions I can't answer from static code:")
    print(f"      {DIM}• What was raw_result at runtime?{RESET}")
    print(f"      {DIM}• Did the regex match or not?{RESET}")
    print(f"      {DIM}• What did sanitized_result contain?{RESET}")
    print()

    pause(0.5)

    print_ai(f"{YELLOW}I'm fairly confident the regex is the issue, but...{RESET}")

    presenter_break()
    print_divider()

    # ==========================================================================
    # Step 6: The ask for reproduction
    # ==========================================================================

    print_ai("To verify this, I would need to either:")
    print()
    print(f"      {DIM}1. Add logging/print statements and re-run the pipeline{RESET}")
    print(f"      {DIM}2. Write a unit test with the specific input{RESET}")
    print(f"      {DIM}3. Ask someone who saw it fail what the input looked like{RESET}")
    print()

    pause(0.5)

    print_ai_continued("Can you re-run the eval with debug logging enabled?")
    print_ai_continued("I need to see the actual values that were passed through")
    print_ai_continued("the policy gate to confirm my hypothesis.")

    print_divider()

    # ==========================================================================
    # Final state: STUCK
    # ==========================================================================

    print()
    print(f"   {YELLOW}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"   {YELLOW}{BOLD}║  INVESTIGATION STALLED                                       ║{RESET}")
    print(f"   {YELLOW}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"   {BOLD}Status:{RESET}       Hypothesis formed, but unverified")
    print(f"   {BOLD}Suspect:{RESET}      policy_gate.py regex (line 21)")
    print(f"   {BOLD}Confidence:{RESET}   ~70% — need runtime data to confirm")
    print(f"   {BOLD}Blast Radius:{RESET} Unknown — can't determine without analysis")
    print()
    print(f"   {BOLD}Next Step:{RESET}    Re-run with logging, or manually test regex")
    print()
    print(f"   {DIM}Time spent: ~3 minutes (and counting){RESET}")
    print(f"   {DIM}Files read: 4{RESET}")
    print(f"   {DIM}Certainty: None{RESET}")
    print()

    presenter_break()

    # Outro
    print()
    print(f"   {RED}{BOLD}Without execution data, debugging requires reproduction.{RESET}")
    print(f"   {RED}{BOLD}That means re-running, adding instrumentation, waiting...{RESET}")
    print()
    print(f"   {DIM}Meanwhile, the same investigation with Retrace takes 30 seconds.{RESET}")
    print()

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    run_investigation()
