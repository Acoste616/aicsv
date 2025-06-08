#!/usr/bin/env python3
"""
Łatwy launcher dla zoptymalizowanego bookmark processora
Pozwala wybrać model i uruchomić z optymalnymi ustawieniami
"""

import sys
import os
from bookmark_processor_fixed import OptimizedBookmarkProcessor, test_llm_connection

# Konfiguracje modeli z optymalnymi ustawieniami
MODEL_CONFIGS = {
    "mistral-7b": {
        "name": "mistralai/mistral-7b-instruct-v0.3",
        "temperature": 0.3,
        "max_tokens": 800,
        "description": "🥇 Mistral 7B - najlepszy dla RTX 4050",
        "vram": "~4GB"
    },
    "llama-3.2": {
        "name": "llama-3.2-7b-instruct.gguf", 
        "temperature": 0.4,
        "max_tokens": 900,
        "description": "🥈 Llama 3.2 7B - dobra alternatywa",
        "vram": "~5GB"
    },
    "phi-3": {
        "name": "phi-3-medium-4k-instruct.gguf",
        "temperature": 0.2,
        "max_tokens": 700,
        "description": "🥉 Phi-3 Medium - szybka opcja",
        "vram": "~7GB"
    },
    "qwen-3": {
        "name": "qwen-3-8b-instruct.gguf",
        "temperature": 0.25,
        "max_tokens": 850,
        "description": "🤖 Qwen 3 8B - dobry w reasoning",
        "vram": "~6GB"
    },
    "llama-3.1": {
        "name": "meta-llama-3.1-8b-instruct-hf",  # STARY MODEL - może nie działać!
        "temperature": 0.2,
        "max_tokens": 750,
        "description": "⚠️ Llama 3.1 8B - oryginalny (może nie działać)",
        "vram": "~6GB"
    }
}

def print_header():
    """Drukuje nagłówek programu"""
    print("🚀 ZOPTYMALIZOWANY BOOKMARK PROCESSOR")
    print("=" * 50)
    print("Wybierz model LLM dla analizy Twoich zakładek:\n")

def print_models():
    """Drukuje dostępne modele"""
    for i, (key, config) in enumerate(MODEL_CONFIGS.items(), 1):
        print(f"{i}. {config['description']}")
        print(f"   📦 Model: {config['name']}")
        print(f"   💾 VRAM: {config['vram']}")
        print(f"   🌡️ Temperature: {config['temperature']}")
        print()

def get_user_choice():
    """Pobiera wybór użytkownika"""
    while True:
        try:
            choice = input("Wybierz numer modelu (1-5) lub 'q' aby wyjść: ").strip()
            
            if choice.lower() == 'q':
                print("👋 Do widzenia!")
                sys.exit(0)
                
            choice_num = int(choice)
            if 1 <= choice_num <= len(MODEL_CONFIGS):
                return list(MODEL_CONFIGS.keys())[choice_num - 1]
            else:
                print(f"❌ Wybierz numer między 1 a {len(MODEL_CONFIGS)}")
                
        except ValueError:
            print("❌ Wprowadź poprawny numer")

def configure_processor(model_key):
    """Konfiguruje processor z wybranym modelem"""
    config = MODEL_CONFIGS[model_key]
    
    print(f"\n🔧 Konfiguruję processor z modelem: {config['description']}")
    print(f"📋 Szczegóły:")
    print(f"   • Model: {config['name']}")
    print(f"   • Temperature: {config['temperature']}")
    print(f"   • Max tokens: {config['max_tokens']}")
    print(f"   • VRAM: {config['vram']}")
    
    # Stwórz processor
    processor = OptimizedBookmarkProcessor()
    
    # Skonfiguruj z optymalnymi ustawieniami
    processor.llm_config.update({
        "model_name": config["name"],
        "temperature": config["temperature"], 
        "max_tokens": config["max_tokens"]
    })
    
    return processor

def main():
    """Główna funkcja"""
    print_header()
    print_models()
    
    # Pobierz wybór użytkownika
    model_key = get_user_choice()
    
    # Test połączenia
    print("\n🔌 Sprawdzam połączenie z LM Studio...")
    if not test_llm_connection():
        print("❌ LM Studio nie jest dostępne!")
        print("💡 Upewnij się że:")
        print("   1. LM Studio jest uruchomione")
        print("   2. Serwer lokalny działa (localhost:1234)")
        print("   3. Model jest załadowany")
        return
    
    # Skonfiguruj processor
    processor = configure_processor(model_key)
    
    # Sprawdź plik CSV
    csv_file = 'bookmarks1.csv'
    if not os.path.exists(csv_file):
        print(f"❌ Plik {csv_file} nie istnieje!")
        print("💡 Upewnij się że plik znajduje się w tym katalogu")
        return
    
    print(f"\n📁 Znaleziono plik: {csv_file}")
    print("🎯 Rozpoczynam analizę z optymalnymi ustawieniami...")
    print("💡 Naciśnij Ctrl+C aby przerwać w dowolnym momencie\n")
    
    # Uruchom przetwarzanie
    try:
        processor.process_bookmarks_advanced(csv_file)
        print("\n🎉 Analiza zakończona!")
        print(f"📊 Wyniki zapisane w: {processor.knowledge_checkpoint_file}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Przerwano przez użytkownika")
        processor.save_checkpoint()
        print("💾 Stan został zapisany")
        
    except Exception as e:
        print(f"\n❌ Błąd: {e}")
        processor.save_checkpoint()
        print("💾 Stan został zapisany")
        
    finally:
        if processor.extractor:
            processor.extractor.close()
        print("✅ Zakończono pracę")

if __name__ == "__main__":
    main() 