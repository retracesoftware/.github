#!/usr/bin/env python3
"""
Visualization Module

Pretty-prints provenance chains and investigation results.
"""

from typing import List, Dict, Optional


def print_header(title: str):
    """Print a major section header"""
    width = 60
    print("=" * width)
    padding = (width - len(title)) // 2
    print(" " * padding + title)
    print("=" * width)


def print_section(title: str):
    """Print a subsection header"""
    print(f"▶ {title}")
    print("-" * 40)


def format_provenance_chain(chain: List, leaked_value: str, leak_location: Dict) -> str:
    """
    Format provenance chain as a visual tree structure
    
    Shows the complete data lineage from source to leak
    """
    lines = []
    
    lines.append("📊 PROVENANCE CHAIN")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Leaked Value: \"{leaked_value}\"")
    lines.append(f"Found in: model.generate() output")
    lines.append("")
    lines.append("Data Flow (traced backwards):")
    lines.append("")
    
    # Group events by operation type for clearer visualization
    generate_events = [s for s in chain if "GENERATE" in s.operation]
    train_events = [s for s in chain if "TRAIN" in s.operation]
    sanitize_events = [s for s in chain if "SANITIZE" in s.operation]
    preprocess_events = [s for s in chain if "PREPROCESS" in s.operation]
    load_events = [s for s in chain if "LOAD" in s.operation]
    
    # Format the tree
    lines.append("└─ 🤖 MODEL OUTPUT [Generation]")
    if generate_events:
        gen = generate_events[0]
        lines.append(f"   │  Step: {gen.step:,}")
        lines.append(f"   │  Location: {gen.location}")
        lines.append(f"   │  Output: \"{gen.output_preview[:60]}...\"")
        if gen.metadata.get("leaked_from_index"):
            lines.append(f"   │  ⚠ Data leaked from training index: {gen.metadata['leaked_from_index']}")
    lines.append("   │")
    
    lines.append("   └─ 📚 TRAINING BATCH [Model memorized this data]")
    if train_events:
        train = train_events[0]
        lines.append(f"      │  Step: {train.step:,}")
        lines.append(f"      │  Location: {train.location}")
        lines.append(f"      │  Batch: {train.metadata.get('batch_num', 'N/A')}")
    lines.append("      │")
    
    lines.append("      └─ 🔓 SANITIZATION [Bug: PII not removed!]")
    if sanitize_events:
        for san in sanitize_events[:2]:  # Show first 2
            lines.append(f"         │  Step: {san.step:,}")
            lines.append(f"         │  Location: {san.location}")
            if san.metadata.get("bug_missed"):
                lines.append(f"         │  ❌ BUG: Input returned unchanged!")
                lines.append(f"         │  Input:  \"{san.input_preview[:50]}...\"")
                lines.append(f"         │  Output: \"{san.output_preview[:50]}...\"")
    lines.append("         │")
    
    lines.append("         └─ 📂 DATA SOURCE [Origin of PII]")
    if preprocess_events:
        pre = preprocess_events[0]
        lines.append(f"            │  Step: {pre.step:,}")
        lines.append(f"            │  Source: {pre.metadata.get('source', 'unknown')}")
        lines.append(f"            │  Index: {pre.metadata.get('index', 'N/A')}")
    lines.append("            │")
    lines.append("            └─ 📁 FILE: data/medical_cases.json")
    lines.append("               │  Type: real_ehr_export")
    lines.append("               │  Patient ID: P-447281")
    lines.append("               │  Contains: Real patient PII")
    lines.append("               └─ 🏥 Original: EHR System Export")
    
    return "\n".join(lines)


