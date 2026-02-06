#!/usr/bin/env python3
"""
PII Detector — Output Scanning for Personal Information

Scans generated outputs for PII patterns and raises alerts
when sensitive data is detected in model responses.
"""

import re
from typing import Optional, Dict, Any, List


def scan_output(output_text: str, prompt_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Scan output text for PII patterns.

    Raises PIILeakDetected if PII is found in the output.
    """
    detected = []

    # Check for name patterns
    name_pattern = r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b"
    names = re.findall(name_pattern, output_text)

    # Filter out common non-name phrases
    excluded = {"Based On", "Patient Records", "Record ID", "Last Visit"}
    names = [n for n in names if n not in excluded]

    if names:
        detected.append({
            "type": "name",
            "values": names[:3],
            "severity": "high"
        })

    # Check for DOB patterns
    dob_pattern = r"\b(\d{2}/\d{2}/\d{4})\b"
    dobs = re.findall(dob_pattern, output_text)

    if dobs:
        detected.append({
            "type": "dob",
            "values": dobs,
            "severity": "high"
        })

    # Check for SSN patterns
    ssn_pattern = r"\b(\d{3}-\d{2}-\d{4})\b"
    ssns = re.findall(ssn_pattern, output_text)

    if ssns:
        detected.append({
            "type": "ssn",
            "values": ["[REDACTED]"] * len(ssns),
            "severity": "critical"
        })

    # If high-severity PII detected, raise exception
    if detected:
        high_severity = [d for d in detected if d["severity"] in ("high", "critical")]
        if high_severity:
            leaked_values = []
            for d in high_severity:
                leaked_values.extend(d["values"])

            raise PIILeakDetected(
                f"Leaked PII in response for prompt {prompt_id}: {', '.join(leaked_values[:2])}",
                prompt_id=prompt_id,
                leaked_values=leaked_values,
                detection_details=detected
            )

    return {
        "pii_detected": len(detected) > 0,
        "detections": detected,
        "prompt_id": prompt_id
    }


class PIILeakDetected(Exception):
    """Exception raised when PII is detected in output."""

    def __init__(self, message: str, prompt_id: Optional[int] = None,
                 leaked_values: Optional[List[str]] = None,
                 detection_details: Optional[List[Dict]] = None):
        super().__init__(message)
        self.prompt_id = prompt_id
        self.leaked_values = leaked_values or []
        self.detection_details = detection_details or []


def check_text_for_pii(text: str) -> bool:
    """Simple check if text contains PII. Returns True if PII found."""
    try:
        scan_output(text)
        return False
    except PIILeakDetected:
        return True


if __name__ == "__main__":
    # Test the detector
    test_texts = [
        "The patient is doing well.",
        "John Smith was born on 03/15/1978.",
        "Patient ID: P-123456",
    ]

    for text in test_texts:
        try:
            result = scan_output(text)
            print(f"OK: {text[:40]}...")
        except PIILeakDetected as e:
            print(f"LEAK: {e}")
