# Fixed Content Processor - Cloud API Support

🚀 **Ulepszona wersja Fixed Content Processor z obsługą cloud APIs**

## 📋 Nowe funkcje

✅ **Obsługa wielu providerów cloud API**
- OpenAI GPT (3.5-turbo, GPT-4)
- Anthropic Claude (Haiku, Sonnet, Opus)
- Google Gemini Pro
- Kompatybilność wsteczna z lokalnym LLM

✅ **Zaawansowane funkcje**
- Rate limiting (automatyczny)
- Retry logic z exponential backoff
- Cache odpowiedzi (oszczędza koszty)
- Konfiguracja przez zmienne środowiskowe
- Obsługa błędów i fallback

## 🔧 Instalacja

```bash
pip install requests
```

## 🔑 Konfiguracja kluczy API

### 1. OpenAI
```bash
# Utwórz konto na https://platform.openai.com/
export OPENAI_API_KEY=your-openai-api-key
```

### 2. Anthropic
```bash
# Utwórz konto na https://console.anthropic.com/
export ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 3. Google
```bash
# Utwórz projekt na https://console.cloud.google.com/
# Włącz Gemini API
export GOOGLE_API_KEY=your-google-api-key
```

## 💡 Przykłady użycia

### Podstawowe użycie

```python
from fixed_content_processor import FixedContentProcessor

# Lokalny LLM (domyślny)
processor = FixedContentProcessor()

# OpenAI
processor = FixedContentProcessor(
    provider="openai",
    api_key="your-openai-api-key"
)

# Anthropic
processor = FixedContentProcessor(
    provider="anthropic", 
    api_key="your-anthropic-api-key"
)

# Google
processor = FixedContentProcessor(
    provider="google",
    api_key="your-google-api-key"
)
```

### Konfiguracja przez zmienne środowiskowe

```bash
# Ustaw provider i klucz API
export LLM_PROVIDER=anthropic
export API_KEY=your-anthropic-api-key

# Teraz możesz użyć bez parametrów
python your_script.py
```

```python
# Automatyczne wykrywanie providera
processor = FixedContentProcessor()  # Użyje zmiennych środowiskowych
```

### Przykład z konkretnym użyciem

```python
import os
from fixed_content_processor import FixedContentProcessor

# Przykład z Anthropic
processor = FixedContentProcessor(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-3-haiku-20240307"  # Opcjonalnie
)

# Przetwórz tweet
result = processor.process_single_item(
    url="https://x.com/example/status/123456789",
    tweet_text="Jak używać AI w programowaniu",
    extracted_content="Szczegółowy artykuł o AI..."
)

if result:
    print(f"Tytuł: {result['title']}")
    print(f"Opis: {result['short_description']}")
    print(f"Kategoria: {result['category']}")
    print(f"Tagi: {result['tags']}")

processor.close()
```

## 🎯 Obsługiwane modele

### OpenAI
- `gpt-3.5-turbo` (domyślny)
- `gpt-4`
- `gpt-4-turbo`

### Anthropic
- `claude-3-haiku-20240307` (domyślny)
- `claude-3-sonnet-20240229`
- `claude-3-opus-20240229`

### Google
- `gemini-pro` (domyślny)
- `gemini-pro-vision`

## 📊 Limity i koszty

| Provider | Rate Limit | Koszt (approx) |
|----------|------------|----------------|
| OpenAI   | 60 req/min | $0.001/1K tokens |
| Anthropic| 50 req/min | $0.00025/1K tokens |
| Google   | 60 req/min | $0.00025/1K tokens |
| Local    | Brak       | Darmowe |

## 🛠️ Zaawansowane opcje

### Custom rate limiting
```python
from fixed_content_processor import OpenAIProvider

provider = OpenAIProvider(
    api_key="your-key",
    model="gpt-4"
)
provider.rate_limiter.requests_per_minute = 30  # Wolniejszy limit
```

### Retry configuration
```python
# Retry logic jest automatyczny, ale możesz dostosować:
# - Exponential backoff z jitter
# - Maksymalnie 3 próby
# - Automatyczne rate limiting
```

### Cache management
```python
processor = FixedContentProcessor(provider="openai")

# Cache jest automatyczny i zapisany do pliku:
# cache_llm_openai.json
# cache_llm_anthropic.json
# cache_llm_google.json
# cache_llm_local.json
```

## 🔄 Migracja z lokalnego LLM

Jeśli masz już działający kod z lokalnym LLM:

```python
# Stary kod
processor = FixedContentProcessor()

# Nowy kod - dodaj tylko parametry
processor = FixedContentProcessor(
    provider="openai",
    api_key="your-key"
)

# Wszystko inne pozostaje takie samo!
```

## 📁 Struktura plików

```
fixed_content_processor.py    # Główna klasa z cloud API
example_cloud_api.py         # Przykłady użycia
cache_llm_*.json            # Pliki cache dla różnych providerów
```

## 🐛 Troubleshooting

### Błąd: "API key is required"
```bash
# Upewnij się, że ustawiłeś klucz API:
export API_KEY=your-api-key
# lub
export OPENAI_API_KEY=your-openai-key
```

### Błąd: "Rate limit exceeded"
```python
# Rate limiting jest automatyczny, poczekaj chwilę
# Lub użyj wolniejszego providera
```

### Błąd: "JSON parsing failed"
```python
# Retry logic jest automatyczny
# Fallback używa lokalnego cache'a
```

## 📈 Porównanie providerów

| Feature | OpenAI | Anthropic | Google | Local |
|---------|--------|-----------|--------|-------|
| Szybkość | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Jakość | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Koszt | 💰💰💰 | 💰💰 | 💰💰 | 🆓 |
| Dostępność | ✅ | ✅ | ✅ | ⚠️ |

## 🚀 Recommended setup

Dla najlepszej kombinacji jakości i kosztu:

```bash
export LLM_PROVIDER=anthropic
export API_KEY=your-anthropic-api-key
```

```python
processor = FixedContentProcessor(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-3-haiku-20240307"  # Szybki i tani
)
```

## 📞 Support

W przypadku problemów:
1. Sprawdź logi (`logging.basicConfig(level=logging.DEBUG)`)
2. Sprawdź konfigurację zmiennych środowiskowych
3. Upewnij się, że masz aktywne klucze API
4. Sprawdź limity na swoim koncie

## 🔮 Roadmap

- [ ] Obsługa Azure OpenAI
- [ ] Obsługa Cohere
- [ ] Obsługa obrazów (multimodal)
- [ ] Batch processing
- [ ] Monitoring i metryki