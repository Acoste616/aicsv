#!/usr/bin/env python3
"""
TEST PARALLEL PIPELINE
Demonstracja możliwości równoległego przetwarzania
"""

import time
from pathlib import Path
from fixed_master_pipeline import ParallelMasterPipeline

def test_performance_comparison():
    """Porównanie wydajności różnych konfiguracji"""
    
    csv_file = "bookmarks_cleaned.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ Plik {csv_file} nie istnieje!")
        return
    
    print("🔬 TEST RÓWNOLEGŁEGO PRZETWARZANIA")
    print("=" * 60)
    
    # Test 1: Małe batche, mało workerów
    print("\n📊 Test 1: Batch size=5, Workers=3")
    pipeline1 = ParallelMasterPipeline(batch_size=5, max_workers=3)
    start1 = time.time()
    result1 = pipeline1.process_csv(csv_file)
    time1 = time.time() - start1
    
    # Test 2: Średnie batche, średnio workerów  
    print("\n📊 Test 2: Batch size=10, Workers=5")
    pipeline2 = ParallelMasterPipeline(batch_size=10, max_workers=5)
    start2 = time.time()
    result2 = pipeline2.process_csv(csv_file)
    time2 = time.time() - start2
    
    # Test 3: Duże batche, dużo workerów
    print("\n📊 Test 3: Batch size=20, Workers=10")
    pipeline3 = ParallelMasterPipeline(batch_size=20, max_workers=10)
    start3 = time.time()
    result3 = pipeline3.process_csv(csv_file)
    time3 = time.time() - start3
    
    # Podsumowanie
    print("\n" + "=" * 60)
    print("📈 PODSUMOWANIE WYDAJNOŚCI:")
    print(f"""
Test 1 (5/3):
  - Czas: {time1/60:.2f} min
  - Prędkość: {result1['throughput_per_minute']:.1f} tweets/min
  - Sukces: {result1['successful']}/{result1['total_processed']}

Test 2 (10/5):
  - Czas: {time2/60:.2f} min  
  - Prędkość: {result2['throughput_per_minute']:.1f} tweets/min
  - Sukces: {result2['successful']}/{result2['total_processed']}

Test 3 (20/10):
  - Czas: {time3/60:.2f} min
  - Prędkość: {result3['throughput_per_minute']:.1f} tweets/min
  - Sukces: {result3['successful']}/{result3['total_processed']}

🏆 Najszybsza konfiguracja: Test {1 if time1 <= min(time2, time3) else (2 if time2 <= time3 else 3)}
🚀 Przyśpieszenie względem Test 1: {time1/time3:.1f}x
    """)

def test_rate_limiting():
    """Test rate limiting dla różnych API"""
    
    print("\n🔒 TEST RATE LIMITING")
    print("=" * 60)
    
    from fixed_master_pipeline import RateLimiter
    
    rate_limiter = RateLimiter()
    
    # Symuluj wywołania API
    apis = ["openai", "anthropic", "google", "local"]
    
    for api in apis:
        print(f"\n📡 Testing {api} rate limits...")
        start_time = time.time()
        
        # Spróbuj wykonać 10 wywołań
        for i in range(10):
            rate_limiter.wait_if_needed(api)
            rate_limiter.acquire(api)
            # Symuluj krótkie przetwarzanie
            time.sleep(0.1)
            rate_limiter.release(api)
            
            if i % 3 == 0:
                elapsed = time.time() - start_time
                print(f"  Call {i+1}: {elapsed:.2f}s elapsed")
        
        total_time = time.time() - start_time
        print(f"  Total time for 10 calls: {total_time:.2f}s")

def main():
    """Główna funkcja testowa"""
    
    print("🚀 PARALLEL PIPELINE - DEMO")
    print("=" * 60)
    
    # Quick test
    print("\n⚡ QUICK TEST - Optymalna konfiguracja")
    pipeline = ParallelMasterPipeline(batch_size=15, max_workers=8)
    
    csv_file = "bookmarks_cleaned.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ Plik {csv_file} nie istnieje!")
        return
    
    print(f"Batch size: 15, Max workers: 8")
    print("Starting processing...")
    
    result = pipeline.process_csv(csv_file)
    
    if result["success"]:
        print(f"""
✅ PRZETWARZANIE ZAKOŃCZONE!

📊 Statystyki:
- Przetworzone: {result['total_processed']} tweetów
- Sukces: {result['successful']} ({result['successful']/result['total_processed']*100:.1f}%)
- Błędy: {result['failed']}
- Czas: {result['processing_time']/60:.1f} minut
- Prędkość: {result['throughput_per_minute']:.1f} tweets/min

🎯 Treści multimodalne:
- Obrazy: {result['images_processed']}
- Nitki: {result['threads_collected']}  
- Wideo: {result['videos_analyzed']}

📁 Wynik zapisany w: {result['output_file']}
        """)
    
    # Opcjonalne testy wydajności
    print("\n" + "=" * 60)
    response = input("Czy chcesz uruchomić pełne testy wydajności? (t/n): ")
    
    if response.lower() == 't':
        test_performance_comparison()
        test_rate_limiting()

if __name__ == "__main__":
    main()