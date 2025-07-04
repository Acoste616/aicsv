# Fixed Content Processor - Cloud API Version

Rozszerzona wersja procesora treści z obsługą wielu providerów Cloud API.

## Wspierane Providery

- **OpenAI** - GPT-3.5 Turbo, GPT-4
- **Anthropic** - Claude 3 (Sonnet, Opus)
- **Google** - Gemini Pro
- **Local** - Kompatybilność wsteczna z lokalnym LLM

## Instalacja

1. Zainstaluj wymagane pakiety:
```bash
pip install -r requirements.txt
```

2. Skopiuj plik konfiguracji:
```bash
cp .env.example .env
```

3. Ustaw klucze API w pliku `.env`

## Użycie

### 1. Konfiguracja przez zmienne środowiskowe (zalecane)

```bash
# Ustaw provider i klucz API
export LLM_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="your-api-key"
```

Następnie w kodzie:
```python
from fixed_content_processor import FixedContentProcessor

# Automatycznie użyje ustawień ze zmiennych środowiskowych
processor = FixedContentProcessor()
```

### 2. Konfiguracja programowa

```python
# OpenAI
processor = FixedContentProcessor(
    provider="openai",
    api_key="your-api-key",
    model="gpt-3.5-turbo"
)

# Anthropic
processor = FixedContentProcessor(
    provider="anthropic", 
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-3-sonnet-20240229"
)

# Google
processor = FixedContentProcessor(
    provider="google",
    api_key=os.getenv("GOOGLE_API_KEY"),
    model="gemini-pro"
)

# Local (domyślnie)
processor = FixedContentProcessor()
```

### 3. Przetwarzanie treści

```python
# Pojedynczy element
result = processor.process_single_item(
    url="https://x.com/example/status/123",
    tweet_text="Example tweet text",
    extracted_content="Additional content..."
)

# Multimodalne przetwarzanie
result = processor.process_multimodal_item(
    tweet_data={"url": "https://x.com/example/status/123"},
    extracted_contents={
        "tweet_text": "Example tweet",
        "article_content": "Article text...",
        "ocr_results": [...],
        "thread_content": [...]
    }
)
```

## Funkcje

### 1. Retry Logic z Exponential Backoff
- Automatyczne ponawianie żądań przy błędach
- Exponential backoff między próbami
- Konfigurowalny przez parametry providera

### 2. Rate Limiting
- Automatyczne ograniczanie liczby żądań
- Różne limity dla każdego providera:
  - OpenAI: 60 żądań/minutę
  - Anthropic: 50 żądań/minutę
  - Google: 60 żądań/minutę
  - Local: bez limitu

### 3. Rozszerzony Cache
- Cache z TTL (Time To Live) - domyślnie 7 dni
- Automatyczne czyszczenie wygasłych wpisów
- Ograniczenie rozmiaru cache do 10000 wpisów
- Osobne pliki cache dla każdego providera

### 4. Kompatybilność wsteczna
- Pełna kompatybilność z poprzednią wersją
- Domyślnie używa lokalnego LLM
- Nie wymaga zmian w istniejącym kodzie

## Konfiguracja Rate Limits

Możesz dostosować limity w kodzie:
```python
RATE_LIMITS = {
    "openai": {"calls": 60, "period": 60},
    "anthropic": {"calls": 50, "period": 60},
    "google": {"calls": 60, "period": 60},
    "local": {"calls": 1000, "period": 60}
}
```

## Cache

Cache jest automatycznie zapisywany w plikach:
- `cache_llm_openai.json`
- `cache_llm_anthropic.json`
- `cache_llm_google.json`
- `cache_llm_local.json`

### Struktura cache
```json
{
  "hash_key": {
    "response": "LLM response text",
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

## Testowanie

```bash
# Test z lokalnym LLM
python fixed_content_processor.py

# Test z Cloud API
export LLM_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="your-key"
python fixed_content_processor.py

# Test wszystkich providerów
python -c "from fixed_content_processor import test_all_providers; test_all_providers()"
```

## Obsługa błędów

Wszystkie wywołania API są zabezpieczone przez:
- Try/catch blocks
- Retry logic (3 próby)
- Fallback do cache
- Graceful degradation

## Przykład pełnego użycia

```python
import os
from fixed_content_processor import FixedContentProcessor

# Ustaw zmienne środowiskowe lub użyj .env
os.environ['LLM_PROVIDER'] = 'anthropic'
os.environ['ANTHROPIC_API_KEY'] = 'your-api-key'

# Utwórz processor
processor = FixedContentProcessor()

# Przetwórz dane
tweet_url = "https://x.com/example/status/123"
tweet_text = "Interesting article about AI"
extracted_content = "Full article text..."

result = processor.process_single_item(
    url=tweet_url,
    tweet_text=tweet_text,
    extracted_content=extracted_content
)

# Wyświetl wynik
if result:
    print(f"Title: {result['title']}")
    print(f"Description: {result['short_description']}")
    print(f"Category: {result['category']}")
    print(f"Tags: {', '.join(result['tags'])}")
```

## Limity i ograniczenia

1. **Koszty API** - Cloud API są płatne, monitoruj użycie
2. **Rate limits** - Przestrzegaj limitów dostawców
3. **Rozmiar promptów** - Niektóre API mają limity tokenów
4. **Cache size** - Domyślnie max 10000 wpisów

## Wsparcie

W razie problemów:
1. Sprawdź logi - są bardzo szczegółowe
2. Upewnij się, że klucze API są poprawne
3. Sprawdź limity API u dostawcy
4. Dla lokalnego LLM - sprawdź czy serwer działa