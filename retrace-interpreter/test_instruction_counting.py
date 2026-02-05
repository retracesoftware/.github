#!/usr/bin/env python3
"""
Test instruction counting with callbacks.
"""

import sys
sys.path.insert(0, '/home/user/retrace-interpreter')

import retraceinterpreter

def simple_function():
    """A simple function to count instructions in."""
    x = 1
    y = 2
    z = x + y
    return z

def longer_function():
    """A function with more instructions."""
    total = 0
    for i in range(10):
        total += i
        if total > 20:
            total = total - 5
    result = total * 2
    return result

callback_log = []

def logging_callback(state):
    """Callback that logs instruction counts."""
    callback_log.append(state.counter)
    # Schedule next callback in 50 instructions
    return state.counter + 50

print("=== Test 1: Simple function with callback every 50 instructions ===")
callback_log = []
result = retraceinterpreter.run(
    target=simple_function,
    callback=logging_callback,
    use_subinterpreter=False,
    callback_at=1
)
print(f"Result: {result}")
print(f"Callbacks at instructions: {callback_log}")

print("\n=== Test 2: Longer function with callback every 50 instructions ===")
callback_log = []
result = retraceinterpreter.run(
    target=longer_function,
    callback=logging_callback,
    use_subinterpreter=False,
    callback_at=1
)
print(f"Result: {result}")
print(f"Callbacks at instructions: {callback_log}")
print(f"Total instructions (approx): {callback_log[-1] if callback_log else 0}")

print("\n=== Test 3: Callback every 10 instructions ===")
callback_log = []
def frequent_callback(state):
    callback_log.append(state.counter)
    return state.counter + 10

result = retraceinterpreter.run(
    target=longer_function,
    callback=frequent_callback,
    use_subinterpreter=False,
    callback_at=1
)
print(f"Result: {result}")
print(f"Number of callbacks: {len(callback_log)}")
print(f"First 10 callback points: {callback_log[:10]}")

print("\n=== Test 4: Stop at specific instruction ===")
def stop_callback(state):
    print(f"  At instruction {state.counter}, frame {state.frame_counter}")
    if state.counter >= 100:
        print("  Stopping at 100 instructions")
        return None  # Stop callbacks
    return state.counter + 25

result = retraceinterpreter.run(
    target=longer_function,
    callback=stop_callback,
    use_subinterpreter=False,
    callback_at=1
)
print(f"Result: {result}")

print("\n=== All tests completed ===")
