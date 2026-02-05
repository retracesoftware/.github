#!/usr/bin/env python3
"""
Eval Pipeline Runner

Runs a simulated tool-using agent evaluation with Retrace recording.
Contains an intentional PII leak due to a policy gate bug.
"""

import json
import os
import re
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import call_tool, get_pii_records_matching_pattern
from policy_gate import policy_gate, get_gate_version


# ============================================================================
# Retrace Integration - Provenance Tracking
# ============================================================================

class ProvenanceTracker:
    """Tracks execution for provenance analysis."""
    
    def __init__(self):
        self.events = []
        self.step = 0
    
    def record(self, operation: str, location: str, data: Any, metadata: dict = None):
        """Record a provenance event."""
        self.step += 1
        self.events.append({
            "step": self.step,
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "location": location,
            "data_preview": str(data)[:200] if data else None,
            "metadata": metadata or {}
        })
        return self.step
    
    def save(self, path: str):
        """Save trace to file."""
        with open(path, 'w') as f:
            json.dump({
                "events": self.events,
                "total_steps": self.step,
                "crash_step": self.step,  # Last step before crash
                "version": "1.0"
            }, f, indent=2)


# Global provenance tracker (simulates Retrace recording)
provenance = ProvenanceTracker()


# ============================================================================
# Custom Exceptions
# ============================================================================

class EvalLeakDetected(RuntimeError):
    """Raised when PII is detected in eval output."""
    pass


# ============================================================================
# Eval Pipeline
# ============================================================================

