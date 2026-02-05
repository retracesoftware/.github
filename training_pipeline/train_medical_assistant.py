#!/usr/bin/env python3
"""
Medical AI Assistant Training Pipeline

This simulates fine-tuning an LLM on medical case data.
Contains an intentional PII sanitization bug for demonstration.
"""

import json
import re
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

# ============================================================================
# PROVENANCE TRACKING - Records every data transformation
# ============================================================================

class ProvenanceTracker:
    """Tracks data lineage through the pipeline"""
    
    def __init__(self):
        self.events = []
        self.step = 0
    
    def record(self, operation: str, location: str, 
               input_val: any, output_val: any, metadata: dict = None):
        """Record a data transformation event"""
        self.step += 1
        event = {
            "step": self.step,
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "location": location,
            "input_hash": hash(str(input_val)) if input_val else None,
            "output_hash": hash(str(output_val)) if output_val else None,
            "input_preview": str(input_val)[:100] if input_val else None,
            "output_preview": str(output_val)[:100] if output_val else None,
            "metadata": metadata or {}
        }
        self.events.append(event)
        return self.step
    
    def save(self, path: str):
        """Save provenance trace to file"""
        with open(path, 'w') as f:
            json.dump(self.events, f, indent=2)


# Global provenance tracker
provenance = ProvenanceTracker()


# ============================================================================
# DATA LOADING
# ============================================================================

class TrainingDataLoader:
    """Loads medical case data from JSON"""
    
    def __init__(self, provenance_tracker: ProvenanceTracker):
        self.provenance = provenance_tracker
    
    def load_dataset(self, path: str) -> List[Dict]:
        """
        Load dataset with mix of:
        - Real EHR data (contains PII: names, DOB, patient IDs)
        - Medical textbook excerpts (safe)
        - Synthetic cases (safe)
        """
        print(f"📂 Loading dataset from {path}...")
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Record the load operation
        self.provenance.record(
            operation="LOAD_DATASET",
            location=f"train_medical_assistant.py:load_dataset()",
            input_val=path,
            output_val=f"{len(data)} examples",
            metadata={"file": path, "count": len(data)}
        )
        
        # Count by source
        sources = {}
        for item in data:
            src = item.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        
        print(f"   Loaded {len(data)} examples:")
        for src, count in sources.items():
            print(f"      - {src}: {count} examples")
        
        return data
    
    def sanitize_pii(self, text: str, index: int) -> str:
        """
        ❌ BUG: This function should remove PII but has a regex bug
        
        It only catches format: "Patient Name: John Smith"
        It misses format: "Patient John Smith, DOB..."
        
        This is the critical bug that causes the leak
        """
        original_text = text
        
        # Record input
        step = self.provenance.record(
            operation="SANITIZE_INPUT",
            location="train_medical_assistant.py:sanitize_pii()",
            input_val=text,
            output_val=None,
            metadata={"index": index}
        )
        
        # ❌ Bug: This pattern is too restrictive!
        # It only matches "Patient Name: John Smith" format
        # It MISSES "Patient John Smith, DOB..." format
        if "Patient Name:" in text:
            pattern = r"Patient Name:\s*[\w\s]+"
            text = re.sub(pattern, "Patient Name: [REDACTED]", text)
        
        # ❌ Bug: Also only catches "DOB:" format, not "DOB " followed by date
        if "DOB:" in text:
            pattern = r"DOB:\s*\d{2}/\d{2}/\d{4}"
            text = re.sub(pattern, "DOB: [REDACTED]", text)
        
        # ❌ Bug: Patient ID pattern too specific
        if "Patient ID:" in text:
            pattern = r"Patient ID:\s*P-\d+"
            text = re.sub(pattern, "Patient ID: [REDACTED]", text)
        
        # Record output - note if unchanged (potential leak!)
        was_sanitized = text != original_text
        self.provenance.record(
            operation="SANITIZE_OUTPUT",
            location="train_medical_assistant.py:sanitize_pii()",
            input_val=original_text,
            output_val=text,
            metadata={
                "index": index,
                "was_sanitized": was_sanitized,
                "bug_missed": not was_sanitized and any(
                    indicator in original_text 
                    for indicator in ["Patient ", "DOB ", "P-"]
                )
            }
        )
        
        return text  # ❌ Returns unchanged if patterns don't match!
    
    def preprocess_batch(self, batch: List[Dict], batch_num: int) -> List[Dict]:
        """Apply sanitization to each example"""
        print(f"   🔄 Processing batch {batch_num} ({len(batch)} examples)...")
        
        processed = []
        for item in batch:
            # Record batch processing
            self.provenance.record(
                operation="PREPROCESS_ITEM",
                location="train_medical_assistant.py:preprocess_batch()",
                input_val=item,
                output_val=None,
                metadata={
                    "batch": batch_num, 
                    "index": item.get("index"),
                    "source": item.get("source")
                }
            )
            
            # Apply sanitization
            sanitized_text = self.sanitize_pii(item["text"], item.get("index", -1))
            
            processed_item = {
                "text": sanitized_text,
                "source": item.get("source"),
                "index": item.get("index"),
                "original_had_pii": item.get("source") == "real_ehr_export"
            }
            processed.append(processed_item)
        
        return processed


# ============================================================================
# MODEL TRAINING (SIMULATED)
# ============================================================================

