#!/usr/bin/env python3
"""
Suspicious Transaction Tracker Demo

A financial transaction processing system that calculates fees and applies discounts.
During a routine audit, someone notices a transaction with an unexpectedly low fee
of $0.23 when it should have been much higher.

This demo shows how Retrace's provenance engine answers:
"Where did this suspicious value come from?"
"""


def calculate_base_fee(amount, transaction_type):
    """Calculate base fee based on transaction type."""
    rates = {
        'wire': 0.025,
        'ach': 0.015,
        'check': 0.010
    }
    rate = rates.get(transaction_type, 0.020)
    base_fee = amount * rate
    return base_fee


def apply_customer_discount(fee, customer_tier):
    """Apply tier-based discount."""
    discounts = {
        'platinum': 0.30,
        'gold': 0.20,
        'silver': 0.10,
        'bronze': 0.05
    }
    discount_rate = discounts.get(customer_tier, 0.0)
    discounted_fee = fee * (1 - discount_rate)
    return discounted_fee


def apply_promotional_discount(fee, promo_code):
    """Apply promotional discount if valid."""
    active_promos = {
        'WELCOME10': 0.10,
        'LOYAL15': 0.15,
        'VIP20': 0.20
    }
    if promo_code in active_promos:
        promo_rate = active_promos[promo_code]
        final_fee = fee * (1 - promo_rate)
        return final_fee
    return fee


def process_transaction(amount, transaction_type, customer_tier, promo_code):
    """Main transaction processing pipeline."""
    # Step 1: Calculate base fee
    base_fee = calculate_base_fee(amount, transaction_type)

    # Step 2: Apply customer tier discount
    fee_after_tier = apply_customer_discount(base_fee, customer_tier)

    # Step 3: Apply promotional discount
    final_fee = apply_promotional_discount(fee_after_tier, promo_code)

    # Round for display
    final_fee_rounded = round(final_fee, 2)
    effective_rate = round(final_fee / amount, 4)

    return {
        'amount': amount,
        'final_fee': final_fee_rounded,
        'effective_rate': effective_rate
    }


def main():
    """Process several transactions including the suspicious one."""
    print("=" * 60)
    print("TRANSACTION PROCESSING REPORT")
    print("=" * 60)

    # Transaction data: (amount, type, customer_tier, promo_code)
    # NOTE: Transaction #3 has a data entry error - amount is 30 instead of 30000!
    transactions = [
        (10000, 'wire', 'gold', None),           # Expected: $200 base, $160 after tier
        (5000, 'ach', 'platinum', 'WELCOME10'),  # Expected: $75 base, many discounts
        (30, 'check', 'silver', 'LOYAL15'),      # SUSPICIOUS: Fee is only $0.23! (should be 30000)
        (8000, 'wire', 'bronze', None),          # Expected: $200 base, $190 after tier
    ]

    for i, (amount, txn_type, tier, promo) in enumerate(transactions, 1):
        result = process_transaction(amount, txn_type, tier, promo)

        # Flag suspicious transactions
        expected_min_rate = 0.005  # Minimum expected rate is 0.5%
        is_suspicious = result['effective_rate'] < expected_min_rate

        flag = " [SUSPICIOUS - LOW FEE!]" if is_suspicious else ""

        print(f"\nTransaction #{i}:{flag}")
        print(f"  Amount: ${result['amount']:,.2f}")
        print(f"  Type: {txn_type}, Tier: {tier}, Promo: {promo or 'None'}")
        print(f"  Final Fee: ${result['final_fee']:.2f}")
        print(f"  Effective Rate: {result['effective_rate']:.4f} ({result['effective_rate']*100:.2f}%)")

    print("\n" + "=" * 60)
    print("AUDIT ALERT: Transaction #3 fee is only $0.23")
    print("Expected fee for this customer's typical transaction: ~$230")
    print("Investigation required: Where did $0.23 come from?")
    print("=" * 60)


if __name__ == '__main__':
    main()
