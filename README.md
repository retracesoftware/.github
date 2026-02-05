# Retrace Demo: Training Data Leak Detection

**Trace AI training data leaks back to their source—in seconds, not days.**

This demo showcases Retrace's provenance tracking capabilities for AI companies. It demonstrates how to trace a PII leak in model output back through the training pipeline to identify the exact source file, the bug that caused it, and all other affected training examples.

## The Problem

When an LLM outputs sensitive data it shouldn't have seen:
- **Traditional debugging**: Days of investigation, uncertain results
- **With Retrace**: Complete audit trail in seconds

## What This Demo Shows

1. **Training Pipeline** - A simulated ML training pipeline with an intentional PII sanitization bug
2. **The Leak** - Model output contains real patient data ("John Smith, DOB 03/15/1978")
3. **Investigation** - Retrace traces the leak backwards through:
   - Model generation → Training batch → Sanitization (bug!) → Source file
4. **Blast Radius** - Find all other affected training examples
5. **Remediation** - Exact code fix and compliance documentation

## Quick Start

```bash
# Run the complete demo
./demo.sh
```

Or run components separately:

```bash
# 1. Run training pipeline (creates trace file)
cd training_pipeline
python train_medical_assistant.py

# 2. Investigate the leak
cd ../investigation
python investigate_leak.py
```

## Project Structure

```
retrace-liquid-demo/
├── demo.sh                           # Run complete demo
├── README.md                         # This file
├── training_pipeline/
│   ├── train_medical_assistant.py    # ML training simulation
│   ├── data/
│   │   └── medical_cases.json        # Training dataset
│   └── requirements.txt
├── investigation/
│   ├── investigate_leak.py           # Leak investigation tool
│   └── visualization.py              # Report formatting
└── training_run.trace                # Generated provenance trace
```

## The Bug

The demo includes an intentional sanitization bug in `sanitize_pii()`:

```python
# ❌ BUG: This regex is too restrictive!
if "Patient Name:" in text:
    pattern = r"Patient Name: [\w\s]+"
    return re.sub(pattern, "Patient [REDACTED]", text)
return text  # Misses "Patient John Smith, DOB..." format!
```

The function only catches `"Patient Name: John Smith"` format but misses `"Patient John Smith, DOB 03/15/1978"` format used in the actual EHR data.

## Key Retrace Features Demonstrated

| Feature | Description |
|---------|-------------|
| **Provenance Tracking** | Every data transformation is recorded |
| **Backward Tracing** | Trace any value back to its origin |
| **Root Cause Analysis** | Identify exact code location of bugs |
| **Blast Radius** | Find all affected data automatically |
| **Compliance Audit** | Full documentation for HIPAA/GDPR |

## Sample Output

```
📊 PROVENANCE CHAIN
==================================================

Leaked Value: "John Smith"
Found in: model.generate() output

Data Flow (traced backwards):

└─ 🤖 MODEL OUTPUT [Generation]
   │  Step: 847
   │  ⚠ Data leaked from training index: 2847
   │
   └─ 📚 TRAINING BATCH [Model memorized this data]
      │  Batch: 89
      │
      └─ 🔓 SANITIZATION [Bug: PII not removed!]
         │  ❌ BUG: Input returned unchanged!
         │
         └─ 📂 DATA SOURCE [Origin of PII]
            │  Source: real_ehr_export
            │  Index: 2847
            └─ 📁 FILE: data/medical_cases.json
```

## Why This Matters for AI Companies

### Compliance
- **HIPAA**: Trace exactly which patient records were exposed
- **GDPR**: Document data lineage for right-to-erasure requests
- **Audit Trail**: Complete provenance for regulators

### Debugging
- **Data Contamination**: Find where bad data entered training
- **Model Behavior**: Trace outputs back to training examples
- **Bug Identification**: Locate exact code causing issues

### Efficiency
- **Time**: Seconds vs days of investigation
- **Cost**: Surgical fixes vs expensive retraining
- **Certainty**: Exact root cause vs guesswork

## Integration with Retrace MCP Server

For automated investigation via LLMs, the Retrace MCP server provides tools:

- `open_trace` - Load recorded execution
- `trace_provenance` - Walk backwards through value history
- `search_variables` - Find variables by pattern
- `get_source` - Get source code context

This enables Claude to investigate data leaks automatically:

```
User: "Investigate where 'John Smith' came from in the training"

Claude: [Uses trace_provenance tool]
"The value originated from data/medical_cases.json index 2847,
passed through sanitize_pii() which failed to remove it due to
a regex pattern mismatch, then was included in training batch 89."
```

## Requirements

- Python 3.8+
- No external dependencies (uses standard library only)

## License

Apache License 2.0