class MockFineTuner:
    """Simulates model training and generation"""
    
    def __init__(self, provenance_tracker: ProvenanceTracker):
        self.training_data = []  # Store what we trained on
        self.provenance = provenance_tracker
        self.batches_trained = 0
    
    def train_batch(self, batch: List[Dict], batch_num: int):
        """Simulate training - store the batch data"""
        self.batches_trained += 1
        
        # Record training
        self.provenance.record(
            operation="TRAIN_BATCH",
            location="train_medical_assistant.py:train_batch()",
            input_val=f"Batch {batch_num} with {len(batch)} items",
            output_val=f"Model updated with batch {batch_num}",
            metadata={
                "batch_num": batch_num,
                "batch_size": len(batch),
                "sources": list(set(item.get("source") for item in batch))
            }
        )
        
        # Store training data (this is what causes the leak!)
        for item in batch:
            self.training_data.append({
                "text": item["text"],
                "source": item.get("source"),
                "index": item.get("index"),
                "batch": batch_num
            })
    
    def generate(self, prompt: str) -> str:
        """
        Simulate generation that "leaks" training data
        
        In reality, LLMs can memorize and regurgitate training data.
        We simulate this by returning text from training_data.
        """
        self.provenance.record(
            operation="GENERATE_INPUT",
            location="train_medical_assistant.py:generate()",
            input_val=prompt,
            output_val=None,
            metadata={"prompt_length": len(prompt)}
        )
        
        # Simulate the model "memorizing" training data
        # Find a training example that relates to the prompt
        response_parts = []
        
        # Start with a reasonable response
        response_parts.append("Based on similar cases in my training, ")
        
        # ❌ LEAK: Model regurgitates training data including unsanitized PII
        # Find examples from real_ehr_export that weren't properly sanitized
        for item in self.training_data:
            if item.get("source") == "real_ehr_export":
                # Check if this item still contains PII (sanitization failed)
                if "Patient " in item["text"] and "DOB" in item["text"]:
                    # This is the leak!
                    leaked_text = item["text"]
                    response_parts.append(f"I recall a case: {leaked_text[:200]}")
                    
                    # Record the leak
                    self.provenance.record(
                        operation="GENERATE_LEAK",
                        location="train_medical_assistant.py:generate()",
                        input_val=item,
                        output_val=leaked_text[:200],
                        metadata={
                            "leaked_from_index": item.get("index"),
                            "leaked_from_batch": item.get("batch"),
                            "source": item.get("source"),
                            "contains_pii": True
                        }
                    )
                    break
        
        response = " ".join(response_parts)
        
        self.provenance.record(
            operation="GENERATE_OUTPUT",
            location="train_medical_assistant.py:generate()",
            input_val=prompt,
            output_val=response,
            metadata={"response_length": len(response)}
        )
        
        return response


# ============================================================================
# MAIN TRAINING FLOW
# ============================================================================

def main():
    """
    Main training pipeline:
    1. Load dataset from medical_cases.json
    2. Process in batches of 32
    3. For each batch: apply sanitize_pii (which has the bug)
    4. "Train" the model (store the data)
    5. Generate a test output
    6. Output should contain leaked PII
    """
    print("=" * 60)
    print("🏥 Medical AI Assistant Training Pipeline")
    print("=" * 60)
    print()
    
    # Initialize components
    loader = TrainingDataLoader(provenance)
    model = MockFineTuner(provenance)
    
    # Load dataset
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data", "medical_cases.json")
    dataset = loader.load_dataset(data_path)
    print()
    
    # Process in batches
    batch_size = 32
    print(f"🔄 Processing {len(dataset)} examples in batches of {batch_size}...")
    print()
    
    for i in range(0, len(dataset), batch_size):
        batch_num = i // batch_size + 1
        batch = dataset[i:i + batch_size]
        
        # Preprocess (apply sanitization - which has the bug)
        processed_batch = loader.preprocess_batch(batch, batch_num)
        
        # Train on the batch
        model.train_batch(processed_batch, batch_num)
    
    print()
    print(f"✅ Training complete! Processed {model.batches_trained} batches.")
    print()
    
    # Test generation
    print("=" * 60)
    print("🧪 Testing model generation...")
    print("=" * 60)
    print()
    
    test_prompt = "Tell me about a patient case involving hypertension treatment."
    print(f"📝 Prompt: {test_prompt}")
    print()
    
    response = model.generate(test_prompt)
    
    print("🤖 Model Response:")
    print("-" * 40)
    print(response)
    print("-" * 40)
    print()
    
    # Check for PII leak
    pii_indicators = ["John Smith", "Mary Johnson", "DOB 03/15/1978", "P-447281"]
    leaked = [pii for pii in pii_indicators if pii in response]
    
    if leaked:
        print("⚠️  WARNING: Potential PII leak detected!")
        print(f"   Found: {leaked}")
        print()
        print("   This data should have been sanitized during preprocessing!")
        print("   Investigation required to find root cause.")
    
    # Save provenance trace
    trace_path = os.path.join(script_dir, "..", "training_run.trace")
    provenance.save(trace_path)
    print()
    print(f"📊 Provenance trace saved to: {trace_path}")
    print(f"   Recorded {len(provenance.events)} events")
    
    return response, leaked


if __name__ == "__main__":
    main()
