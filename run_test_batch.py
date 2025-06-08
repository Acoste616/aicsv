#!/usr/bin/env python3
"""
TEST BATCH RUNNER
Uruchamia naprawiony pipeline na małej próbce 5 wpisów
"""

import pandas as pd
from fixed_master_pipeline import FixedMasterPipeline
import json

def run_test_batch():
    """Uruchom test na pierwszych 5 wpisach."""
    print("🧪 TESTOWY BATCH - Pierwszych 5 wpisów")
    print("=" * 50)
    
    # Stwórz testowy CSV z pierwszymi 5 wpisami
    df = pd.read_csv('bookmarks_cleaned.csv')
    test_df = df.head(5)
    test_csv = 'test_batch_5.csv'
    test_df.to_csv(test_csv, index=False)
    
    print(f"Stworzony testowy CSV: {test_csv} ({len(test_df)} wpisów)")
    
    # Uruchom naprawiony pipeline
    pipeline = FixedMasterPipeline()
    
    # Konfiguruj na bardziej verbose
    pipeline.config["batch_size"] = 1  # Po jednym dla lepszego debugowania
    pipeline.config["checkpoint_frequency"] = 2  # Częste checkpointy
    
    print("\nUruchamiam naprawiony pipeline...")
    result = pipeline.process_csv(test_csv)
    
    print("\n" + "=" * 50)
    print("📊 WYNIKI TESTOWEGO BATCHA:")
    print(f"✅ Sukces: {result['successful']}/{result['total_processed']}")
    print(f"❌ Błędy: {result['failed']}")
    print(f"🔄 Duplikaty: {result['duplicates']}")
    print(f"📉 Problemy jakości: {result['quality_fails']}")
    print(f"⏱️ Czas: {result['processing_time']:.1f}s")
    print(f"📁 Output: {result['output_file']}")
    
    # Sprawdź output
    if result['successful'] > 0:
        print(f"\n🎉 SUKCES! {result['successful']} wpisów przetworzonych pomyślnie!")
        
        # Pokaż przykładowy wynik
        with open(result['output_file'], 'r', encoding='utf-8') as f:
            output_data = json.load(f)
            
        if output_data['entries']:
            print("\n📋 PRZYKŁADOWY WYNIK:")
            first_entry = output_data['entries'][0]
            print(f"Tytuł: {first_entry.get('title', 'BRAK')}")
            print(f"Kategoria: {first_entry.get('category', 'BRAK')}")
            print(f"Opis: {first_entry.get('short_description', 'BRAK')[:100]}...")
            
        return True
    else:
        print(f"\n❌ NIEPOWODZENIE! Żaden wpis nie został przetworzony pomyślnie.")
        return False

if __name__ == "__main__":
    success = run_test_batch()
    if success:
        print("\n✅ TEST BATCH PRZESZEDŁ! Można uruchomić pełny pipeline.")
    else:
        print("\n❌ TEST BATCH NIE PRZESZEDŁ! Sprawdź logi i błędy.") 