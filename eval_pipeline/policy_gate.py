#!/usr/bin/env python3
"""
Policy Gate - Sanitizes PII from tool outputs before they reach the model.

VERSION: v0.9-buggy-regex

KNOWN BUG: The regex patterns are too restrictive and miss common PII formats.
This is an intentional bug for demonstration purposes.
"""

import re
import copy
from typing import Dict, Any, Tuple

# Gate version for tracking
GATE_VERSION = "v0.9-buggy-regex"


def _sanitize_name_in_text(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Attempt to sanitize patient names in text.
    
    ❌ BUG: Only catches "Patient Name: X" format
    ❌ MISSES: "Patient X, DOB..." format (common in EHR exports)
    
    Args:
        text: Text that may contain PII
        
    Returns:
        Tuple of (sanitized_text, decision_info)
    """
    decision = {
        "checked_patterns": [],
        "redacted": False,
        "original_text_preview": text[:100] if text else None
    }
    
    # ❌ BUG: This pattern is too restrictive!
    # Only matches "Patient Name: John Smith" format
    if "Patient Name:" in text:
        pattern = r"Patient Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"
        decision["checked_patterns"].append({
            "pattern": pattern,
            "matched": bool(re.search(pattern, text))
        })
        
        if re.search(pattern, text):
            text = re.sub(pattern, "Patient Name: [REDACTED]", text)
            decision["redacted"] = True
    else:
        # ❌ BUG: If "Patient Name:" is not present, we don't check at all!
        # This misses formats like "Patient John Smith, DOB..."
        decision["checked_patterns"].append({
            "pattern": "Patient Name: prefix check",
            "matched": False,
            "note": "No 'Patient Name:' prefix found - skipping sanitization"
        })
    
    return text, decision


def _sanitize_dob_in_text(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Attempt to sanitize dates of birth in text.
    
    ❌ BUG: Only catches "DOB: MM/DD/YYYY" format
    ❌ MISSES: "DOB MM/DD/YYYY" format (no colon)
    
    Args:
        text: Text that may contain DOB
        
    Returns:
        Tuple of (sanitized_text, decision_info)
    """
    decision = {
        "checked_patterns": [],
        "redacted": False
    }
    
    # ❌ BUG: Requires "DOB:" with colon
    # Misses "DOB 03/15/1978" format (space instead of colon)
    if "DOB:" in text:
        pattern = r"DOB:\s*(\d{2}/\d{2}/\d{4})"
        decision["checked_patterns"].append({
            "pattern": pattern,
            "matched": bool(re.search(pattern, text))
        })
        
        if re.search(pattern, text):
            text = re.sub(pattern, "DOB: [REDACTED]", text)
            decision["redacted"] = True
    else:
        # ❌ BUG: Doesn't check for "DOB " (space) format
        decision["checked_patterns"].append({
            "pattern": "DOB: prefix check",
            "matched": False,
            "note": "No 'DOB:' prefix found - skipping DOB sanitization"
        })
    
    return text, decision


def _sanitize_patient_id(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Attempt to sanitize patient IDs in text.
    
    Args:
        text: Text that may contain patient IDs
        
    Returns:
        Tuple of (sanitized_text, decision_info)
    """
    decision = {
        "checked_patterns": [],
        "redacted": False
    }
    
    # This one actually works correctly
    pattern = r"P-\d{6}"
    decision["checked_patterns"].append({
        "pattern": pattern,
        "matched": bool(re.search(pattern, text))
    })
    
    if re.search(pattern, text):
        text = re.sub(pattern, "[PATIENT_ID_REDACTED]", text)
        decision["redacted"] = True
    
    return text, decision


def policy_gate(tool_payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Apply PII sanitization policy to a tool payload.
    
    This is the main entry point for the policy gate.
    It should sanitize all PII before the payload is used.
    
    ❌ KNOWN BUGS in v0.9-buggy-regex:
    - Name sanitization only works for "Patient Name: X" format
    - DOB sanitization only works for "DOB: X" format
    - Notes field sanitization misses common EHR export formats
    
    Args:
        tool_payload: The raw tool result to sanitize
        
    Returns:
        Tuple of (redacted_payload, gate_decision)
    """
    # Deep copy to avoid modifying original
    redacted = copy.deepcopy(tool_payload)
    
    gate_decision = {
        "gate_version": GATE_VERSION,
        "tool": tool_payload.get("tool"),
        "actions": [],
        "fields_checked": [],
        "pii_found": False,
        "pii_redacted": False,
        "potential_leak": False
    }
    
    payload = redacted.get("payload", {})
    
    # Sanitize 'name' field directly (this works)
    if "name" in payload:
        original_name = payload["name"]
        payload["name"] = "[NAME_REDACTED]"
        gate_decision["actions"].append({
            "field": "name",
            "action": "redacted",
            "original": original_name
        })
        gate_decision["pii_found"] = True
        gate_decision["pii_redacted"] = True
        gate_decision["fields_checked"].append("name")
    
    # Sanitize 'notes' field - THIS IS WHERE THE BUG MANIFESTS
    if "notes" in payload:
        notes = payload["notes"]
        gate_decision["fields_checked"].append("notes")
        
        # Try to sanitize name in notes
        notes, name_decision = _sanitize_name_in_text(notes)
        gate_decision["actions"].append({
            "field": "notes",
            "action": "name_sanitization",
            "decision": name_decision
        })
        
        # Try to sanitize DOB in notes
        notes, dob_decision = _sanitize_dob_in_text(notes)
        gate_decision["actions"].append({
            "field": "notes",
            "action": "dob_sanitization", 
            "decision": dob_decision
        })
        
        # Try to sanitize patient ID in notes
        notes, pid_decision = _sanitize_patient_id(notes)
        gate_decision["actions"].append({
            "field": "notes",
            "action": "patient_id_sanitization",
            "decision": pid_decision
        })
        
        payload["notes"] = notes
        
        # Check if any PII might have leaked through
        # This is a secondary check that detects the bug
        if name_decision.get("redacted") or dob_decision.get("redacted"):
            gate_decision["pii_redacted"] = True
        
        # ❌ BUG: We don't properly detect that PII leaked through!
        # The notes field still contains "Patient John Smith, DOB 03/15/1978"
        # but we don't flag it because our patterns didn't match
    
    redacted["payload"] = payload
    
    return redacted, gate_decision


def get_gate_version() -> str:
    """Return the current gate version."""
    return GATE_VERSION
