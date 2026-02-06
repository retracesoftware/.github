#!/usr/bin/env python3
"""
Policy Gate — PII Sanitization Layer

This module provides sanitization for tool outputs before they
reach the model context or are stored in transcripts.
"""

import re
from typing import Tuple, Dict, Any, Optional

__version__ = "1.2.0"


def _sanitize_name_in_text(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Attempt to sanitize patient names in free text.

    Returns:
        Tuple of (sanitized_text, metadata)
    """
    metadata = {"names_redacted": 0, "pattern_used": None}
    result = text

    # BUG: This pattern only matches "Patient Name: <name>" format!
    # It will miss inline formats like "Patient John Smith, DOB..."
    pattern = r"Patient Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"
    match = re.search(pattern, text)

    if match:
        name = match.group(1)
        result = text.replace(name, "[REDACTED_NAME]")
        metadata["names_redacted"] = 1
        metadata["pattern_used"] = pattern
        return result, metadata

    # No match found - return text unchanged
    # This is where the bug manifests: "Patient John Smith, DOB..."
    # does NOT match the pattern above, so PII passes through!
    result = text
    return result, metadata


def _sanitize_dob_in_text(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Sanitize date of birth patterns in text.

    Matches formats like: DOB 03/15/1978, DOB: 1978-03-15, etc.
    """
    metadata = {"dobs_redacted": 0}

    # Match DOB followed by various date formats
    patterns = [
        r"DOB[:\s]+(\d{2}/\d{2}/\d{4})",
        r"DOB[:\s]+(\d{4}-\d{2}-\d{2})",
        r"Date of Birth[:\s]+(\d{2}/\d{2}/\d{4})",
    ]

    result = text
    for pattern in patterns:
        matches = re.findall(pattern, result, re.IGNORECASE)
        for match in matches:
            result = result.replace(match, "[REDACTED_DOB]")
            metadata["dobs_redacted"] += 1

    return result, metadata


def _sanitize_ids(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Sanitize patient and record IDs.
    """
    metadata = {"ids_redacted": 0}
    result = text

    # Patient ID pattern: P-NNNNNN
    patient_id_pattern = r"Patient ID:\s*(P-\d+)"
    matches = re.findall(patient_id_pattern, result)
    for match in matches:
        result = result.replace(match, "[REDACTED_PATIENT_ID]")
        metadata["ids_redacted"] += 1

    # Record ID pattern
    record_id_pattern = r"Record ID:\s*(\d+)"
    matches = re.findall(record_id_pattern, result)
    for match in matches:
        result = result.replace(match, "[REDACTED_RECORD_ID]")
        metadata["ids_redacted"] += 1

    return result, metadata


def sanitize(input_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Main sanitization entry point.

    Applies all PII sanitization rules to the input text.

    Args:
        input_text: Raw text that may contain PII

    Returns:
        Tuple of (sanitized_text, metadata_dict)
    """
    metadata = {
        "gate_version": __version__,
        "input_length": len(input_text),
        "sanitizations": {}
    }

    # Apply sanitization layers
    result = input_text

    # Layer 1: Names (this is where the bug is!)
    result, name_meta = _sanitize_name_in_text(result)
    metadata["sanitizations"]["names"] = name_meta

    # Layer 2: Dates of birth
    result, dob_meta = _sanitize_dob_in_text(result)
    metadata["sanitizations"]["dobs"] = dob_meta

    # Layer 3: IDs
    result, id_meta = _sanitize_ids(result)
    metadata["sanitizations"]["ids"] = id_meta

    metadata["output_length"] = len(result)
    metadata["was_modified"] = result != input_text

    return result, metadata


def check_for_pii(text: str) -> Optional[Dict[str, Any]]:
    """
    Check if text contains obvious PII patterns.

    Returns None if no PII detected, otherwise returns details.
    """
    issues = []

    # Check for name patterns (simplified)
    name_pattern = r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b"
    names = re.findall(name_pattern, text)
    if names:
        issues.append({"type": "potential_name", "values": names[:3]})

    # Check for DOB patterns
    dob_pattern = r"\b(\d{2}/\d{2}/\d{4})\b"
    dobs = re.findall(dob_pattern, text)
    if dobs:
        issues.append({"type": "potential_dob", "values": dobs})

    if issues:
        return {"pii_detected": True, "issues": issues}

    return None
