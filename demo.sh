#!/bin/bash

# Retrace Demo: Eval Leak Forensics
# Traces PII leaks in tool-using agent evals back to their source

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║      RETRACE DEMO: Eval Leak Forensics                       ║"
echo "║                                                              ║"
echo "║      Trace PII leaks in tool-using agent evals               ║"
echo "║      back to their source - using MCP provenance             ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# PART 1: Run Eval Pipeline
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PART 1: Running Tool-Using Agent Evaluation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Scenario: Evaluating an AI assistant that uses tools to"
echo "   look up customer records. A policy gate should sanitize"
echo "   PII from tool outputs before they reach the model."
echo ""
echo "   The policy gate has a bug: it only catches 'Patient Name:'"
echo "   format but misses 'Patient John Smith, DOB...' format."
echo ""

read -p "   Press Enter to start eval pipeline..."
echo ""

cd "$SCRIPT_DIR"

# Run eval pipeline (expected to fail with leak detection)
echo "Running eval pipeline..."
echo ""

set +e  # Don't exit on error - we expect the eval to fail
python3 eval_pipeline/run_eval.py 2>&1
EVAL_EXIT=$?
set -e

echo ""

if [ $EVAL_EXIT -ne 0 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ⚠️  LEAK DETECTED - As Expected!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "   The eval crashed because PII was detected in output:"
    echo "   • Name: \"John Smith\""
    echo "   • DOB: \"03/15/1978\""
    echo ""
    echo "   Traditional debugging would require:"
    echo "   ┌─────────────────────────────────────────────────────────┐"
    echo "   │  ❌ Re-running with verbose logging                    │"
    echo "   │  ❌ Manually tracing through code                      │"
    echo "   │  ❌ Adding print statements everywhere                 │"
    echo "   │  ❌ Hours of investigation                             │"
    echo "   └─────────────────────────────────────────────────────────┘"
    echo ""
else
    echo "⚠️  Unexpected: Eval completed without detecting leak"
    exit 1
fi

# ============================================================================
# PART 2: Run Investigation
# ============================================================================

read -p "   Press Enter to investigate with Retrace..."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PART 2: Retrace MCP Forensics Investigation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔍 Using Retrace MCP tools to investigate:"
echo "   1. open_trace() - Load the recorded execution"
echo "   2. get_crash_state() - Find where the leak was detected"
echo "   3. inspect_stack() - Extract breadcrumb locals"
echo "   4. trace_provenance() - Find the bug location"
echo ""

python3 investigation/investigate_leak.py 2>&1

echo ""

# ============================================================================
# PART 3: Run Regression Test
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PART 3: Running Generated Regression Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 The investigation generated a regression test that will"
echo "   fail until the policy gate bug is fixed."
echo ""

set +e
python3 investigation/generated_tests/test_pii_gate_regression.py 2>&1
TEST_EXIT=$?
set -e

echo ""

if [ $TEST_EXIT -ne 0 ]; then
    echo "   ⚠️  Regression test failed (expected - bug not yet fixed)"
else
    echo "   ✓ Regression test passed"
fi

# ============================================================================
# PART 4: AI-Driven Investigation (The "What Your Product Could Do" Moment)
# ============================================================================

echo ""
read -p "   Press Enter to see AI-driven investigation..."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PART 4: AI-Driven Investigation via MCP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🤖 What if your AI coding assistant could do this automatically?"
echo ""
echo "   Instead of a human running investigation commands,"
echo "   the AI queries Retrace MCP tools autonomously and"
echo "   delivers the root cause in seconds."
echo ""
echo "   This is what Cursor, Copilot, or your AI assistant"
echo "   could offer: \"Here's why your code leaked PII.\""
echo ""

python3 investigation/ai_investigation.py 2>&1

# ============================================================================
# SUMMARY
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  DEMO SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   ┌─────────────────────────────────────────────────────────┐"
echo "   │                                                         │"
echo "   │   WITHOUT RETRACE        │   WITH RETRACE              │"
echo "   │   ──────────────────────┼────────────────────────      │"
echo "   │   Hours of debugging     │   Seconds                   │"
echo "   │   Uncertain root cause   │   Exact file:line:function  │"
echo "   │   Unknown blast radius   │   All affected records      │"
echo "   │   Manual test writing    │   Auto-generated tests      │"
echo "   │   Incomplete audit       │   Full compliance trail     │"
echo "   │                                                         │"
echo "   └─────────────────────────────────────────────────────────┘"
echo ""
echo "   Key Capabilities Demonstrated:"
echo "   ✓ Record-replay execution tracing"
echo "   ✓ MCP provenance queries (open_trace, inspect_stack, trace_provenance)"
echo "   ✓ Crash-on-leak detection with breadcrumb locals"
echo "   ✓ Automatic regression test generation"
echo "   ✓ Complete audit trail for compliance"
echo "   ✓ AI-native: LLMs query MCP tools for autonomous investigation"
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                      DEMO COMPLETE                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
