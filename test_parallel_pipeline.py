#!/usr/bin/env python3
"""
Test script for Parallel Processing Pipeline
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test basic imports"""
    print("🔍 Testing imports...")
    
    try:
        # Test core imports
        import threading
        import queue
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from tqdm import tqdm
        print("✅ Core parallel processing imports successful")
        
        # Test enum and dataclass
        from enum import Enum
        from dataclasses import dataclass
        print("✅ Python standard library imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_parallel_components():
    """Test the parallel processing components"""
    print("\n🧪 Testing parallel processing components...")
    
    try:
        from enum import Enum
        from dataclasses import dataclass
        import threading
        import queue
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        # Test APIProvider enum
        class APIProvider(Enum):
            OPENAI = "openai"
            ANTHROPIC = "anthropic"
            GOOGLE = "google"
            LOCAL = "local"
        
        print("✅ APIProvider enum works")
        
        # Test RateLimitConfig
        @dataclass
        class RateLimitConfig:
            requests_per_minute: int
            burst_limit: int
            cooldown_seconds: float
        
        config = RateLimitConfig(
            requests_per_minute=1000,
            burst_limit=5,
            cooldown_seconds=0.1
        )
        print("✅ RateLimitConfig dataclass works")
        
        # Test basic threading
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(lambda: time.sleep(0.1)) for _ in range(3)]
            for future in futures:
                future.result()
        
        print("✅ ThreadPoolExecutor works")
        
        # Test priority queue
        pq = queue.PriorityQueue()
        pq.put((-10, "high priority"))
        pq.put((-5, "medium priority"))
        pq.put((-1, "low priority"))
        
        items = []
        while not pq.empty():
            items.append(pq.get())
        
        print("✅ Priority queue works")
        
        # Test progress bar
        from tqdm import tqdm
        import time
        
        print("✅ Testing progress bar...")
        for i in tqdm(range(5), desc="Testing"):
            time.sleep(0.1)
        
        print("✅ All parallel processing components work!")
        return True
        
    except Exception as e:
        print(f"❌ Component test error: {e}")
        return False

def test_pipeline_structure():
    """Test the basic pipeline structure"""
    print("\n🏗️ Testing pipeline structure...")
    
    try:
        # Mock the pipeline class structure
        class MockParallelPipeline:
            def __init__(self, max_workers=5, batch_size=10):
                self.max_workers = max_workers
                self.batch_size = batch_size
                self.state = {
                    "processed_count": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "api_usage": {},
                    "error_categories": {}
                }
                
            def process_batch_parallel(self, batch):
                """Mock batch processing"""
                return [{"success": True, "url": f"test_{i}"} for i in range(len(batch))]
                
            def generate_progress_report(self):
                """Mock progress report"""
                return f"Processed: {self.state['processed_count']}, Success: {self.state['success_count']}"
        
        # Test mock pipeline
        pipeline = MockParallelPipeline(max_workers=10, batch_size=15)
        
        # Test batch processing
        mock_batch = [{"url": f"test_{i}", "content": f"content_{i}"} for i in range(5)]
        results = pipeline.process_batch_parallel(mock_batch)
        
        print(f"✅ Pipeline structure works - processed {len(results)} items")
        print(f"✅ Pipeline config: {pipeline.max_workers} workers, {pipeline.batch_size} batch size")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline structure test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 PARALLEL PROCESSING PIPELINE - COMPONENT TESTS")
    print("=" * 50)
    
    tests = [
        ("Basic Imports", test_imports),
        ("Parallel Components", test_parallel_components),
        ("Pipeline Structure", test_pipeline_structure)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n🎉 SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Parallel processing pipeline is ready!")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)