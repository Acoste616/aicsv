#!/usr/bin/env python3
"""
Szybki test czy nowy ContentExtractor działa lepiej
"""

import logging
from content_extractor import ContentExtractor

logging.basicConfig(level=logging.INFO)

def quick_test():
    print("🧪 SZYBKI TEST CONTENTEXTRACTOR")
    print("=" * 50)
    
    extractor = ContentExtractor()
    
    # Testuj z prawdziwymi URL z tweetów (różne typy treści)
    test_urls = [
        "https://t.co/0lLjxGSCue",  # Nowy link testowy 1
        "https://t.co/d0wPyTGnDh",  # Nowy link testowy 2
        "https://t.co/FCUsmol5XR",  # Poprzedni działający
        "https://github.com/langchain-ai/langchain",  # Referencyjny - zawsze działa
        "https://openai.com/blog/chatgpt",  # Trudny przypadek
    ]
    
    success_count = 0
    total_chars = 0
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n🔗 URL {i}/5: {url}")
        print("-" * 50)
        
        # Użyj nowej metody z retry
        content = extractor.extract_with_retry(url, max_retries=2)
        
        if content:
            char_count = len(content)
            total_chars += char_count
            
            print(f"✅ Sukces! Pobrano {char_count} znaków")
            
            # Sprawdź jakość treści
            if char_count < 100:
                print("⚠️  Treść bardzo krótka - możliwy błąd")
            elif "javascript" in content.lower()[:200]:
                print("⚠️  Możliwy komunikat o JavaScript")
            elif "treść niedostępna" in content.lower():
                print("⚠️  Treść niedostępna - strona blokuje boty")
            elif char_count > 500:
                print("✅ Treść wygląda bardzo dobrze!")
                success_count += 1
            else:
                print("✅ Treść wygląda dobrze!")
                success_count += 1
                
            # Pokaż fragment
            print(f"\n📄 Fragment treści:")
            print("-" * 40)
            print(content[:400])
            if len(content) > 400:
                print("...")
        else:
            print("❌ Nie udało się pobrać treści")
    
    # Podsumowanie
    print(f"\n{'='*60}")
    print("📊 PODSUMOWANIE TESTÓW")
    print(f"{'='*60}")
    print(f"✅ Sukces: {success_count}/5 ({(success_count/5)*100:.0f}%)")
    print(f"📏 Średnia długość: {total_chars//5 if total_chars > 0 else 0} znaków")
    print(f"📈 Łączna treść: {total_chars} znaków")
    
    if success_count >= 4:
        print("🎉 DOSKONAŁY WYNIK! ContentExtractor działa świetnie!")
    elif success_count >= 3:
        print("✅ DOBRY WYNIK! Większość stron działa poprawnie")
    elif success_count >= 2:
        print("⚠️  ŚREDNI WYNIK - wymaga dalszych optymalizacji")
    else:
        print("❌ SŁABY WYNIK - potrzebne poważne poprawki")
    
    extractor.close()
    print("\n✅ Test zakończony!")

if __name__ == "__main__":
    quick_test() 