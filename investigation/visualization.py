#!/usr/bin/env python3
"""
Visualization Module

Pretty-prints investigation results with tree structures and formatting.
"""

from typing import Dict, Any, List, Optional


def print_header(title: str):
    """Print a major section header."""
    width = 60
    print("╔" + "═" * (width - 2) + "╗")
    padding = (width - len(title) - 2) // 2
    print("║" + " " * padding + title + " " * (width - padding - len(title) - 2) + "║")
    print("╚" + "═" * (width - 2) + "╝")


def print_section(title: str):
    """Print a subsection header."""
    print(f"▶ {title}")
    print("─" * 50)


def format_crash_state(crash_state: Dict[str, Any]) -> str:
    """Format the crash state information."""
    if not crash_state:
        return "❌ No crash state available"
    
    lines = []
    lines.append("📊 CRASH STATE")
    lines.append("═" * 50)
    lines.append("")
    
    crash_event = crash_state.get("crash_event", {})
    
    lines.append(f"   Crash Step: {crash_state.get('crash_step', 'N/A')}")
    lines.append(f"   Operation: {crash_event.get('operation', 'unknown')}")
    lines.append(f"   Location: {crash_event.get('location', 'unknown')}")
    lines.append(f"   Timestamp: {crash_event.get('timestamp', 'N/A')}")
    
    threads = crash_state.get("threads", [])
    if threads:
        lines.append("")
        lines.append("   Threads:")
        for t in threads:
            lines.append(f"      [{t.get('thread_id')}] {t.get('name')} - {t.get('state')}")
    
    return "\n".join(lines)


def format_stack_inspection(stack_info: Dict[str, Any], 
                           breadcrumbs: Dict[str, Any]) -> str:
    """Format the stack inspection results."""
    if not stack_info:
        return "❌ No stack information available"
    
    lines = []
    lines.append("🔍 STACK INSPECTION")
    lines.append("═" * 50)
    lines.append("")
    
    frames = stack_info.get("frames", [])
    
    lines.append("   Call Stack:")
    for frame in frames:
        fn = frame.get("function", "unknown")
        file = frame.get("file", "unknown")
        line = frame.get("line", "?")
        idx = frame.get("frame_index", 0)
        marker = "→" if idx == 0 else " "
        lines.append(f"   {marker} [{idx}] {fn}() at {file}:{line}")
    
    lines.append("")
    lines.append("   Breadcrumb Locals (from crash frame):")
    lines.append("   ┌────────────────────────────────────────────────┐")
    
    if breadcrumbs.get("leaked_value"):
        lines.append(f"   │ leaked_value = \"{breadcrumbs['leaked_value']}\"")
    if breadcrumbs.get("leaked_dob"):
        lines.append(f"   │ leaked_dob = \"{breadcrumbs['leaked_dob']}\"")
    if breadcrumbs.get("gate_version"):
        lines.append(f"   │ gate_version = \"{breadcrumbs['gate_version']}\"")
    if breadcrumbs.get("leak_source"):
        src = breadcrumbs["leak_source"]
        lines.append(f"   │ leak_source = {{")
        lines.append(f"   │     source_file: \"{src.get('source_file')}\"")
        lines.append(f"   │     record_id: {src.get('record_id')}")
        lines.append(f"   │     patient_id: \"{src.get('patient_id')}\"")
        lines.append(f"   │ }}")
    if breadcrumbs.get("blast_radius_count"):
        lines.append(f"   │ blast_radius_count = {breadcrumbs['blast_radius_count']}")
    
    lines.append("   └────────────────────────────────────────────────┘")
    
    return "\n".join(lines)


def format_provenance_chain(provenance_info: Dict[str, Any]) -> str:
    """Format the provenance chain as a tree."""
    if not provenance_info:
        return "❌ No provenance information available"
    
    lines = []
    lines.append("🔗 PROVENANCE CHAIN")
    lines.append("═" * 50)
    lines.append("")
    lines.append("   Data flow (traced backwards):")
    lines.append("")
    
    chain = provenance_info.get("provenance_chain", [])
    
    # Build tree visualization
    lines.append("   └─ 🚨 LEAK_DETECTED [Crash Point]")
    lines.append("      │")
    
    for i, event in enumerate(chain):
        op = event.get("operation", "unknown")
        loc = event.get("location", "unknown").split(":")[-1] if event.get("location") else "unknown"
        step = event.get("step", "?")
        
        if op == "LEAK_DETECTED":
            continue  # Skip, already shown
        
        icon = "🔓" if "POLICY_GATE" in op else "🔧" if "TOOL" in op else "📝"
        is_last = i == len(chain) - 1
        connector = "└" if is_last else "├"
        
        lines.append(f"      {connector}─ {icon} {op} [step {step}]")
        if not is_last:
            lines.append("      │     │")
    
    lines.append("")
    lines.append(f"   Provenance hops: {provenance_info.get('provenance_hops', 1)}")
    
    return "\n".join(lines)


