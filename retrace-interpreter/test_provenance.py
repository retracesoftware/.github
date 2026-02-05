#!/usr/bin/env python3
"""
Test provenance tracking - tracking where values come from.
"""

import sys
sys.path.insert(0, '/home/user/retrace-interpreter')

import retraceinterpreter
from retraceinterpreter import ProvenanceTracker

def simple_calculation():
    """A simple function with trackable provenance."""
    x = 10      # x created here
    y = 20      # y created here
    z = x + y   # z created from x and y
    return z

def complex_calculation():
    """A more complex function with nested operations."""
    a = 5
    b = 3
    c = a * b       # c = 15
    d = c + 10      # d = 25
    e = d * 2       # e = 50
    result = e - a  # result = 45
    return result

def print_provenance_tree(tracker, prov, indent=0):
    """Pretty print a provenance tree."""
    prefix = "  " * indent
    if prov is None:
        return

    tree = tracker.trace_value_origin(prov)
    if tree:
        print(f"{prefix}Variable: {tree['variable']}")
        print(f"{prefix}  Created at instruction {tree['instruction']}, line {tree['line']}")
        print(f"{prefix}  Operation: {tree['operation']}")
        if tree['sources']:
            print(f"{prefix}  Sources:")
            for source in tree['sources']:
                print(f"{prefix}    - {source['variable']} (instr {source['instruction']})")


print("=== Test 1: Simple calculation provenance ===")
result, tracker = retraceinterpreter.run(
    target=simple_calculation,
    use_subinterpreter=False,
    track_provenance=True,
    callback_at=0  # No callbacks, just track
)
print(f"Result: {result}")
print(f"\nProvenance history ({len(tracker.history)} events):")
for prov in tracker.history[-10:]:  # Last 10 events
    print(f"  {prov}")

# Find provenance for variables
print("\nVariable provenance:")
for (fid, var), prov in tracker.get_all_provenance().items():
    if not var.startswith('<') and not var.startswith('const:'):
        print(f"  {var}: instruction {prov.instruction_counter}, line {prov.lineno}")
        if prov.sources:
            print(f"    Sources: {[s.variable_name for s in prov.sources]}")


print("\n=== Test 2: Complex calculation with data flow ===")
result, tracker = retraceinterpreter.run(
    target=complex_calculation,
    use_subinterpreter=False,
    track_provenance=True,
    callback_at=0
)
print(f"Result: {result}")

print("\nData flow trace:")
# Find the 'result' variable
for (fid, var), prov in tracker.get_all_provenance().items():
    if var == 'result':
        print(f"\nTracing 'result' back to its origins:")
        print_provenance_tree(tracker, prov)
        break


print("\n=== Test 3: Provenance with callbacks ===")
def provenance_callback(state):
    """Callback that shows provenance at each checkpoint."""
    print(f"\nAt instruction {state.counter}:")
    if state.provenance:
        recent = state.provenance.history[-3:] if state.provenance.history else []
        for prov in recent:
            print(f"  Recent: {prov.variable_name} = {prov.opname} at line {prov.lineno}")
    return state.counter + 20  # Every 20 instructions

result, tracker = retraceinterpreter.run(
    target=complex_calculation,
    callback=provenance_callback,
    use_subinterpreter=False,
    track_provenance=True,
    callback_at=1
)
print(f"\nFinal result: {result}")


print("\n=== Test 4: Binary operation provenance ===")
def show_binary_ops():
    """Function to show binary operation tracking."""
    a = 2
    b = 3
    c = 4
    # This creates a chain: ((a + b) * c)
    temp = a + b
    result = temp * c
    return result

result, tracker = retraceinterpreter.run(
    target=show_binary_ops,
    use_subinterpreter=False,
    track_provenance=True,
    callback_at=0
)
print(f"Result: {result}")

print("\nBinary operations tracked:")
for prov in tracker.history:
    if prov.opname.startswith('BINARY') or prov.opname == 'BINARY_OP':
        print(f"  {prov.variable_name} at line {prov.lineno}")
        if prov.sources:
            sources = [s.variable_name for s in prov.sources]
            print(f"    Combined from: {sources}")


print("\n=== All provenance tests completed ===")