class EvalPipeline:
    """Simulated tool-using agent evaluation pipeline."""
    
    def __init__(self):
        self.transcript: List[Dict[str, Any]] = []
        self.prompts: List[Dict] = []
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
    
    def load_prompts(self) -> List[Dict]:
        """Load evaluation prompts."""
        prompts_path = os.path.join(self.script_dir, "datasets", "eval_prompts.json")
        
        provenance.record(
            operation="LOAD_PROMPTS",
            location="run_eval.py:load_prompts()",
            data=prompts_path,
            metadata={"file": prompts_path}
        )
        
        with open(prompts_path, 'r') as f:
            self.prompts = json.load(f)
        
        print(f"📋 Loaded {len(self.prompts)} evaluation prompts")
        return self.prompts
    
    def parse_tool_call(self, prompt: str, prompt_data: Dict) -> Optional[Dict]:
        """
        Parse a prompt to determine which tool to call.
        Uses the expected_tool and expected_args from prompt data for determinism.
        """
        tool_name = prompt_data.get("expected_tool")
        tool_args = prompt_data.get("expected_args", {})
        
        if tool_name:
            provenance.record(
                operation="PARSE_TOOL_CALL",
                location="run_eval.py:parse_tool_call()",
                data={"tool": tool_name, "args": tool_args},
                metadata={"prompt_id": prompt_data.get("prompt_id")}
            )
            return {"tool": tool_name, "args": tool_args}
        
        return None
    
    def execute_tool(self, tool_call: Dict) -> Dict[str, Any]:
        """Execute a tool call and return the result."""
        tool_name = tool_call["tool"]
        tool_args = tool_call["args"]
        
        provenance.record(
            operation="TOOL_CALL_START",
            location="run_eval.py:execute_tool()",
            data={"tool": tool_name, "args": tool_args}
        )
        
        result = call_tool(tool_name, tool_args)
        
        provenance.record(
            operation="TOOL_CALL_RESULT",
            location="run_eval.py:execute_tool()",
            data=result,
            metadata={"tool": tool_name, "has_payload": "payload" in result}
        )
        
        return result
    
    def apply_policy_gate(self, tool_result: Dict) -> tuple[Dict, Dict]:
        """Apply the policy gate to sanitize PII from tool results."""
        provenance.record(
            operation="POLICY_GATE_INPUT",
            location="run_eval.py:apply_policy_gate()",
            data=tool_result,
            metadata={"gate_version": get_gate_version()}
        )
        
        # This is where the bug occurs - policy_gate fails to sanitize
        redacted_result, gate_decision = policy_gate(tool_result)
        
        provenance.record(
            operation="POLICY_GATE_OUTPUT",
            location="run_eval.py:apply_policy_gate()",
            data={"redacted": redacted_result, "decision": gate_decision},
            metadata={
                "gate_version": get_gate_version(),
                "pii_redacted": gate_decision.get("pii_redacted", False)
            }
        )
        
        return redacted_result, gate_decision
    
    def generate_response(self, prompt: str, tool_result: Dict) -> str:
        """
        Generate a simulated model response.
        
        For determinism, this directly uses content from the tool result.
        In a real eval, this would be LLM generation.
        """
        payload = tool_result.get("payload", {})
        tool_name = tool_result.get("tool", "unknown")
        
        provenance.record(
            operation="GENERATE_RESPONSE_START",
            location="run_eval.py:generate_response()",
            data={"prompt": prompt, "tool_result": tool_result}
        )
        
        if tool_name == "lookup_customer":
            # Generate response that includes the notes (which may contain PII)
            notes = payload.get("notes", "No notes available")
            response = f"Based on the customer record, here is the relevant information: {notes}"
        
        elif tool_name == "fetch_invoice":
            amount = payload.get("amount", "N/A")
            status = payload.get("status", "N/A")
            response = f"Invoice details: Amount ${amount}, Status: {status}"
        
        else:
            response = f"Tool result: {json.dumps(payload)}"
        
        provenance.record(
            operation="GENERATE_RESPONSE_END",
            location="run_eval.py:generate_response()",
            data=response,
            metadata={"response_length": len(response)}
        )
        
        return response
    
    def check_for_pii_leak(self, response: str) -> tuple[bool, List[str]]:
        """
        Check if the response contains PII that should have been redacted.
        
        Returns:
            Tuple of (has_leak, list of detected PII)
        """
        detected_pii = []
        
        # Check for name pattern
        if "John Smith" in response:
            detected_pii.append("John Smith")
        
        # Check for DOB pattern (MM/DD/YYYY)
        dob_pattern = r"\d{2}/\d{2}/\d{4}"
        dob_matches = re.findall(dob_pattern, response)
        for dob in dob_matches:
            if dob == "03/15/1978":  # The known leaked DOB
                detected_pii.append(dob)
        
        return len(detected_pii) > 0, detected_pii
    
    def run_eval(self):
        """
        Run the complete evaluation pipeline.
        
        Processes all prompts, applies tools, and checks for PII leaks.
        Raises EvalLeakDetected if PII is found in any response.
        """
        print("=" * 60)
        print("🔬 Starting Eval Pipeline")
        print("=" * 60)
        print()
        
        # Load prompts
        self.load_prompts()
        print()
        
        # Process each prompt
        for prompt_data in self.prompts:
            prompt_id = prompt_data["prompt_id"]
            prompt = prompt_data["prompt"]
            
            print(f"📝 Processing prompt {prompt_id}: {prompt[:50]}...")
            
            # Add user message to transcript
            self.transcript.append({
                "role": "user",
                "content": prompt,
                "prompt_id": prompt_id
            })
            
            # Parse tool call
            tool_call = self.parse_tool_call(prompt, prompt_data)
            
            if tool_call:
                # Execute tool
                tool_result = self.execute_tool(tool_call)
                
                # Store original for investigation
                original_tool_result = tool_result.copy()
                
                # Apply policy gate (this is where the bug occurs)
                redacted_result, gate_decision = self.apply_policy_gate(tool_result)
                
                # Add tool interaction to transcript
                self.transcript.append({
                    "role": "tool",
                    "tool_name": tool_call["tool"],
                    "tool_args": tool_call["args"],
                    "tool_result": redacted_result,
                    "gate_decision": gate_decision
                })
                
                # Generate response using (supposedly) sanitized result
                response = self.generate_response(prompt, redacted_result)
            else:
                response = "I don't have a tool to help with that request."
            
            # Add assistant response to transcript
            self.transcript.append({
                "role": "assistant",
                "content": response,
                "prompt_id": prompt_id
            })
            
            # Check for PII leak
            has_leak, detected_pii = self.check_for_pii_leak(response)
            
            if has_leak:
                print(f"   ⚠️  PII LEAK DETECTED!")
                
                # ============================================================
                # BREADCRUMB LOCALS - These will be found by the investigator
                # ============================================================
                
                # The leaked values
                leaked_value = "John Smith"
                leaked_dob = "03/15/1978"
                leaked_text = response
                
                # The tool payload that contained the PII
                leaked_tool_payload = original_tool_result
                
                # Source information
                leak_source = {
                    "source_file": "datasets/pii_export.json",
                    "record_id": 2847,
                    "patient_id": "P-447281"
                }
                
                # Gate information
                gate_version = get_gate_version()
                gate_decision_info = gate_decision
                
                # Blast radius - other records affected by same bug
                blast_radius_candidates = get_pii_records_matching_pattern(
                    "missing_patient_name_prefix"
                )
                
                # Regression test specification
                regression_test_spec = {
                    "test_name": "test_policy_gate_patient_dob_format",
                    "input_payload": {
                        "tool": "lookup_customer",
                        "customer_id": "C-1007",
                        "payload": {
                            "notes": "Patient John Smith, DOB 03/15/1978, diagnosed with hypertension."
                        }
                    },
                    "expected_behavior": "notes field should not contain 'John Smith' or DOB pattern",
                    "bug_location": "policy_gate.py:_sanitize_name_in_text()"
                }
                
                # Record the leak detection
                provenance.record(
                    operation="LEAK_DETECTED",
                    location="run_eval.py:run_eval()",
                    data={
                        "leaked_value": leaked_value,
                        "leaked_dob": leaked_dob,
                        "leaked_text": leaked_text,
                        "leak_source": leak_source,
                        "gate_version": gate_version,
                        "blast_radius_count": len(blast_radius_candidates)
                    },
                    metadata={
                        "prompt_id": prompt_id,
                        "is_crash_point": True
                    }
                )
                
                # Save provenance trace before raising
                trace_path = os.path.join(
                    self.script_dir, "..", "eval_run.trace"
                )
                provenance.save(trace_path)
                print(f"   📊 Provenance trace saved to: {trace_path}")
                
                # Raise exception (this is the crash anchor)
                raise EvalLeakDetected(
                    f"PII leak detected in response to prompt {prompt_id}: {detected_pii}"
                )
            
            print(f"   ✓ Response generated (no leak detected)")
        
        print()
        print("=" * 60)
        print("✅ Eval pipeline completed without leaks")
        print("=" * 60)


def main():
    """Main entry point for the eval pipeline."""
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        EVAL PIPELINE - Tool-Using Agent Evaluation         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    pipeline = EvalPipeline()
    
    try:
        pipeline.run_eval()
    except EvalLeakDetected as e:
        print()
        print("❌ " + "=" * 56)
        print(f"❌ EVAL FAILED: {e}")
        print("❌ " + "=" * 56)
        print()
        print("Investigation required. Run: python investigation/investigate_leak.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
