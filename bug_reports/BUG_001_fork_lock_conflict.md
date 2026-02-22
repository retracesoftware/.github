# BUG-001: File Lock Conflict When Using os.fork()

## Summary

Recording fails when the target application uses `os.fork()`. Child processes inherit the parent's trace writer file lock, causing lock conflicts and empty pipe reads.

## Environment

- **Python:** 3.11.14
- **retracesoftware:** 0.1.1
- **retracesoftware_stream:** 0.2.41
- **retracesoftware_utils:** 0.2.16
- **Platform:** Linux 4.4.0

## Reproduction Steps

1. Create a test file `test_forking.py`:

```python
import os
import sys
import datetime
import random
import json
import time

def child_work(child_id: int, write_fd: int):
    """Work done in each forked child."""
    ts = str(datetime.datetime.now())
    rval = random.randint(1, 10000)
    pid = os.getpid()
    time.sleep(0.05)
    ts2 = str(datetime.datetime.now())
    rval2 = random.randint(1, 10000)

    result = json.dumps({
        "child_id": child_id,
        "pid": pid,
        "start_time": ts,
        "random_1": rval,
        "end_time": ts2,
        "random_2": rval2,
    })

    os.write(write_fd, (result + "\n").encode())
    os.close(write_fd)
    os._exit(0)

def main():
    print(f"Parent PID: {os.getpid()}")
    children = []

    for i in range(3):
        read_fd, write_fd = os.pipe()
        pid = os.fork()

        if pid == 0:
            os.close(read_fd)
            child_work(i, write_fd)
        else:
            os.close(write_fd)
            children.append((i, pid, read_fd))

    results = {}
    for child_id, pid, read_fd in children:
        data = b""
        while True:
            chunk = os.read(read_fd, 4096)
            if not chunk:
                break
            data += chunk
        os.close(read_fd)
        os.waitpid(pid, 0)
        results[child_id] = json.loads(data.decode().strip())

    for i in range(3):
        print(f"Child {i}: {results[i]}")

if __name__ == "__main__":
    main()
```

2. Run with Retrace:
```bash
python3 -m retracesoftware --recording ./trace -- test_forking.py
```

## Expected Behavior

Recording completes successfully, capturing non-deterministic values from all child processes.

## Actual Behavior

Recording fails with:
```
TRIED TO LOCK AN ALREADY LOCKED FILE!!!!
TRIED TO LOCK AN ALREADY LOCKED FILE!!!!
TRIED TO LOCK AN ALREADY LOCKED FILE!!!!
```

Followed by:
```
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

The parent receives empty data from child pipes because the children crashed.

## Root Cause Analysis

When `os.fork()` is called:

1. The child process inherits the parent's file descriptors, including the trace file handle
2. The child also inherits the parent's lock state on `trace.bin`
3. When the child's `RecordProxySystem` tries to write to the trace, it attempts to acquire the lock
4. The lock is already held (inherited from parent), causing the "ALREADY LOCKED" error
5. The child crashes, never writes to its pipe, parent gets empty data

## Affected Use Cases

- **Gunicorn** with `--workers N` (uses fork)
- **Celery** with prefork pool
- **multiprocessing.Process** with fork start method
- Any application using `os.fork()` directly

## Suggested Fixes

### Option 1: Detect fork and disable tracing in child
```python
# In child after fork
os.register_at_fork(after_in_child=lambda: retrace.disable())
```

### Option 2: Per-process trace files
Create separate `trace_{pid}.bin` for each process, merge on replay.

### Option 3: Fork-aware lock handling
Use `pthread_atfork()` to release/reacquire locks around fork:
- `prepare`: Release lock in parent before fork
- `parent`: Reacquire lock in parent after fork
- `child`: Initialize fresh writer in child

### Option 4: Shared memory with lock-free writes
Use a lock-free ring buffer in shared memory for multi-process tracing.

## Workaround

Currently none. Applications using fork cannot be recorded.

## Priority

**High** — Blocks recording of production web servers (Gunicorn, uWSGI) and task queues (Celery).

## Related

- Python `os.register_at_fork()` documentation
- POSIX `pthread_atfork()` semantics
