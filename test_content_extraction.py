#!/usr/bin/env python3
"""
Test sprawdzający czy ContentExtractor pobiera treść z linków
"""

from content_extractor import ContentExtractor
import sys

def test_extraction():
    """Test ekstrakcji treści z przykładowego tweeta."""
    
    print("=== TEST CONTENT EXTRACTION ===")
    
    # Przykładowy URL z CSV
    test_url = "https://x.com/aaditsh/status/1931041095317688786"
    
    try:
        extractor = ContentExtractor()
        print(f"Testuję URL: {test_url}")
        
        # Pobierz treść
        content = extractor.extract_with_retry(test_url)
        
        print(f"\n📊 WYNIKI:")
        print(f"Długość treści: {len(content)} znaków")
        print(f"Czy treść nie jest pusta: {len(content.strip()) > 0}")
        
        print(f"\n📝 PIERWSZE 500 ZNAKÓW:")
        print("-" * 50)
        print(content[:500])
        print("-" * 50)
        
        # Sprawdź czy treść zawiera przydatne informacje
        useful_indicators = [
            "app", "AI", "workflow", "build", "tutorial", 
            "video", "guide", "learn", "development"
        ]
        
        found_indicators = [word for word in useful_indicators 
                          if word.lower() in content.lower()]
        
        print(f"\n🎯 ZNALEZIONE SŁOWA KLUCZOWE: {found_indicators}")
        
        # Sprawdź czy to wystarczy do analizy
        if len(content.strip()) > 100 and found_indicators:
            print("✅ TREŚĆ WYDAJE SIĘ WYSTARCZAJĄCA DO ANALIZY")
        else:
            print("❌ TREŚĆ MOŻE BYĆ NIEWYSTARCZAJĄCA")
            
        extractor.close()
        
    except Exception as e:
        print(f"❌ BŁĄD: {e}")
        return False
        
    return True

if __name__ == "__main__":
    test_extraction() 