#!/usr/bin/env python3
"""
Główny skrypt do uruchomienia analizy zakładek
"""

import sys
from pathlib import Path
from config import LLM_CONFIG
import requests

def check_llm_connection():
    """Sprawdza połączenie z LM Studio"""
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ LM Studio dostępne")
            models = response.json()
            if models.get('data'):
                print(f"📌 Załadowany model: {models['data'][0]['id']}")
                return True
    except:
        pass
    
    print("❌ LM Studio niedostępne!")
    print("\n💡 Instrukcje:")
    print("1. Uruchom LM Studio")
    print("2. Załaduj model: Mistral 7B Instruct v0.3 (Q4_K_M)")
    print("3. Uruchom serwer lokalny (port 1234)")
    return False

def main():
    print("🚀 SYSTEM ANALIZY ZAKŁADEK Z TWITTERA")
    print("=" * 50)
    
    # Sprawdź LLM
    if not check_llm_connection():
        sys.exit(1)
    
    # Sprawdź plik CSV
    csv_file = "bookmarks_cleaned.csv"
    if not Path(csv_file).exists():
        print(f"❌ Brak pliku {csv_file}")
        print("\n💡 Najpierw uruchom:")
        print("python csv_cleaner_and_prep.py")
        sys.exit(1)
    
    # Uruchom analizę
    print(f"\n📋 Plik wejściowy: {csv_file}")
    
    choice = input("\n🤔 Rozpocząć analizę? (t/n): ")
    if choice.lower() != 't':
        print("❌ Anulowano")
        sys.exit(0)
    
    print("\n⏳ Rozpoczynam analizę...")
    print("💡 Możesz przerwać w dowolnym momencie (Ctrl+C)\n")
    
    from fixed_master_pipeline import FixedMasterPipeline
    
    try:
        pipeline = FixedMasterPipeline()
        result = pipeline.process_csv(csv_file)
        
        if result['successful'] > 0:
            print(f"\n✅ SUKCES! Przeanalizowano {result['successful']} zakładek")
            print(f"📁 Wyniki zapisane w: {result['output_file']}")
        else:
            print("\n❌ Nie udało się przeanalizować żadnej zakładki")
            
    except KeyboardInterrupt:
        print("\n⚠️ Przerwano przez użytkownika")
    except Exception as e:
        print(f"\n❌ Błąd: {e}")

if __name__ == "__main__":
    main() 