# 🚨 QUICK FIX - Niezdefiniowana zmienna 'content'

## Problem
W funkcji `create_adaptive_prompt` w przypadku `content_quality == 'medium'` używana jest niezdefiniowana zmienna `content`, co powoduje błąd:

```python
NameError: name 'content' is not defined
```

## ⚡ Natychmiastowe rozwiązanie (1 minuta)

### OPCJA A: Minimalna naprawa
```python
def create_adaptive_prompt(self, url: str, tweet_text: str, content_quality: str) -> str:
    """Dostosuj prompt do jakości dostępnej treści"""
    
    # DODAJ TĘ LINIĘ na początku funkcji:
    content = ""  # Inicjalizacja zmiennej
    
    if content_quality == 'high':
        return self._full_analysis_prompt(url, tweet_text, content)
    
    elif content_quality == 'medium':
        # Teraz content jest zdefiniowane, ale puste
        prompt = f"""
        Przeanalizuj tweet i dostępne metadane:
        
        Tweet: {tweet_text}
        URL: {url}
        Opis ze strony: {content[:500] if content else "Brak dostępnych metadanych"}
        
        Na podstawie dostępnych informacji określ:
        1. Prawdopodobny temat główny
        2. Kategoria treści
        3. Wartość edukacyjna (1-10)
        4. Czy warto wrócić do tego linku
        
        Zwróć JSON z polami: title, category, educational_value, worth_revisiting, confidence_level
        """
        return prompt
    
    else:
        # Reszta bez zmian
        prompt = f"""..."""
        return prompt
```

### OPCJA B: Lepsze rozwiązanie (5 minut)
```python
def create_adaptive_prompt(self, url: str, tweet_text: str, content_quality: str) -> str:
    """Dostosuj prompt do jakości dostępnej treści"""
    
    # Spróbuj pobrać treść - prosty fallback
    content = ""
    try:
        # Tutaj możesz dodać swoją logikę pozyskiwania treści
        # Na razie używamy prostego fallback'a
        content = f"URL: {url}, Tweet: {tweet_text}"
    except:
        content = ""
    
    if content_quality == 'high':
        return self._full_analysis_prompt(url, tweet_text, content)
    
    elif content_quality == 'medium':
        # Teraz content zawiera podstawowe info
        prompt = f"""
        Przeanalizuj tweet i dostępne informacje:
        
        Tweet: {tweet_text}
        URL: {url}
        Dostępne dane: {content[:500]}
        
        Na podstawie dostępnych informacji określ:
        1. Prawdopodobny temat główny
        2. Kategoria treści 
        3. Wartość edukacyjna (1-10)
        4. Czy warto wrócić do tego linku
        
        Zwróć JSON z polami: title, category, educational_value, worth_revisiting, confidence_level
        """
        return prompt
    
    else:
        # Bez zmian
        prompt = f"""..."""
        return prompt
```

## 🚀 Ulepszone rozwiązanie (30 minut)

Jeśli masz więcej czasu, użyj naszego Enhanced Content Strategy:

```python
from enhanced_content_strategy import EnhancedContentStrategy

class YourClass:
    def __init__(self):
        self.content_strategy = EnhancedContentStrategy()
    
    def create_adaptive_prompt(self, url: str, tweet_text: str, content_quality: str = None) -> str:
        # Pobierz treść automatycznie
        content_data = self.content_strategy.get_content(url, tweet_text)
        content = content_data.get('content', '')
        
        # Użyj automatycznie wykrytej jakości jeśli nie podana
        if content_quality is None:
            content_quality = content_data.get('quality', 'low')
        
        # Reszta kodu jak wcześniej, ale teraz content jest zawsze zdefiniowane
        if content_quality == 'medium':
            prompt = f"""
            Tweet: {tweet_text}
            URL: {url}
            Źródło: {content_data.get('source')}
            Treść/Metadane: {content[:500]}
            
            Przeanalizuj...
            """
            return prompt
```

## 🧪 Test naprawy

```python
# Test czy działa
try:
    prompt = your_instance.create_adaptive_prompt(
        "https://example.com", 
        "Test tweet", 
        "medium"
    )
    print("✅ NAPRAWIONE! Prompt wygenerowany bez błędów")
except NameError as e:
    print(f"❌ Nadal błąd: {e}")
```

## 💡 Dlaczego to się stało?

Prawdopodobnie w oryginalnym kodzie planowano pobrać zmienną `content` z jakiegoś źródła, ale:
1. Kod został napisany niepełny
2. Import/inicjalizacja została zapomniana  
3. Funkcja pozyskiwania treści nie została jeszcze zaimplementowana

## 📞 Potrzebujesz więcej pomocy?

- Użyj `improved_prompts.py` dla kompletnego rozwiązania
- Sprawdź `integration_example.py` dla pełnego przykładu migracji
- Enhanced Content Strategy automatycznie rozwiązuje wszystkie te problemy 