#!/usr/bin/env python3
"""
Interactive Provenance Demo - Shows the investigation process step by step
"""

import sys
import time

def slow_print(text, delay=0.02):
    """Print text with typing effect."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def pause(seconds=1.5):
    time.sleep(seconds)

def section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")
    pause(0.5)

def main():
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#     RETRACE PROVENANCE DEMO                              #")
    print("#     'Where did this value come from?'                    #")
    print("#" + " " * 58 + "#")
    print("#" * 60)

    pause(1)

    # =========================================
    # SCENE 1: The Alert
    # =========================================
    section("SCENE 1: THE ALERT")

    slow_print("Your monitoring system flags an anomaly...", 0.03)
    pause(1)

    print("\n  +------------------------------------------+")
    print("  |  AUDIT ALERT                             |")
    print("  |  Transaction #3: Fee = $0.23             |")
    print("  |  Expected: ~$230                         |")
    print("  |  Anomaly: 1000x lower than expected!     |")
    print("  +------------------------------------------+")

    pause(2)

    slow_print("\nThis customer typically pays ~$230 in fees.", 0.03)
    slow_print("Why is this transaction only $0.23?", 0.03)

    pause(1.5)

    # =========================================
    # SCENE 2: Traditional Approach (Frustration)
    # =========================================
    section("SCENE 2: TRADITIONAL DEBUGGING")

    slow_print("Let's try to debug this the traditional way...", 0.03)
    pause(1)

    print("\n  Checking logs...")
    pause(0.8)
    print("  > Transaction processed successfully")
    print("  > Final fee: $0.23")
    print("  > Customer: silver tier")
    print("  > Promo: LOYAL15")

    pause(1)
    slow_print("\n  That's ALL the logs show.", 0.03)
    slow_print("  No intermediate values. No calculation steps.", 0.03)

    pause(1)

    print("\n  Trying to reproduce...")
    pause(0.8)
    print("  > What were the exact inputs?")
    print("  > What was the server state?")
    print("  > Which code path executed?")

    pause(1)
    slow_print("\n  We CAN'T reproduce it - the moment has passed.", 0.03)

    pause(1)

    print("\n  Options:")
    print("  [X] Add logging to every function")
    print("  [X] Redeploy to production")
    print("  [X] Wait for it to happen again")
    print("  [X] Hope we catch it next time")

    pause(1.5)
    slow_print("\n  This could take HOURS or DAYS...", 0.03)
    slow_print("  Or we might NEVER find the root cause.", 0.03)

    pause(2)

    # =========================================
    # SCENE 3: Retrace Provenance (The Solution)
    # =========================================
    section("SCENE 3: RETRACE PROVENANCE")

    slow_print("But wait - we recorded this execution with Retrace.", 0.03)
    slow_print("Let's trace the $0.23 backwards to find its origin...", 0.03)

    pause(1.5)

    print("\n  QUERY: trace_provenance('final_fee')")
    pause(1)

    # Step 1
    print("\n  " + "-" * 50)
    slow_print("  STEP 1: Where did $0.23 come from?", 0.03)
    print("  " + "-" * 50)
    pause(0.5)
    print("  final_fee_rounded = round(final_fee, 2)")
    print("  final_fee = $0.2295")
    print("              ^^^^^^")
    slow_print("  --> The $0.23 came from rounding $0.2295", 0.03)
    pause(1.5)

    # Step 2
    print("\n  " + "-" * 50)
    slow_print("  STEP 2: Where did $0.2295 come from?", 0.03)
    print("  " + "-" * 50)
    pause(0.5)
    print("  final_fee = fee_after_tier * (1 - promo_discount)")
    print("  final_fee = $0.27 * 0.85")
    print("            = $0.2295")
    slow_print("  --> 15% promo discount applied to $0.27", 0.03)
    pause(1.5)

    # Step 3
    print("\n  " + "-" * 50)
    slow_print("  STEP 3: Where did $0.27 come from?", 0.03)
    print("  " + "-" * 50)
    pause(0.5)
    print("  fee_after_tier = base_fee * (1 - tier_discount)")
    print("  fee_after_tier = $0.30 * 0.90")
    print("                 = $0.27")
    slow_print("  --> 10% tier discount applied to $0.30", 0.03)
    pause(1.5)

    # Step 4
    print("\n  " + "-" * 50)
    slow_print("  STEP 4: Where did $0.30 come from?", 0.03)
    print("  " + "-" * 50)
    pause(0.5)
    print("  base_fee = amount * rate")
    print("  base_fee = ??? * 0.01")
    print("           = $0.30")
    print()
    slow_print("  Solving for amount: $0.30 / 0.01 = ...", 0.03)
    pause(1)

    # THE REVEAL
    print("\n  " + "!" * 50)
    print("  !                                                !")
    print("  !   amount = 30                                  !")
    print("  !                                                !")
    print("  !   *** ROOT CAUSE FOUND ***                     !")
    print("  !                                                !")
    print("  " + "!" * 50)

    pause(2)

    # =========================================
    # SCENE 4: The Diagnosis
    # =========================================
    section("SCENE 4: ROOT CAUSE IDENTIFIED")

    slow_print("The transaction amount was $30, not $30,000!", 0.03)
    pause(1)

    print("\n  EXPECTED:  amount = $30,000")
    print("  ACTUAL:    amount = $30")
    print("  ERROR:     Missing three zeros!")

    pause(1.5)

    print("\n  This is a DATA ENTRY ERROR.")
    print("  Someone typed '30' instead of '30000'.")

    pause(1.5)

    print("\n  Fee calculation proof:")
    print("  -----------------------")
    print("  If amount = $30,000:")
    print("    Base fee:    $30,000 x 0.01 = $300.00")
    print("    After tier:  $300 x 0.90    = $270.00")
    print("    After promo: $270 x 0.85    = $229.50  <-- Expected!")
    print()
    print("  If amount = $30 (actual):")
    print("    Base fee:    $30 x 0.01     = $0.30")
    print("    After tier:  $0.30 x 0.90   = $0.27")
    print("    After promo: $0.27 x 0.85   = $0.23    <-- What we saw!")

    pause(2)

    # =========================================
    # SCENE 5: The Value
    # =========================================
    section("SCENE 5: THE VALUE OF PROVENANCE")

    print("  +--------------------+--------------------+")
    print("  | WITHOUT RETRACE    | WITH RETRACE       |")
    print("  +--------------------+--------------------+")
    print("  | Hours of work      | 10 seconds         |")
    print("  | Maybe find cause   | Guaranteed answer  |")
    print("  | Need reproduction  | Works on past data |")
    print("  | Add logging first  | No code changes    |")
    print("  +--------------------+--------------------+")

    pause(2)

    print("\n  KEY INSIGHT:")
    print("  -------------")
    slow_print("  Retrace recorded EVERY intermediate value.", 0.03)
    slow_print("  We traced backwards from $0.23 to amount=30.", 0.03)
    slow_print("  Total time: under 10 seconds.", 0.03)

    pause(1.5)

    print("\n  This is IMPOSSIBLE with traditional debugging")
    print("  after the execution has completed.")

    pause(2)

    section("DEMO COMPLETE")
    print("  Retrace Provenance answers:")
    print('  "Where did this value come from?"')
    print()
    print("  The question every debugger asks.")
    print("  The question traditional tools can't answer.")
    print()

if __name__ == '__main__':
    main()
