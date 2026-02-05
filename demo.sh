#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║      ${YELLOW}RETRACE DEMO: Training Data Leak Detection${CYAN}            ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║      Trace AI training data leaks back to their source      ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# PART 1: Run Training Pipeline
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  PART 1: ML Training Pipeline${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "📚 ${CYAN}Scenario:${NC} Fine-tuning a Medical AI Assistant"
echo ""
echo "   We're training an LLM on medical case data to help doctors."
echo "   The training data includes:"
echo "   • Real EHR exports (should be sanitized)"
echo "   • Medical textbook excerpts (safe)"
echo "   • Synthetic case studies (safe)"
echo ""

read -p "   Press Enter to start training pipeline..."
echo ""

cd "$SCRIPT_DIR/training_pipeline"
python3 train_medical_assistant.py 2>&1

echo ""

# ============================================================================
# PART 2: The Problem
# ============================================================================

echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  ⚠️  ALERT: PII Detected in Model Output!${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "   The model output contains: ${RED}\"Patient John Smith, DOB 03/15/1978\"${NC}"
echo ""
echo "   This is REAL patient data that should have been removed!"
echo ""
echo -e "${YELLOW}   Traditional debugging options:${NC}"
echo "   ┌─────────────────────────────────────────────────────────────┐"
echo "   │  ❌  Re-run training with verbose logging (hours/days)     │"
echo "   │  ❌  Search through millions of training examples (tedious)│"
echo "   │  ❌  Retrain from scratch (expensive, weeks)               │"
echo "   │  ❌  Hope it doesn't happen again (risky)                  │"
echo "   └─────────────────────────────────────────────────────────────┘"
echo ""
echo -e "   ${RED}Problem: We can't trace data lineage after training!${NC}"
echo ""

read -p "   Press Enter to see how Retrace solves this..."
echo ""

# ============================================================================
# PART 3: Retrace Investigation
# ============================================================================

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  PART 2: Retrace Provenance Investigation${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "🔍 ${CYAN}Retrace recorded every data transformation.${NC}"
echo "   Now we can trace backwards to find exactly where the leak originated."
echo ""

read -p "   Press Enter to start investigation..."
echo ""

cd "$SCRIPT_DIR/investigation"
python3 investigate_leak.py 2>&1

echo ""

# ============================================================================
# PART 4: Summary
# ============================================================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  SUMMARY: The Value of Retrace${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "   ┌─────────────────────────────────────────────────────────────┐"
echo "   │                                                             │"
echo "   │   WITHOUT RETRACE          │    WITH RETRACE               │"
echo "   │   ─────────────────────────┼──────────────────────────     │"
echo "   │   Days of investigation    │    Seconds                    │"
echo "   │   Uncertain root cause     │    Exact code location        │"
echo "   │   Unknown blast radius     │    All affected data found    │"
echo "   │   Incomplete audit trail   │    Full compliance record     │"
echo "   │   Expensive retraining     │    Surgical fix possible      │"
echo "   │                                                             │"
echo "   └─────────────────────────────────────────────────────────────┘"
echo ""
echo -e "${GREEN}   Key Capabilities Demonstrated:${NC}"
echo "   ✓ Traced leak from model output → sanitization bug → source file"
echo "   ✓ Identified exact regex bug in sanitize_pii() function"
echo "   ✓ Found all other affected training examples"
echo "   ✓ Generated compliance-ready audit trail"
echo ""
echo -e "${YELLOW}   For AI Companies Like Liquid AI:${NC}"
echo "   • Training data auditing for compliance"
echo "   • Debug data contamination issues"
echo "   • Trace model behaviors back to training examples"
echo "   • HIPAA/GDPR compliance documentation"
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                     DEMO COMPLETE                            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
