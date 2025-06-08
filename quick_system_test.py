#!/usr/bin/env python3
"""
QUICK SYSTEM TEST
Prosty test całego systemu przetwarzania CSV
"""

import sys
import time
from pathlib import Path

print("🧪 QUICK SYSTEM TEST")
print("=" * 50)

# Test 1: Import komponentów
print("\n1. Testowanie importów...")
try:
    from csv_cleaner_and_prep import CSVCleanerAndPrep
    print("✅ csv_cleaner_and_prep - OK")
except Exception as e:
    print(f"❌ csv_cleaner_and_prep - ERROR: {e}")

try:
    from content_extractor import ContentExtractor
    print("✅ content_extractor - OK")
except Exception as e:
    print(f"❌ content_extractor - ERROR: {e}")

try:
    from enhanced_content_processor import EnhancedContentProcessor
    print("✅ enhanced_content_processor - OK")
except Exception as e:
    print(f"❌ enhanced_content_processor - ERROR: {e}")

try:
    from master_processing_pipeline import MasterProcessingPipeline
    print("✅ master_processing_pipeline - OK")
except Exception as e:
    print(f"❌ master_processing_pipeline - ERROR: {e}")

# Test 2: Sprawdź pliki CSV
print("\n2. Sprawdzanie plików CSV...")
csv_files = [
    "bookmarks.csv",
    "bookmarks1.csv", 
    "bookmarks_cleaned.csv",
    "bookmarks1_cleaned.csv"
]

for csv_file in csv_files:
    if Path(csv_file).exists():
        size_kb = Path(csv_file).stat().st_size / 1024
        print(f"✅ {csv_file} - {size_kb:.1f} KB")
    else:
        print(f"❌ {csv_file} - BRAK")

# Test 3: Test połączenia z LLM
print("\n3. Test połączenia z LLM...")
try:
    import requests
    response = requests.get("http://localhost:1234/v1/models", timeout=5)
    if response.status_code == 200:
        print("✅ LLM lokalny - DOSTĘPNY")
        models = response.json()
        if 'data' in models:
            print(f"   Modele: {len(models['data'])}")
    else:
        print(f"❌ LLM lokalny - STATUS {response.status_code}")
except Exception as e:
    print(f"❌ LLM lokalny - ERROR: {e}")

# Test 4: Test pojedynczego procesowania
print("\n4. Test pojedynczego wpisu...")
try:
    # Najprostszy możliwy test
    from content_extractor import ContentExtractor
    extractor = ContentExtractor()
    
    test_url = "https://httpbin.org/html"
    content = extractor.extract_with_retry(test_url)
    
    if len(content) > 0:
        print(f"✅ Content extraction - OK ({len(content)} znaków)")
    else:
        print("❌ Content extraction - PUSTE")
        
    extractor.close()
    
except Exception as e:
    print(f"❌ Content extraction - ERROR: {e}")

# Test 5: Test EnhancedContentProcessor
print("\n5. Test Enhanced Content Processor...")
try:
    processor = EnhancedContentProcessor()
    
    # Test z prostym przykładem
    test_result = processor.process_single_item(
        url="https://httpbin.org/html",
        tweet_text="Test tweet content"
    )
    
    if test_result:
        print("✅ Enhanced processor - OK")
        print(f"   Wynik: {type(test_result)}")
    else:
        print("❌ Enhanced processor - BRAK WYNIKU")
        
    processor.close()
    
except Exception as e:
    print(f"❌ Enhanced processor - ERROR: {e}")

# Test 6: Sprawdź konfigurację pipeline
print("\n6. Test konfiguracji pipeline...")
try:
    pipeline = MasterProcessingPipeline()
    print("✅ Pipeline inicjalizacja - OK")
    print(f"   Batch size: {pipeline.config['batch_size']}")
    print(f"   Quality threshold: {pipeline.config['quality_threshold']}")
except Exception as e:
    print(f"❌ Pipeline inicjalizacja - ERROR: {e}")

# Podsumowanie
print("\n" + "=" * 50)
print("🎯 GOTOWOŚĆ SYSTEMU:")

# Sprawdź czy mamy wszystko co potrzeba
ready_components = []
csv_ready = any(Path(f).exists() for f in ["bookmarks_cleaned.csv", "bookmarks1_cleaned.csv"])
if csv_ready:
    ready_components.append("CSV")

try:
    requests.get("http://localhost:1234/v1/models", timeout=2)
    ready_components.append("LLM")
except:
    pass

if len(ready_components) >= 1:
    print(f"✅ System GOTOWY do uruchomienia!")
    print(f"   Dostępne komponenty: {', '.join(ready_components)}")
    
    if csv_ready:
        print("\n🚀 URUCHOM SYSTEM:")
        print("   python master_processing_pipeline.py")
else:
    print("❌ System NIE GOTOWY")
    print("   Brakuje kluczowych komponentów")

print("\n📋 STATUS: Test zakończony") 