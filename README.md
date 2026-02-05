# Retrace Demo: Eval Leak Forensics

**Trace PII leaks in tool-using agent evaluations back to their source—using MCP provenance.**

This demo showcases Retrace's record-replay and MCP provenance capabilities for post-hoc forensics of AI evaluation runs. It demonstrates how to trace a PII leak in eval output back through the policy gate to identify the exact bug location.

## The Problem

When a tool-using AI agent leaks PII in its output during evaluation:
- **Traditional debugging**: Hours of manual code tracing
- **With Retrace**: Complete forensics in seconds via MCP tools

## What This Demo Shows

1. **Eval Pipeline** - A simulated tool-using agent that calls `lookup_customer` and `fetch_invoice` tools
2. **Policy Gate Bug** - A sanitization function with an intentional regex bug that misses common PII formats
3. **Crash-on-Leak** - The eval crashes when PII is detected, creating a clear anchor point
4. **MCP Investigation** - Uses real Retrace MCP calls to trace provenance and find root cause
5. **Regression Test** - Automatically generates a test file to prevent bug recurrence

## Quick Start

```bash
# Run the complete demo
./demo.sh
```

## Project Structure

```
retrace-eval-leak-demo/
├── eval_pipeline/
│   ├── run_eval.py           # Main eval runner with Retrace recording
│   ├── policy_gate.py        # PII sanitization (contains bug)
│   ├── tools.py              # Tool implementations
│   └── datasets/
│       ├── eval_prompts.json # Evaluation prompts
│       ├── tool_results.json # Tool response data
│       └── pii_export.json   # PII records (includes record 2847)
├── investigation/
│   ├── investigate_leak.py   # MCP-based investigation tool
│   ├── mcp_client.py         # Retrace MCP client
│   ├── visualization.py      # Report formatting
│   ├── regression_test_gen.py
│   └── generated_tests/      # Auto-generated tests
├── demo.sh                   # Run complete demo
└── README.md
```

## The Bug

The policy gate has an intentional bug in `_sanitize_name_in_text()`:

```python
# ❌ BUG: Only catches "Patient Name: X" format
if "Patient Name:" in text:
    pattern = r"Patient Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"
    text = re.sub(pattern, "Patient Name: [REDACTED]", text)
# MISSES: "Patient John Smith, DOB 03/15/1978..." format!
```

This causes PII from record 2847 (John Smith, DOB 03/15/1978) to leak through.

## Retrace Features Demonstrated

| Feature | How It's Used |
|---------|---------------|
| **Record-Replay** | Eval pipeline records execution with provenance tracking |
| **Crash-on-Leak** | Exception raised at leak detection creates investigation anchor |
| **Breadcrumb Locals** | Key variables (leaked_value, leak_source, etc.) in crash frame |
| **MCP: open_trace** | Opens the recorded trace for investigation |
| **MCP: get_crash_state** | Gets crash point and thread info |
| **MCP: inspect_stack** | Extracts breadcrumb locals from stack frames |
| **MCP: trace_provenance** | Traces backwards to find bug location |
| **Regression Test Gen** | Auto-generates test file from investigation |

## Expected Output

```
▶ Step 4: Tracing provenance (1 hop)
──────────────────────────────────────────────────────
   ✓ Found 5 provenance events
      [15] LEAK_DETECTED @ run_eval.py:run_eval()
      [14] GENERATE_RESPONSE_END @ run_eval.py:generate_response()
      [13] POLICY_GATE_OUTPUT @ run_eval.py:apply_policy_gate()
   ✓ Root cause identified:
      File: policy_gate.py
      Function: _sanitize_name_in_text()
      Line: 28

🎯 ROOT CAUSE ANALYSIS
══════════════════════════════════════════════════════

   Bug Location:
   ┌────────────────────────────────────────────────┐
   │ File: policy_gate.py                          │
   │ Function: _sanitize_name_in_text()            │
   │ Line: 28                                      │
   └────────────────────────────────────────────────┘
```

## Requirements

- Python 3.8+
- No external dependencies (uses standard library)

## How It Works

1. **Eval runs** under Retrace recording, tracking all data transformations
2. **PII leaks** through the buggy policy gate
3. **Leak detected** in output → exception raised with breadcrumb locals
4. **MCP investigation** opens trace, inspects stack, traces provenance
5. **Report generated** showing exact bug location
6. **Regression test** written to disk to prevent recurrence

## License

Apache License 2.0
