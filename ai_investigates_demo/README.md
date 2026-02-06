# Retrace MCP Demo — AI Investigates a PII Leak Autonomously

An AI coding assistant investigates a personal data leak in a recorded Python execution, using Retrace's MCP server tools. The demo's central narrative: **an AI system debugs itself, post-hoc, from a single recording — no re-running, no extra logging, no human in the loop.**

## Quick Start

```bash
cd ai_investigates_demo
python investigate.py
```

**Requirements:** Python 3.8+ (no external dependencies)

## What You'll See

The demo simulates an autonomous AI investigator using Retrace MCP tools to find the root cause of a PII leak:

1. **Orient** — Opens the trace, finds the crash point (PIILeakDetected exception)
2. **Inspect** — Examines the call stack, discovers raw and sanitized data are identical
3. **Trace** — Uses provenance tracking to find the exact line where sanitization failed
4. **Assess** — Calculates blast radius (how many records are affected)
5. **Remediate** — Generates a regression test that proves the bug

## MCP Tools Demonstrated

| Tool | Purpose |
|------|---------|
| `open_trace` | Open a recorded execution for investigation |
| `get_crash_state` | Get exception info and crash location |
| `list_frames_at_step` | List call stack frames at any execution step |
| `inspect_stack` | Inspect local variables at a specific frame |
| `trace_provenance` | Trace a variable's value back to its origin |

## The Bug

The policy gate in `policy_gate.py` has a regex that only matches:
```
"Patient Name: John Smith"
```

But the actual data uses:
```
"Patient John Smith, DOB 03/15/1978"
```

The regex doesn't match, so PII passes through unredacted.

## File Structure

```
ai_investigates_demo/
├── investigate.py              # Main demo (run this!)
├── mock_mcp_server.py          # Simulated MCP server
├── policy_gate.py              # The buggy sanitization code
├── eval_runner.py              # Reference: eval pipeline
├── pii_detector.py             # Reference: PII scanner
├── tool_registry.py            # Reference: tool implementations
├── test_policy_gate_regression.py  # Auto-generated tests
├── datasets/
│   └── pii_export.json         # Sample patient records
└── README.md
```

## Key Messages

1. **AI can debug AI** — No human had to read logs or set breakpoints
2. **Record once, investigate forever** — The trace was recorded in production
3. **Root cause in seconds** — From "PII leaked" to exact line number in 6 MCP calls
4. **Blast radius quantified** — Not just "bug found" but "N records affected"
5. **Any MCP client can do this** — Claude, Cursor, custom agents

## Running the Regression Tests

```bash
python test_policy_gate_regression.py
```

The inline name format test will **fail** (as expected) until the regex is fixed.
