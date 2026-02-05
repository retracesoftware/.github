# Retrace Provenance Demo: The Suspicious Transaction Tracker

## Overview

This demo showcases Retrace's unique provenance tracking capability - the ability to trace any value back to its origin to answer **"Where did this value come from?"**

## The Scenario

A financial transaction processing system calculates fees with multiple discounts applied. During a routine audit, someone notices a transaction with an unexpectedly low fee of **$0.23** when it should have been around **$230**.

**The Question:** Where did this suspicious $0.23 come from?

## Why This Is Hard

Traditional debugging tools can't answer this question because:

1. **The incident already happened** - can't reproduce it with a debugger
2. **Logs show final values, not intermediate steps** - no trace of how it was computed
3. **The fee calculation involves multiple functions** - discounts applied in sequence
4. **No code instrumentation was in place** - would need to add logging and redeploy

## How Retrace Solves It

Retrace's provenance engine automatically tracks which instruction produced each value during execution. When you find a suspicious value, you can trace it backwards through every transformation to find the root cause.

## Files

- `suspicious_transaction.py` - The sample transaction processing application
- `demo_provenance_query.py` - Demo showing provenance tracing in action

## Running the Demo

```bash
# Run the transaction processor (shows the suspicious $0.23 fee)
python suspicious_transaction.py

# Run the provenance demo (traces $0.23 back to its origin)
python demo_provenance_query.py
```

## Demo Output

The provenance demo traces the $0.23 value through the calculation chain:

```
DATA LINEAGE FOR $0.23:
--------------------------------------------------

  $0.23 = final_fee_rounded
      └─ Created at instruction 36

      └─ final_fee = fee_after_tier * (1 - 0.15)
         = $0.27 * 0.85 = $0.2295
         @ instruction 30

          └─ fee_after_tier = base_fee * (1 - 0.10)
             = $0.30 * 0.90 = $0.27
             @ instruction 20

              └─ base_fee = amount * rate
                 = 30 * 0.01 = $0.30
                 @ instruction 10

                  └─ amount = 30
                     *** ROOT CAUSE FOUND ***
                     @ instruction 2
```

**Root Cause:** The amount was entered as $30 instead of $30,000 - a data entry error with missing zeros.

## MCP Server Integration

The `/home/user/retrace-interpreter/mcp_server.py` provides an MCP (Model Context Protocol) server that exposes provenance capabilities as tools for LLM integration:

### Available Tools

| Tool | Description |
|------|-------------|
| `open_trace` | Open a retrace recording for analysis |
| `close_trace` | Close an open trace session |
| `run_to_instruction` | Run execution to a specific instruction count |
| `get_provenance` | Get provenance information for tracked values |
| `trace_provenance` | Trace the origin of a value recursively |
| `get_source` | Get source code around a specific line |
| `search_variables` | Search for variables by name pattern |

### Example MCP Query

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "trace_provenance",
    "arguments": {
      "session_id": "session_1",
      "variable": "final_fee"
    }
  },
  "id": 1
}
```

## Why This Matters

| Traditional Debugging | Retrace Provenance |
|----------------------|-------------------|
| Only see final values | See every intermediate step |
| Need to reproduce the bug | Works on past executions |
| Add logging, redeploy, wait | No code changes needed |
| May never find root cause | Deterministic trace to source |
| Hours of investigation | Instant provenance query |

## Use Cases

1. **Financial Auditing** - Trace any transaction value back to its inputs
2. **Compliance** - Demonstrate data lineage for regulatory requirements
3. **Debugging** - Find root causes of incorrect values without reproduction
4. **Security** - Trace suspicious values to identify potential injection points
5. **ML Debugging** - Track which inputs influenced a model's prediction
