#!/usr/bin/env python3
"""
Tool implementations for the eval pipeline.

These simulate external API calls that return data which may contain PII.
The policy gate should sanitize these before they reach the model output.
"""

import json
import os
from typing import Dict, Any, Optional

# Load tool results data
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOL_RESULTS_PATH = os.path.join(_SCRIPT_DIR, "datasets", "tool_results.json")
_PII_EXPORT_PATH = os.path.join(_SCRIPT_DIR, "datasets", "pii_export.json")

_tool_results = None
_pii_records = None


def _load_tool_results() -> Dict:
    """Load tool results from JSON file."""
    global _tool_results
    if _tool_results is None:
        with open(_TOOL_RESULTS_PATH, 'r') as f:
            _tool_results = json.load(f)
    return _tool_results


def _load_pii_records() -> list:
    """Load PII records from JSON file."""
    global _pii_records
    if _pii_records is None:
        with open(_PII_EXPORT_PATH, 'r') as f:
            _pii_records = json.load(f)
    return _pii_records


def lookup_customer(customer_id: str) -> Dict[str, Any]:
    """
    Look up customer information by customer ID.
    
    Returns a structured payload containing customer data.
    WARNING: Payload may contain PII that must be sanitized by policy gate.
    
    Args:
        customer_id: The customer identifier (e.g., "C-1007")
        
    Returns:
        Dict containing tool name, customer_id, and payload with customer data
    """
    tool_results = _load_tool_results()
    
    lookup_data = tool_results.get("lookup_customer", {})
    
    if customer_id in lookup_data:
        return lookup_data[customer_id]
    
    # Return empty result for unknown customer
    return {
        "tool": "lookup_customer",
        "customer_id": customer_id,
        "payload": {
            "error": f"Customer {customer_id} not found",
            "source_file": None
        }
    }


def fetch_invoice(invoice_id: str) -> Dict[str, Any]:
    """
    Fetch invoice information by invoice ID.
    
    Returns a structured payload containing invoice data.
    Invoice data typically doesn't contain PII.
    
    Args:
        invoice_id: The invoice identifier (e.g., "INV-5001")
        
    Returns:
        Dict containing tool name, invoice_id, and payload with invoice data
    """
    tool_results = _load_tool_results()
    
    invoice_data = tool_results.get("fetch_invoice", {})
    
    if invoice_id in invoice_data:
        return invoice_data[invoice_id]
    
    # Return empty result for unknown invoice
    return {
        "tool": "fetch_invoice",
        "invoice_id": invoice_id,
        "payload": {
            "error": f"Invoice {invoice_id} not found"
        }
    }


def get_tool_by_name(tool_name: str):
    """Get tool function by name."""
    tools = {
        "lookup_customer": lookup_customer,
        "fetch_invoice": fetch_invoice
    }
    return tools.get(tool_name)


def call_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a tool by name with given arguments.
    
    Args:
        tool_name: Name of the tool to call
        args: Dictionary of arguments to pass to the tool
        
    Returns:
        Tool result dictionary
    """
    tool_fn = get_tool_by_name(tool_name)
    
    if tool_fn is None:
        return {
            "tool": tool_name,
            "payload": {
                "error": f"Unknown tool: {tool_name}"
            }
        }
    
    # Call the tool with appropriate arguments
    if tool_name == "lookup_customer":
        return tool_fn(args.get("customer_id", ""))
    elif tool_name == "fetch_invoice":
        return tool_fn(args.get("invoice_id", ""))
    else:
        return tool_fn(**args)


def get_pii_records_matching_pattern(pattern_type: str = "missing_patient_name_prefix") -> list:
    """
    Get PII records that match a specific pattern vulnerability.
    
    Used to calculate blast radius - other records affected by the same bug.
    
    Args:
        pattern_type: Type of pattern to match
        
    Returns:
        List of record_ids that would be affected by the bug
    """
    records = _load_pii_records()
    affected = []
    
    if pattern_type == "missing_patient_name_prefix":
        # Records where notes contain "Patient X, DOB" format (not "Patient Name: X")
        for record in records:
            notes = record.get("notes", "")
            # Check if notes uses the vulnerable format
            if "Patient Name:" not in notes and "Patient " in notes and "DOB" in notes:
                affected.append(record["record_id"])
    
    return affected
