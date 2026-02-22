# BUG-002: SIGTRAP Assertion Failure During Wagtail Recording

## Summary

Recording fails with SIGTRAP (trace/breakpoint trap) when attempting to record a Wagtail/Django application. The crash occurs during Python module import, specifically in the C++ utils layer assertion checking.

## Environment

- **Python:** 3.11.14
- **retracesoftware:** 0.1.1
- **retracesoftware_stream:** 0.2.41
- **retracesoftware_utils:** 0.2.16
- **Platform:** Linux 4.4.0
- **Django:** 4.2.x
- **Wagtail:** 5.2

## Reproduction Steps

1. Clone the Wagtail bakerydemo:
```bash
git clone https://github.com/wagtail/bakerydemo.git
cd bakerydemo
git checkout v5.2
```

2. Install dependencies:
```bash
pip install -r requirements/development.txt
```

3. Create a test file `test_retrace.py`:

```python
"""
Test Retrace with Wagtail bakerydemo.

Uses Django test client to make requests without running a server.
Sets up minimal database in memory.
"""
import os
import sys
import django

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bakerydemo.settings.dev')
os.environ['DATABASE_URL'] = 'sqlite://:memory:'
os.environ['SECRET_KEY'] = 'retrace-test-key'

# Must setup Django before importing models
django.setup()

import datetime
import random
from django.test import Client
from django.core.management import call_command

def main():
    print("=== Wagtail Bakerydemo + Retrace Test ===")
    print()

    # Run migrations to set up the database
    print("Setting up database...")
    call_command('migrate', '--run-syncdb', verbosity=0)
    print("Database ready.")
    print()

    # Create test client
    client = Client()

    print("Making requests...")
    print()

    for i in range(3):
        ts = str(datetime.datetime.now())
        rval = random.randint(1, 1000)

        response = client.get('/')

        print(f"Request {i+1}:")
        print(f"  timestamp: {ts}")
        print(f"  random:    {rval}")
        print(f"  status:    {response.status_code}")
        print()

    # Try the admin
    response = client.get('/admin/')
    print(f"Admin request:")
    print(f"  timestamp: {datetime.datetime.now()}")
    print(f"  status:    {response.status_code}")
    print()

    print("Done.")

if __name__ == "__main__":
    main()
```

4. Run with Retrace:
```bash
python3 -m retracesoftware --recording ./trace -- test_retrace.py
```

## Expected Behavior

Recording completes successfully, capturing non-deterministic values from Django/Wagtail request handling.

## Actual Behavior

Process terminates with SIGTRAP:

```
Trace/breakpoint trap
```

The crash occurs early during initialization, before any application code runs. The process exits immediately with no trace file created.

## Root Cause Analysis

The SIGTRAP signal indicates an assertion failure in the C++ extension code (`retracesoftware_utils` or `retracesoftware_stream`). This typically occurs when:

1. **Assertion macro triggered** — A condition in the C++ code evaluated to false, triggering `__builtin_trap()` or similar
2. **During module import** — The crash occurs during Python's import machinery while loading Django/Wagtail modules
3. **Possible causes:**
   - Type mismatch in proxy setup for a complex type
   - Unexpected state during recursive module import
   - Buffer overflow or memory corruption during proxy initialization
   - Thread-safety issue during concurrent module loading

## Debugging Information Needed

To diagnose further, the following would help:

1. **Stack trace from gdb:**
```bash
gdb -ex run -ex bt --args python3 -m retracesoftware --recording ./trace -- test_retrace.py
```

2. **Valgrind memory check:**
```bash
valgrind --track-origins=yes python3 -m retracesoftware --recording ./trace -- test_retrace.py
```

3. **Verbose output:**
```bash
RETRACE_DEBUG=1 python3 -m retracesoftware --recording ./trace -- test_retrace.py
```

## Affected Use Cases

- **Wagtail CMS applications**
- **Django applications with many third-party packages**
- **Any application with complex module dependency graphs**
- Potentially any application importing packages that trigger the assertion

## Workaround

Currently none. The crash occurs before application code runs, making it impossible to avoid.

**Partial workaround:** Test with simpler Django configurations first:
- Minimal Django (no ORM): Works
- Django with sqlite: Works
- Django with test client: Works
- Wagtail bakerydemo: Fails

## Related Information

### Comparison with Working Django Test

A minimal Django app (`/home/user/django_test/app.py`) records successfully:
- Single-file Django with in-memory sqlite
- Uses RequestFactory (lighter weight than test client)
- No Wagtail or complex third-party dependencies

The difference suggests the issue is related to:
- Number or complexity of imported modules
- Specific packages in Wagtail's dependency tree
- Something in Wagtail's initialization sequence

### Packages in Wagtail That May Trigger Issue

Key Wagtail dependencies that differ from minimal Django:
- `willow` (image processing)
- `beautifulsoup4` (HTML parsing)
- `django-taggit`
- `django-modelcluster`
- `django-treebeard`
- `draftjs_exporter`
- `Pillow` (C extension)
- `lxml` (C extension)

The C extensions (Pillow, lxml) are prime suspects as they may interact poorly with Retrace's proxy system.

## Priority

**High** — Blocks recording of production CMS applications. Wagtail is widely used for content-heavy sites.

## Suggested Investigation Steps

1. **Binary search on imports** — Create a test that imports Wagtail packages one at a time to isolate which triggers the crash

2. **Check C extension interaction** — Test with `Pillow` and `lxml` directly (without Django) to see if they trigger the same issue

3. **Review assertion locations** — Add logging before assertions in `retracesoftware_utils` to identify which check fails

4. **Test with debug build** — Compile `retracesoftware_stream` and `retracesoftware_utils` with debug symbols and no optimization for better stack traces

## Related

- BUG-001: File Lock Conflict When Using os.fork() (separate issue)
- retracesoftware_utils C++ assertion macros
- Python import machinery internals
