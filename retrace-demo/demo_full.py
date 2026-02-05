#!/usr/bin/env python3
"""
Full Demo - Shows the code, the problem, and the investigation
"""

import sys
import time

def slow_print(text, delay=0.015):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def pause(seconds=1):
    time.sleep(seconds)

def section(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65 + "\n")
    pause(0.3)

def main():
    print("\n" + "#" * 65)
    print("#" + " " * 63 + "#")
    print("#   RETRACE PROVENANCE DEMO                                     #")
    print("#   'Where did this value come from?'                           #")
    print("#" + " " * 63 + "#")
    print("#" * 65)

    # =========================================
    # PART 1: Show the Code
    # =========================================
    section("PART 1: THE CODE - How Fees Are Calculated")

    slow_print("First, let's look at the actual code that calculates fees:", 0.02)
    pause(0.5)

    print('''
  +------------------------------------------------------------------+
  |  def calculate_base_fee(amount, transaction_type):               |
  |      rates = {'wire': 0.025, 'ach': 0.015, 'check': 0.010}       |
  |      return amount * rates.get(transaction_type, 0.020)          |
  |                                                                  |
  |  def apply_customer_discount(fee, customer_tier):                |
  |      discounts = {'platinum': 0.30, 'gold': 0.20, 'silver': 0.10}|
  |      return fee * (1 - discounts.get(customer_tier, 0.0))        |
  |                                                                  |
  |  def apply_promotional_discount(fee, promo_code):                |
  |      promos = {'WELCOME10': 0.10, 'LOYAL15': 0.15, 'VIP20': 0.20}|
  |      if promo_code in promos:                                    |
  |          return fee * (1 - promos[promo_code])                   |
  |      return fee                                                  |
  +------------------------------------------------------------------+
''')

    pause(1)

    slow_print("The fee calculation pipeline:", 0.02)
    print('''
      amount ──> calculate_base_fee() ──> apply_customer_discount()
                                                    │
                                                    v
                              final_fee <── apply_promotional_discount()
''')

    pause(1)

    # =========================================
    # PART 2: Show Normal Calculation
    # =========================================
    section("PART 2: A NORMAL TRANSACTION - Let's Trace It")

    slow_print("Let's manually trace a NORMAL $10,000 wire transfer:", 0.02)
    pause(0.5)

    print('''
  TRANSACTION: $10,000 wire transfer, gold customer, no promo

  STEP 1: calculate_base_fee(10000, 'wire')
          base_fee = 10000 * 0.025 = $250.00

  STEP 2: apply_customer_discount(250, 'gold')
          20% discount for gold tier
          fee = 250 * (1 - 0.20) = $200.00

  STEP 3: apply_promotional_discount(200, None)
          No promo code
          final_fee = $200.00

  RESULT: Fee = $200.00 on $10,000 = 2.0% effective rate
          This looks NORMAL for a business transaction.
''')

    pause(1.5)

    # =========================================
    # PART 3: Show the Suspicious Transaction
    # =========================================
    section("PART 3: THE SUSPICIOUS TRANSACTION")

    slow_print("Now here's the transaction that triggered an AUDIT ALERT:", 0.02)
    pause(0.5)

    print('''
  +------------------------------------------------------------------+
  |                                                                  |
  |   AUDIT ALERT: Transaction #3                                    |
  |                                                                  |
  |   Customer: Silver tier (usually processes ~$30,000/month)       |
  |   Promo: LOYAL15 (15% off - loyal customer)                      |
  |   Transaction Type: Check                                        |
  |                                                                  |
  |   EXPECTED FEE: ~$230 (based on typical transaction size)        |
  |   ACTUAL FEE:   $0.23                                            |
  |                                                                  |
  |   ANOMALY: Fee is 1000x LOWER than expected!                     |
  |                                                                  |
  +------------------------------------------------------------------+
''')

    pause(1)

    slow_print("Why is this suspicious?", 0.02)
    print('''
  - This customer typically transacts ~$30,000
  - Their normal fee would be: $30,000 * 1% * 0.9 * 0.85 = $229.50
  - But this transaction's fee is only $0.23
  - That's a 1000x difference!

  QUESTION: Where did $0.23 come from?
''')

    pause(1.5)

    # =========================================
    # PART 4: Traditional Debugging Fails
    # =========================================
    section("PART 4: WHY TRADITIONAL DEBUGGING FAILS")

    slow_print("Let's try to debug this the traditional way...", 0.02)
    pause(0.5)

    print('''
  CHECKING LOGS:
  > 2024-01-15 14:32:15 INFO  Transaction processed
  > 2024-01-15 14:32:15 INFO  Customer: silver, Promo: LOYAL15
  > 2024-01-15 14:32:15 INFO  Final fee: $0.23

  PROBLEM: Logs only show the FINAL value!
           No intermediate calculations logged.
''')

    pause(1)

    print('''
  TRYING TO REPRODUCE:
  > What was the exact input amount? (Not logged)
  > What code path executed? (Not logged)
  > What were the intermediate values? (Not logged)

  PROBLEM: We CAN'T reproduce it without knowing the inputs!
''')

    pause(1)

    print('''
  OPTIONS (all bad):
  [X] Add logging to every function → Requires code changes
  [X] Redeploy to production → Takes time, may not catch it
  [X] Wait for it to happen again → Could take weeks
  [X] Guess and check → Unreliable

  RESULT: Hours or DAYS of investigation, maybe never find it.
''')

    pause(1.5)

    # =========================================
    # PART 5: Retrace Provenance Investigation
    # =========================================
    section("PART 5: RETRACE PROVENANCE - Trace Backwards")

    slow_print("But we RECORDED this execution with Retrace!", 0.02)
    slow_print("Let's trace the $0.23 backwards to find its origin...", 0.02)
    pause(1)

    print('''
  QUERY: trace_provenance('final_fee')

  Retrace recorded every instruction. Now we ask:
  "Where did each value come from?"
''')

    pause(1)

    # Step-by-step trace
    print("\n  " + "-" * 55)
    slow_print("  TRACE STEP 1: Where did $0.23 come from?", 0.02)
    print("  " + "-" * 55)
    pause(0.3)
    print('''
    final_fee_rounded = round(final_fee, 2)
    final_fee = 0.2295
                ^^^^^^
    --> $0.23 came from rounding 0.2295
''')
    pause(1)

    print("  " + "-" * 55)
    slow_print("  TRACE STEP 2: Where did $0.2295 come from?", 0.02)
    print("  " + "-" * 55)
    pause(0.3)
    print('''
    final_fee = fee_after_tier * (1 - promo_discount)
    final_fee = 0.27 * (1 - 0.15)
              = 0.27 * 0.85
              = 0.2295

    --> 15% promo discount (LOYAL15) applied to $0.27
''')
    pause(1)

    print("  " + "-" * 55)
    slow_print("  TRACE STEP 3: Where did $0.27 come from?", 0.02)
    print("  " + "-" * 55)
    pause(0.3)
    print('''
    fee_after_tier = base_fee * (1 - tier_discount)
    fee_after_tier = 0.30 * (1 - 0.10)
                   = 0.30 * 0.90
                   = 0.27

    --> 10% tier discount (silver) applied to $0.30
''')
    pause(1)

    print("  " + "-" * 55)
    slow_print("  TRACE STEP 4: Where did $0.30 come from?", 0.02)
    print("  " + "-" * 55)
    pause(0.3)
    print('''
    base_fee = amount * rate
    base_fee = ??? * 0.01
             = 0.30

    Solving: amount = 0.30 / 0.01 = ???
''')
    pause(1)

    # The reveal
    print("\n  " + "!" * 55)
    print("  !" + " " * 53 + "!")
    print("  !   amount = 30                                      !")
    print("  !" + " " * 53 + "!")
    print("  !   *** ROOT CAUSE FOUND ***                         !")
    print("  !" + " " * 53 + "!")
    print("  " + "!" * 55)

    pause(2)

    # =========================================
    # PART 6: Root Cause Explanation
    # =========================================
    section("PART 6: ROOT CAUSE IDENTIFIED")

    print('''
  THE BUG: The transaction amount was $30, not $30,000!

  +------------------------------------------------------------------+
  |  EXPECTED:  amount = $30,000  (typical for this customer)        |
  |  ACTUAL:    amount = $30      (what was entered)                 |
  |  ERROR:     Missing THREE ZEROS!                                 |
  +------------------------------------------------------------------+

  This is a DATA ENTRY ERROR.
  Someone typed "30" instead of "30000".
''')

    pause(1)

    print('''
  PROOF - Let's verify both calculations:

  If amount = $30,000 (expected):
  --------------------------------
    base_fee = 30000 * 0.01 = $300.00
    after tier (10% off)    = $270.00
    after promo (15% off)   = $229.50  <-- Expected fee!

  If amount = $30 (actual):
  --------------------------------
    base_fee = 30 * 0.01    = $0.30
    after tier (10% off)    = $0.27
    after promo (15% off)   = $0.23    <-- What we saw!

  MATCH! The provenance trace is correct.
''')

    pause(1.5)

    # =========================================
    # PART 7: The Value
    # =========================================
    section("PART 7: THE VALUE OF PROVENANCE")

    print('''
  +---------------------------+---------------------------+
  |   WITHOUT RETRACE         |   WITH RETRACE            |
  +---------------------------+---------------------------+
  | Check logs - no details   | Query the recording       |
  | Try to reproduce - fail   | Trace backwards instantly |
  | Add logging - redeploy    | No code changes needed    |
  | Guess and check - slow    | Deterministic answer      |
  | Hours or days             | SECONDS                   |
  +---------------------------+---------------------------+

  TIME TO ROOT CAUSE:
  - Traditional: Hours to days (if ever)
  - With Retrace: < 10 seconds
''')

    pause(1)

    print('''
  KEY INSIGHT:
  ------------
  Retrace recorded EVERY intermediate value during execution.

  When we found the suspicious $0.23, we traced backwards:
    $0.23 → $0.2295 → $0.27 → $0.30 → amount=30

  This is IMPOSSIBLE with traditional debugging after the fact.
''')

    pause(1.5)

    section("DEMO COMPLETE")

    print('''
  RETRACE PROVENANCE answers the universal debugging question:

     "Where did this value come from?"

  - The question every debugger asks
  - The question traditional tools can't answer after execution
  - The question Retrace answers in seconds

  For your meeting: This capability enables
  - Instant root cause analysis
  - Compliance audit trails
  - LLM-powered automated debugging (via MCP server)
''')

if __name__ == '__main__':
    main()
