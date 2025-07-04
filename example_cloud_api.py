#!/usr/bin/env python3
"""
PRZYKŁAD UŻYCIA FIXED CONTENT PROCESSOR Z CLOUD APIs

Ten plik pokazuje jak używać nowej funkcjonalności cloud API w fixed_content_processor.py.
Obsługuje OpenAI, Anthropic, Google i lokalne LLM.
"""

import os
import logging
from fixed_content_processor import FixedContentProcessor

# Skonfiguruj logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Demonstracja użycia różnych providerów."""
    
    print("🚀 PRZYKŁAD UŻYCIA FIXED CONTENT PROCESSOR Z CLOUD APIs")
    print("="*60)
    
    # Dane testowe
    test_url = "https://x.com/aaditsh/status/1931041095317688786"
    test_tweet = "How to build an app from scratch using the latest AI workflows (76 mins)"
    test_content = "Article about building applications with AI workflows, including step-by-step guide and best practices."
    
    print(f"📄 Test URL: {test_url}")
    print(f"📝 Test Tweet: {test_tweet}")
    print(f"📋 Test Content: {test_content[:100]}...")
    print()
    
    # 1. UŻYCIE Z LOKALNYM LLM (domyślny)
    print("1️⃣ LOKALNY LLM")
    print("-" * 30)
    try:
        processor = FixedContentProcessor()
        result = processor.process_single_item(test_url, test_tweet, test_content)
        
        if result:
            print("✅ Sukces!")
            print(f"📋 Tytuł: {result.get('title', 'Brak')}")
            print(f"📝 Opis: {result.get('short_description', 'Brak')}")
            print(f"🏷️  Kategoria: {result.get('category', 'Brak')}")
        else:
            print("❌ Nieudane")
            
        processor.close()
    except Exception as e:
        print(f"❌ Błąd: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # 2. UŻYCIE Z OPENAI
    print("2️⃣ OPENAI GPT")
    print("-" * 30)
    
    # Możesz ustawić klucz API na kilka sposobów:
    
    # Sposób 1: Bezpośrednio w kodzie (NIE REKOMENDOWANY dla produkcji)
    # openai_key = "twoj-klucz-api"
    
    # Sposób 2: Zmienne środowiskowe (REKOMENDOWANY)
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if openai_key:
        try:
            processor = FixedContentProcessor(
                provider="openai",
                api_key=openai_key,
                model="gpt-3.5-turbo"  # Możesz też użyć "gpt-4"
            )
            
            result = processor.process_single_item(test_url, test_tweet, test_content)
            
            if result:
                print("✅ Sukces!")
                print(f"📋 Tytuł: {result.get('title', 'Brak')}")
                print(f"📝 Opis: {result.get('short_description', 'Brak')}")
                print(f"🏷️  Kategoria: {result.get('category', 'Brak')}")
            else:
                print("❌ Nieudane")
                
            processor.close()
        except Exception as e:
            print(f"❌ Błąd: {e}")
    else:
        print("⚠️  Brak klucza API. Ustaw zmienną środowiskową OPENAI_API_KEY")
    
    print("\n" + "="*60 + "\n")
    
    # 3. UŻYCIE Z ANTHROPIC
    print("3️⃣ ANTHROPIC CLAUDE")
    print("-" * 30)
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if anthropic_key:
        try:
            processor = FixedContentProcessor(
                provider="anthropic",
                api_key=anthropic_key,
                model="claude-3-haiku-20240307"  # Lub "claude-3-sonnet-20240229"
            )
            
            result = processor.process_single_item(test_url, test_tweet, test_content)
            
            if result:
                print("✅ Sukces!")
                print(f"📋 Tytuł: {result.get('title', 'Brak')}")
                print(f"📝 Opis: {result.get('short_description', 'Brak')}")
                print(f"🏷️  Kategoria: {result.get('category', 'Brak')}")
            else:
                print("❌ Nieudane")
                
            processor.close()
        except Exception as e:
            print(f"❌ Błąd: {e}")
    else:
        print("⚠️  Brak klucza API. Ustaw zmienną środowiskową ANTHROPIC_API_KEY")
    
    print("\n" + "="*60 + "\n")
    
    # 4. UŻYCIE Z GOOGLE
    print("4️⃣ GOOGLE GEMINI")
    print("-" * 30)
    
    google_key = os.getenv("GOOGLE_API_KEY")
    
    if google_key:
        try:
            processor = FixedContentProcessor(
                provider="google",
                api_key=google_key,
                model="gemini-pro"  # Lub "gemini-pro-vision" dla obrazów
            )
            
            result = processor.process_single_item(test_url, test_tweet, test_content)
            
            if result:
                print("✅ Sukces!")
                print(f"📋 Tytuł: {result.get('title', 'Brak')}")
                print(f"📝 Opis: {result.get('short_description', 'Brak')}")
                print(f"🏷️  Kategoria: {result.get('category', 'Brak')}")
            else:
                print("❌ Nieudane")
                
            processor.close()
        except Exception as e:
            print(f"❌ Błąd: {e}")
    else:
        print("⚠️  Brak klucza API. Ustaw zmienną środowiskową GOOGLE_API_KEY")
    
    print("\n" + "="*60 + "\n")
    
    # 5. UŻYCIE ZE ZMIENNYMI ŚRODOWISKOWYMI
    print("5️⃣ AUTOMATYCZNE WYKRYWANIE PROVIDERA")
    print("-" * 30)
    
    # Możesz ustawić provider i klucz przez zmienne środowiskowe:
    # export LLM_PROVIDER=anthropic
    # export API_KEY=your-anthropic-api-key
    
    print("Przykład z zmiennymi środowiskowymi:")
    print("$ export LLM_PROVIDER=anthropic")
    print("$ export API_KEY=your-anthropic-api-key")
    print("$ python your_script.py")
    print()
    
    try:
        # Processor automatycznie wykryje provider ze zmiennych środowiskowych
        processor = FixedContentProcessor()
        
        provider = os.getenv("LLM_PROVIDER", "local")
        api_key = os.getenv("API_KEY", "brak")
        
        print(f"🔧 Wykryty provider: {provider}")
        print(f"🔑 API Key: {'***' + api_key[-4:] if len(api_key) > 4 else 'brak'}")
        
        processor.close()
    except Exception as e:
        print(f"❌ Błąd: {e}")
    
    print("\n" + "="*60)
    print("📚 INSTRUKCJE INSTALACJI I KONFIGURACJI")
    print("="*60)
    
    print("""
🔧 INSTALACJA DEPENDENCIES:
   pip install requests

🔑 KONFIGURACJA KLUCZY API:

1. OpenAI:
   - Utwórz konto na https://platform.openai.com/
   - Pobierz klucz API
   - export OPENAI_API_KEY=your-key

2. Anthropic:
   - Utwórz konto na https://console.anthropic.com/
   - Pobierz klucz API
   - export ANTHROPIC_API_KEY=your-key

3. Google:
   - Utwórz projekt na https://console.cloud.google.com/
   - Włącz Gemini API
   - export GOOGLE_API_KEY=your-key

💡 PRZYKŁADY UŻYCIA:

# Prosty przykład z OpenAI
processor = FixedContentProcessor(
    provider="openai",
    api_key="your-key"
)

# Z custom modelem
processor = FixedContentProcessor(
    provider="anthropic",
    api_key="your-key",
    model="claude-3-sonnet-20240229"
)

# Automatyczne wykrywanie
export LLM_PROVIDER=google
export API_KEY=your-google-key
processor = FixedContentProcessor()

🚀 FUNKCJE:
- ✅ Rate limiting (automatyczny)
- ✅ Retry logic z exponential backoff
- ✅ Cache odpowiedzi (oszczędza koszty)
- ✅ Kompatybilność wsteczna z lokalnym LLM
- ✅ Obsługa błędów i fallback
    """)

if __name__ == "__main__":
    main()