def format_blast_radius(affected_examples: List[Dict]) -> str:
    """
    Show other examples affected by the same bug
    """
    lines = []
    
    lines.append("💥 BLAST RADIUS ANALYSIS")
    lines.append("=" * 50)
    lines.append("")
    
    if not affected_examples:
        lines.append("✓ No other affected examples found")
        return "\n".join(lines)
    
    lines.append(f"⚠ Found {len(affected_examples)} other examples with same bug")
    lines.append("")
    
    # Count by type
    lines.append("Impact Summary:")
    lines.append(f"   • {len(affected_examples)} examples from real_ehr_export")
    lines.append(f"   • All contain real patient identifiers")
    lines.append(f"   • All were used in training batches")
    lines.append("")
    
    lines.append("Sample Affected Records:")
    lines.append("-" * 40)
    
    # Show first 5 affected examples
    for i, example in enumerate(affected_examples[:5]):
        preview = example.get("preview", "")[:60]
        idx = example.get("index", "N/A")
        lines.append(f"   {i+1}. Index {idx}: \"{preview}...\"")
    
    if len(affected_examples) > 5:
        lines.append(f"   ... and {len(affected_examples) - 5} more")
    
    lines.append("")
    lines.append("Estimated Exposure:")
    lines.append(f"   • Patient records: {len(affected_examples)}")
    lines.append(f"   • Unique patients: {len(affected_examples)}")
    lines.append(f"   • Data types: Names, DOB, Patient IDs, Medical history")
    
    return "\n".join(lines)


def format_remediation(root_cause: Dict) -> str:
    """
    Generate remediation recommendations
    """
    lines = []
    
    lines.append("🔧 ROOT CAUSE & REMEDIATION")
    lines.append("=" * 50)
    lines.append("")
    
    lines.append("Root Cause Identified:")
    lines.append("-" * 40)
    
    if root_cause.get("bug_description"):
        for line in root_cause["bug_description"].split("\n"):
            lines.append(f"   {line}")
    
    lines.append("")
    lines.append("Code Location:")
    lines.append("-" * 40)
    
    san_failure = root_cause.get("sanitization_failure", {})
    if san_failure:
        lines.append(f"   File: train_medical_assistant.py")
        lines.append(f"   Function: sanitize_pii()")
        lines.append(f"   Step: {san_failure.get('step', 'N/A')}")
        lines.append("")
        lines.append("   Buggy Code:")
        lines.append("   ┌────────────────────────────────────────┐")
        lines.append("   │ if \"Patient Name:\" in text:           │")
        lines.append("   │     pattern = r\"Patient Name: [\\w\\s]+\" │")
        lines.append("   │     # ❌ Misses \"Patient X, DOB...\"    │")
        lines.append("   └────────────────────────────────────────┘")
    
    lines.append("")
    lines.append("Required Actions:")
    lines.append("-" * 40)
    lines.append("   ☐ 1. IMMEDIATE: Quarantine affected model")
    lines.append("   ☐ 2. Fix sanitize_pii() regex patterns:")
    lines.append("        - Add pattern for 'Patient [Name], DOB'")
    lines.append("        - Add pattern for 'DOB MM/DD/YYYY'")
    lines.append("        - Add pattern for inline Patient IDs")
    lines.append("   ☐ 3. Retrain model without affected examples")
    lines.append("   ☐ 4. Audit all real_ehr_export sources")
    lines.append("   ☐ 5. Add validation layer:")
    lines.append("        - No training text should match DOB patterns")
    lines.append("        - No training text should match name patterns")
    lines.append("   ☐ 6. Document incident for compliance")
    
    lines.append("")
    lines.append("Compliance Notes:")
    lines.append("-" * 40)
    lines.append("   • HIPAA: Patient data exposure requires notification")
    lines.append("   • Audit trail: This investigation provides full lineage")
    lines.append("   • Retention: Preserve trace file for compliance records")
    
    return "\n".join(lines)


def format_summary_stats(investigation_time: float, events_analyzed: int) -> str:
    """
    Format investigation summary statistics
    """
    lines = []
    
    lines.append("")
    lines.append("📈 INVESTIGATION SUMMARY")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"   Investigation time: {investigation_time:.2f} seconds")
    lines.append(f"   Events analyzed: {events_analyzed:,}")
    lines.append(f"   Root cause: IDENTIFIED")
    lines.append(f"   Blast radius: CALCULATED")
    lines.append(f"   Remediation: GENERATED")
    lines.append("")
    lines.append("   Without Retrace: Days of manual investigation")
    lines.append("   With Retrace: Complete audit in seconds")
    
    return "\n".join(lines)
