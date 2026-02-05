#!/usr/bin/env python3
"""
Leak Investigation Tool

Uses Retrace's provenance tracking to trace data leaks back to their source.
Demonstrates how AI companies can audit training data lineage.
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from visualization import (
    format_provenance_chain, 
    format_blast_radius, 
    format_remediation,
    print_header,
    print_section
)


@dataclass
class ProvenanceStep:
    """Represents one step in the provenance chain"""
    step: int
    operation: str
    location: str
    input_preview: str
    output_preview: str
    metadata: dict


class LeakInvestigator:
    """Uses Retrace provenance data to trace data leaks"""
    
    def __init__(self, trace_file: str):
        """Load the provenance trace from the training run"""
        self.trace_file = trace_file
        self.events = []
        self.session_id = "investigation_001"
        
        # Load trace file
        if os.path.exists(trace_file):
            with open(trace_file, 'r') as f:
                self.events = json.load(f)
            print(f"   Loaded {len(self.events)} provenance events")
        else:
            print(f"   ⚠ Trace file not found: {trace_file}")
    
    def find_leak_in_output(self, leaked_value: str) -> Optional[Dict]:
        """
        Find where the leaked value first appears in model output
        
        Searches through provenance events to find the GENERATE_LEAK event
        """
        print(f"   Searching for '{leaked_value}' in execution trace...")
        
        # Search backwards through events (most recent first)
        for event in reversed(self.events):
            if event.get("operation") == "GENERATE_LEAK":
                if leaked_value in str(event.get("output_preview", "")):
                    return {
                        "step": event["step"],
                        "location": event["location"],
                        "value": event.get("output_preview"),
                        "metadata": event.get("metadata", {})
                    }
            
            # Also check GENERATE_OUTPUT
            if event.get("operation") == "GENERATE_OUTPUT":
                if leaked_value in str(event.get("output_preview", "")):
                    return {
                        "step": event["step"],
                        "location": event["location"],
                        "value": event.get("output_preview"),
                        "metadata": event.get("metadata", {})
                    }
        
        return None
    
    def trace_provenance(self, from_step: int, leaked_value: str) -> List[ProvenanceStep]:
        """
        Trace provenance backwards from the leak to find its origin
        
        Walks through the event chain to reconstruct data lineage
        """
        chain = []
        current_step = from_step
        
        # Find all relevant events that contain or processed the leaked value
        relevant_events = []
        
        for event in self.events:
            # Check if this event is related to the leaked data
            input_preview = str(event.get("input_preview", ""))
            output_preview = str(event.get("output_preview", ""))
            
            if (leaked_value in input_preview or 
                leaked_value in output_preview or
                event.get("metadata", {}).get("leaked_from_index") or
                event.get("metadata", {}).get("bug_missed")):
                relevant_events.append(event)
        
        # Sort by step number (descending) to trace backwards
        relevant_events.sort(key=lambda e: e["step"], reverse=True)
        
        # Build the provenance chain
        for event in relevant_events:
            step = ProvenanceStep(
                step=event["step"],
                operation=event["operation"],
                location=event["location"],
                input_preview=event.get("input_preview", ""),
                output_preview=event.get("output_preview", ""),
                metadata=event.get("metadata", {})
            )
            chain.append(step)
        
        return chain
    
    def identify_root_cause(self, chain: List[ProvenanceStep]) -> Dict:
        """
        Analyze the provenance chain to identify the root cause
        
        Returns structured information about:
        - Where the data came from
        - Why sanitization failed
        - What other data might be affected
        """
        root_cause = {
            "source_file": None,
            "source_index": None,
            "patient_id": None,
            "bug_description": None,
            "sanitization_failure": None,
            "batch_number": None
        }
        
        for step in chain:
            metadata = step.metadata
            
            # Find source information
            if step.operation == "SANITIZE_OUTPUT":
                if metadata.get("bug_missed"):
                    root_cause["sanitization_failure"] = {
                        "step": step.step,
                        "location": step.location,
                        "reason": "Regex pattern too restrictive - only matches 'Patient Name:' format",
                        "input": step.input_preview,
                        "output": step.output_preview
                    }
                    root_cause["source_index"] = metadata.get("index")
            
            if step.operation == "GENERATE_LEAK":
                root_cause["source_index"] = metadata.get("leaked_from_index")
                root_cause["batch_number"] = metadata.get("leaked_from_batch")
                root_cause["source_type"] = metadata.get("source")
            
            if step.operation == "PREPROCESS_ITEM":
                if metadata.get("source") == "real_ehr_export":
                    root_cause["source_file"] = "data/medical_cases.json"
                    root_cause["patient_id"] = f"P-{447280 + (metadata.get('index', 0) - 2846)}"
        
        # Set bug description
        root_cause["bug_description"] = (
            "The sanitize_pii() function uses regex patterns that are too restrictive.\n"
            "   It only matches:\n"
            "      - 'Patient Name: [Name]' format\n"
            "      - 'DOB: MM/DD/YYYY' format\n"
            "      - 'Patient ID: P-XXXXXX' format\n"
            "   \n"
            "   But the EHR data uses:\n"
            "      - 'Patient [Name], DOB MM/DD/YYYY' format\n"
            "   \n"
            "   This mismatch causes PII to pass through unsanitized."
        )
        
        return root_cause
    
    def find_blast_radius(self, root_cause: Dict) -> List[Dict]:
        """
        Find all other examples affected by the same bug
        
        Searches for other real_ehr_export examples that weren't properly sanitized
        """
        affected = []
        
        for event in self.events:
            if event.get("operation") == "SANITIZE_OUTPUT":
                metadata = event.get("metadata", {})
                if metadata.get("bug_missed"):
                    affected.append({
                        "index": metadata.get("index"),
                        "preview": event.get("input_preview"),
                        "step": event["step"]
                    })
        
        return affected
    
    def generate_report(self, leaked_value: str) -> str:
        """
        Full investigation workflow:
        1. Find where leaked_value appears
        2. Trace its provenance backwards
        3. Identify root cause
        4. Find blast radius
        5. Generate formatted report
        """
        report_parts = []
        
        # Step 1: Find the leak
        print_section("Step 1: Locating leak in model output")
        leak_location = self.find_leak_in_output(leaked_value)
        
        if not leak_location:
            return "❌ Could not locate leaked value in trace"
        
        print(f"   ✓ Found at step {leak_location['step']}")
        print(f"   ✓ Location: {leak_location['location']}")
        
        # Step 2: Trace provenance
        print()
        print_section("Step 2: Tracing data provenance backwards")
        chain = self.trace_provenance(leak_location["step"], leaked_value)
        print(f"   ✓ Found {len(chain)} steps in provenance chain")
        
        # Step 3: Identify root cause
        print()
        print_section("Step 3: Analyzing root cause")
        root_cause = self.identify_root_cause(chain)
        print(f"   ✓ Source: {root_cause.get('source_file')}")
        print(f"   ✓ Index: {root_cause.get('source_index')}")
        print(f"   ✓ Bug identified in sanitize_pii()")
        
        # Step 4: Find blast radius
        print()
        print_section("Step 4: Calculating blast radius")
        affected = self.find_blast_radius(root_cause)
        print(f"   ✓ Found {len(affected)} other affected examples")
        
        # Step 5: Generate formatted report
        print()
        print_section("Step 5: Generating investigation report")
        
        report = []
        report.append(format_provenance_chain(chain, leaked_value, leak_location))
        report.append("")
        report.append(format_blast_radius(affected))
        report.append("")
        report.append(format_remediation(root_cause))
        
        return "\n".join(report)


def main():
    print_header("Retrace Data Leak Investigation")
    print()
    print("🔍 Investigating PII leak detected in model output...")
    print()
    
    # Path to trace file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    trace_file = os.path.join(script_dir, "..", "training_run.trace")
    
    print_section("Loading provenance trace")
    investigator = LeakInvestigator(trace_file)
    print()
    
    # The leaked value we're investigating
    leaked_value = "John Smith"
    
    print(f"Target: '{leaked_value}' found in model output")
    print("=" * 60)
    print()
    
    # Run investigation
    report = investigator.generate_report(leaked_value)
    
    print()
    print("=" * 60)
    print("                    INVESTIGATION REPORT")
    print("=" * 60)
    print()
    print(report)


if __name__ == "__main__":
    main()
