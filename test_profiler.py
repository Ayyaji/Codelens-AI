#!/usr/bin/env python
"""Test script for profiler."""

from rag_core.pipeline import run_pipeline

if __name__ == "__main__":
    print("Testing CodeLens pipeline with profiling...\n")
    
    result = run_pipeline('I got a NameError', 'test_student', profile=True)
    
    print(f"\n✅ Query completed in {result['response_time']:.2f}s")
    print(f"Agent: {result['agent_used']}")
    print(f"Directive: {result['directive']}")
