#!/usr/bin/env python3
"""
Test script for retrace-interpreter with use_subinterpreter option.
"""

import sys
sys.path.insert(0, '/home/user/retrace-interpreter')

print("1. Importing module...")
import _retraceinterpreter as ri
print(f"2. Module imported: {ri}")

def test_function():
    print("3. In test function")
    return 42

def my_callback(state):
    print(f"CALLBACK CALLED: counter={state}")
    return None  # Disable further callbacks

def thread_id(modules):
    return 1

# Test with subinterpreter (should work)
print("\n=== Testing with use_subinterpreter=True (default) ===")
try:
    print("About to call run with SUBINTERPRETER...")
    result = ri.run(
        target=test_function,
        args=(),
        kwargs={},
        main_thread=thread_id,
        thread=thread_id,
        callback=my_callback,
        use_subinterpreter=True
    )
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Test without subinterpreter (causes segfault)
print("\n=== Testing with use_subinterpreter=False ===")
try:
    print("About to call run WITHOUT subinterpreter...")
    result = ri.run(
        target=test_function,
        args=(),
        kwargs={},
        main_thread=thread_id,
        thread=thread_id,
        callback=my_callback,
        use_subinterpreter=False
    )
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== All tests completed ===")