def format_root_cause(provenance_info: Dict[str, Any],
                     source_context: Dict[str, Any]) -> str:
    """Format the root cause analysis."""
    lines = []
    lines.append("🎯 ROOT CAUSE ANALYSIS")
    lines.append("═" * 50)
    lines.append("")
    
    root_cause = provenance_info.get("root_cause_location", {}) if provenance_info else {}
    
    if not root_cause:
        lines.append("   ❌ Root cause not identified")
        return "\n".join(lines)
    
    lines.append("   Bug Location:")
    lines.append("   ┌────────────────────────────────────────────────┐")
    lines.append(f"   │ File: {root_cause.get('file', 'unknown')}")
    lines.append(f"   │ Function: {root_cause.get('function', 'unknown')}()")
    lines.append(f"   │ Line: {root_cause.get('line', '?')}")
    lines.append("   └────────────────────────────────────────────────┘")
    lines.append("")
    
    # Show the buggy code
    lines.append("   Buggy Code:")
    lines.append("   ┌────────────────────────────────────────────────┐")
    
    if source_context and "lines" in source_context:
        for line_info in source_context["lines"]:
            line_num = line_info.get("line", "")
            content = line_info.get("content", "")
            marker = " → " if line_info.get("current") else "   "
            lines.append(f"   │{marker}{line_num}: {content}")
    else:
        lines.append(f"   │ {root_cause.get('code', 'Code not available')}")
    
    lines.append("   └────────────────────────────────────────────────┘")
    lines.append("")
    
    lines.append("   Explanation:")
    lines.append(f"   {root_cause.get('explanation', 'No explanation available')}")
    
    return "\n".join(lines)


def format_blast_radius(breadcrumbs: Dict[str, Any]) -> str:
    """Format the blast radius analysis."""
    lines = []
    lines.append("💥 BLAST RADIUS")
    lines.append("═" * 50)
    lines.append("")
    
    count = breadcrumbs.get("blast_radius_count", 0)
    
    if count == 0:
        lines.append("   ✓ No additional affected records identified")
        return "\n".join(lines)
    
    lines.append(f"   ⚠ Found {count} other records affected by same bug")
    lines.append("")
    lines.append("   Affected records use the vulnerable format:")
    lines.append("   'Patient [Name], DOB [Date]...' (missing 'Patient Name:' prefix)")
    lines.append("")
    lines.append("   These records would also leak PII through the policy gate.")
    
    return "\n".join(lines)


def format_remediation(provenance_info: Dict[str, Any],
                      breadcrumbs: Dict[str, Any]) -> str:
    """Format remediation recommendations."""
    lines = []
    lines.append("🔧 REMEDIATION REQUIRED")
    lines.append("═" * 50)
    lines.append("")
    
    lines.append("   Immediate Actions:")
    lines.append("   ┌────────────────────────────────────────────────┐")
    lines.append("   │ ☐ 1. Quarantine affected eval outputs          │")
    lines.append("   │ ☐ 2. Fix policy_gate.py regex patterns:        │")
    lines.append("   │      - Add pattern for 'Patient [Name], DOB'   │")
    lines.append("   │      - Add pattern for 'DOB [Date]' (no colon) │")
    lines.append("   │ ☐ 3. Re-run affected evals after fix           │")
    lines.append("   │ ☐ 4. Run generated regression test to verify   │")
    lines.append("   └────────────────────────────────────────────────┘")
    lines.append("")
    
    lines.append("   Compliance Notes:")
    lines.append("   • HIPAA: PII exposure detected - assess notification requirements")
    lines.append("   • Audit: This investigation provides complete trace")
    lines.append("   • Testing: Regression test generated to prevent recurrence")
    
    return "\n".join(lines)
