# improved_prompts.py
"""
Ulepszona wersja funkcji create_adaptive_prompt
"""

from enhanced_content_strategy import EnhancedContentStrategy
import logging

class ImprovedAdaptivePrompts:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.content_strategy = EnhancedContentStrategy()
    
    def create_adaptive_prompt(self, url: str, tweet_text: str, content_quality: str = None) -> str:
        """
        Ulepszona wersja - naprawia problem z niezdefiniowaną zmienną 'content'
        """
        
        # Pobierz treść używając Enhanced Content Strategy
        content_data = self.content_strategy.get_content(url, tweet_text)
        
        # Użyj jakości z content_data jeśli nie podana
        if content_quality is None:
            content_quality = content_data.get('quality', 'low')
        
        # NAPRAWKA: Teraz mamy dostęp do zmiennej content
        content = content_data.get('content', '')
        
        if content_quality == 'high':
            # Pełna analiza
            return self._full_analysis_prompt(url, tweet_text, content, content_data)
        
        elif content_quality == 'medium':
            # NAPRAWIONE: Teraz content jest zdefiniowane
            prompt = f"""
            Przeanalizuj tweet i dostępne metadane:
            
            Tweet: {tweet_text}
            URL: {url}
            Źródło: {content_data.get('source', 'unknown')}
            Opis ze strony: {content[:500]}
            
            Na podstawie dostępnych informacji określ:
            1. Prawdopodobny temat główny
            2. Kategoria treści
            3. Wartość edukacyjna (1-10)
            4. Czy warto wrócić do tego linku
            
            Zwróć JSON z polami: title, category, educational_value, worth_revisiting, confidence_level
            """
            return prompt
        
        else:
            # Tylko tweet
            prompt = f"""
            Przeanalizuj sam tweet (artykuł niedostępny):
            
            Tweet: {tweet_text}
            URL: {url}
            Powód niedostępności: {content_data.get('error', 'nieznany')}
            
            Na podstawie treści tweeta wywnioskuj:
            1. O czym prawdopodobnie jest artykuł
            2. Dlaczego autor go udostępnił
            3. Dla kogo może być wartościowy
            
            Zwróć JSON z polami: inferred_topic, sharing_reason, target_audience, confidence_level
            """
            return prompt

    def _full_analysis_prompt(self, url: str, tweet_text: str, content: str, content_data: dict) -> str:
        """Prompt dla pełnej analizy"""
        return f"""
        Masz dostęp do pełnej treści artykułu:
        
        Tweet: {tweet_text}
        URL: {url}
        Źródło: {content_data.get('source')}
        Pewność: {content_data.get('confidence', 0)}
        
        TREŚĆ:
        {content[:2000]}
        
        Przeprowadź pełną analizę i zwróć JSON z polami:
        title, category, main_topic, key_points, educational_value, 
        target_audience, worth_revisiting, confidence_level, summary
        """


# Przykład użycia pokazujący różnice
def demo_comparison():
    """Demo pokazujące różnice między starą a nową wersją"""
    
    print("🔍 PORÓWNANIE: Stara vs Nowa implementacja")
    print("=" * 60)
    
    # Test case
    url = "https://github.com/microsoft/vscode"
    tweet_text = "Amazing code editor! #programming"
    
    try:
        # Nowa implementacja
        improved = ImprovedAdaptivePrompts()
        new_prompt = improved.create_adaptive_prompt(url, tweet_text)
        
        print("✅ NOWA IMPLEMENTACJA:")
        print(f"  📏 Długość: {len(new_prompt)} znaków")
        print(f"  🎯 Jakość wykryta automatycznie")
        print(f"  🔧 Zintegrowana z Enhanced Content Strategy")
        print(f"  🚫 Brak błędów z niezdefiniowanymi zmiennymi")
        
    except Exception as e:
        print(f"❌ Błąd w nowej implementacji: {e}")
    
    print("\n❌ PROBLEMY W STAREJ IMPLEMENTACJI:")
    print("  • Niezdefiniowana zmienna 'content' w medium quality")
    print("  • Brak integracji z systemem pozyskiwania treści")
    print("  • Ograniczone typy promptów")
    print("  • Brak obsługi różnych źródeł (threads, GitHub, etc.)")

if __name__ == "__main__":
    demo_comparison() 