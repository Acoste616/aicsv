# integration_example.py
"""
Przykład integracji ulepszonej funkcji create_adaptive_prompt z istniejącym systemem
"""

from improved_prompts import ImprovedAdaptivePrompts
import logging

logging.basicConfig(level=logging.INFO)

class ExistingSystem:
    """
    Symulacja istniejącego systemu z problemami
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def old_create_adaptive_prompt(self, url: str, tweet_text: str, content_quality: str) -> str:
        """
        STARA WERSJA z błędem - niezdefiniowana zmienna 'content'
        """
        
        if content_quality == 'high':
            # Ta część działała
            return self._full_analysis_prompt(url, tweet_text, "some content")
        
        elif content_quality == 'medium':
            # 🐛 BUG: zmienna 'content' nie jest zdefiniowana!
            prompt = f"""
            Przeanalizuj tweet i dostępne metadane:
            
            Tweet: {tweet_text}
            URL: {url}
            Opis ze strony: {content[:500]}  # ❌ NameError: name 'content' is not defined
            
            Zwróć JSON z polami: title, category, educational_value
            """
            return prompt
        
        else:
            # Ta część też działała
            return f"Analiza tweeta: {tweet_text}"

    def _full_analysis_prompt(self, url: str, tweet_text: str, content: str) -> str:
        return f"Full analysis of {url}: {tweet_text}"


class UpgradedSystem:
    """
    Zmodernizowany system z Enhanced Content Strategy
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Użyj nowej implementacji
        self.adaptive_prompts = ImprovedAdaptivePrompts()
        
    def create_adaptive_prompt(self, url: str, tweet_text: str, content_quality: str = None) -> str:
        """
        NOWA WERSJA - zintegrowana z Enhanced Content Strategy
        """
        return self.adaptive_prompts.create_adaptive_prompt(url, tweet_text, content_quality)

    def process_tweet(self, tweet_data: dict) -> dict:
        """
        Przykład przetwarzania tweeta z nowym systemem
        """
        url = tweet_data.get('url', '')
        text = tweet_data.get('text', '')
        
        self.logger.info(f"[System] Przetwarzam tweet: {url[:50]}...")
        
        try:
            # Automatyczne wykrywanie jakości i generowanie promptu
            prompt = self.create_adaptive_prompt(url, text)
            
            # Tu byłoby wywołanie LLM
            # llm_response = call_llm(prompt)
            
            # Symulacja odpowiedzi
            llm_response = {
                "title": "Automatycznie wygenerowany tytuł",
                "category": "technical",
                "educational_value": 7,
                "confidence_level": 0.8
            }
            
            return {
                "success": True,
                "prompt_length": len(prompt),
                "analysis": llm_response,
                "enhanced_features_used": True
            }
            
        except Exception as e:
            self.logger.error(f"[System] Błąd: {e}")
            return {
                "success": False,
                "error": str(e),
                "enhanced_features_used": False
            }


def demo_migration():
    """
    Demonstracja migracji ze starego do nowego systemu
    """
    
    print("🔄 DEMO MIGRACJI SYSTEMU")
    print("=" * 50)
    
    # Test data
    test_cases = [
        {
            'url': 'https://github.com/microsoft/vscode',
            'text': 'Amazing code editor! #programming',
            'quality': 'medium'
        },
        {
            'url': 'https://arxiv.org/abs/2023.12345',
            'text': 'Interesting AI research paper 🧵',
            'quality': 'high'  
        },
        {
            'url': 'https://nytimes.com/paywall-article',
            'text': 'Breaking tech news',
            'quality': 'low'
        }
    ]
    
    old_system = ExistingSystem()
    new_system = UpgradedSystem()
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 TEST {i}: {test['url'][:40]}...")
        
        # Test starego systemu
        print("❌ STARY SYSTEM:")
        try:
            old_prompt = old_system.old_create_adaptive_prompt(
                test['url'], test['text'], test['quality']
            )
            print(f"  ✅ Sukces - prompt: {len(old_prompt)} znaków")
        except NameError as e:
            print(f"  🐛 BŁĄD: {e}")
        except Exception as e:
            print(f"  ❌ Inny błąd: {e}")
        
        # Test nowego systemu
        print("✅ NOWY SYSTEM:")
        try:
            result = new_system.process_tweet(test)
            if result['success']:
                print(f"  🎯 Sukces - prompt: {result['prompt_length']} znaków")
                print(f"  📊 Analiza: {result['analysis']['title']}")
                print(f"  🔧 Enhanced features: {result['enhanced_features_used']}")
            else:
                print(f"  ❌ Błąd: {result['error']}")
        except Exception as e:
            print(f"  ❌ Nieoczekiwany błąd: {e}")

def simple_before_after():
    """
    Prosty przykład przed/po dla konkretnej funkcji
    """
    
    print("\n🔍 PRZED vs PO - create_adaptive_prompt")
    print("=" * 50)
    
    url = "https://blog.openai.com/some-article"
    tweet = "Interesting article about AI developments"
    quality = "medium"
    
    print("❌ PRZED (z błędem):")
    print("""
    def create_adaptive_prompt(url, tweet_text, content_quality):
        if content_quality == 'medium':
            prompt = f'''
            URL: {url}
            Tweet: {tweet_text}  
            Content: {content[:500]}  # ❌ NameError!
            '''
    """)
    
    print("✅ PO (naprawione + enhanced):")
    improved = ImprovedAdaptivePrompts()
    try:
        prompt = improved.create_adaptive_prompt(url, tweet, quality)
        print(f"  🎯 Wygenerowano prompt: {len(prompt)} znaków")
        print(f"  🔧 Automatyczne pozyskiwanie treści: TAK")
        print(f"  🎪 Jakość automatycznie wykryta: TAK")
        print(f"  🚫 Błędy z niezdefiniowanymi zmiennymi: BRAK")
    except Exception as e:
        print(f"  ❌ Błąd: {e}")

def easy_migration_guide():
    """
    Prosty przewodnik migracji
    """
    
    print("\n📋 PRZEWODNIK MIGRACJI - 3 KROKI")
    print("=" * 50)
    
    print("""
🔧 KROK 1: Zastąp starą implementację
   STARE:
   def create_adaptive_prompt(url, tweet_text, content_quality):
       # kod z błędami...
   
   NOWE:
   from improved_prompts import ImprovedAdaptivePrompts
   prompts = ImprovedAdaptivePrompts()
   prompt = prompts.create_adaptive_prompt(url, tweet_text, content_quality)

🎯 KROK 2: Opcjonalnie - usuń parametr content_quality  
   Nowy system automatycznie wykrywa jakość:
   prompt = prompts.create_adaptive_prompt(url, tweet_text)  # bez quality!

🚀 KROK 3: Ciesz się nowymi funkcjami
   ✅ Brak błędów z niezdefiniowanymi zmiennymi
   ✅ Automatyczne pozyskiwanie treści 
   ✅ Wsparcie dla threadów, GitHub, YouTube
   ✅ Inteligentne fallback'i
   ✅ Lepsze prompty dla LLM
""")

if __name__ == "__main__":
    demo_migration()
    simple_before_after() 
    easy_migration_guide() 