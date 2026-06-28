"""
Response time profiler for CodeLens pipeline.
Measures each step: routing, judgment, retrieval, LLM, logging.
"""
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Dict

class Profiler:
    def __init__(self):
        self.timings: Dict[str, float] = {}
        self.start_times: Dict[str, float] = {}
    
    @contextmanager
    def measure(self, step_name: str):
        """Context manager to measure time for a specific step."""
        start = time.time()
        self.start_times[step_name] = start
        try:
            yield
        finally:
            elapsed = time.time() - start
            self.timings[step_name] = elapsed
            print(f"⏱️  {step_name}: {elapsed:.3f}s")
    
    def report(self) -> str:
        """Generate a summary report of all timings."""
        total = sum(self.timings.values())
        report = f"\n📊 PROFILING REPORT\n{'='*50}\n"
        
        for step, elapsed in sorted(self.timings.items(), key=lambda x: x[1], reverse=True):
            percent = (elapsed / total * 100) if total > 0 else 0
            bar = "█" * int(percent / 5)
            report += f"{step:.<30} {elapsed:.3f}s ({percent:>5.1f}%) {bar}\n"
        
        report += f"{'='*50}\nTotal: {total:.3f}s\n"
        return report

# Global profiler instance
profiler = Profiler()

def reset_profiler():
    """Reset profiler for next run."""
    profiler.timings.clear()
    profiler.start_times.clear()
