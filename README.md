# CloudLLMRouter

Inteligentny router LLM, który automatycznie wybiera najtańszy model dla różnych typów zadań z mechanizmem fallback i śledzeniem kosztów.

## ✨ Funkcje

### 🎯 Automatyczny wybór modelu
- **Proste kategoryzacje** → Gemini Flash (free tier)
- **Średnie analizy** → Claude Haiku / GPT-4o-mini
- **Kompleksowe wątki** → Claude Sonnet / GPT-4o

### 🔄 Mechanizm fallback
Primary: Gemini → Fallback: Claude → Emergency: Local

### 💰 Śledzenie kosztów
- Szacowanie kosztów na zapytanie
- Raportowanie użycia dostawców
- Całkowity koszt i statystyki

## 🚀 Szybki start

### Podstawowe użycie

```python
import asyncio
from llm_router import CloudLLMRouter

async def main():
    router = CloudLLMRouter()
    
    # Proste zadanie - automatycznie wybierze Gemini Flash (free)
    response = await router.route_request("Kategoryzuj ten email jako spam lub nie spam")
    print(f"Dostawca: {response.provider.value}")
    print(f"Koszt: ${response.cost:.6f}")
    
    # Kompleksowe zadanie - wybierze Claude Sonnet
    response = await router.route_request(
        "Przeprowadź kompleksową analizę trendów rynkowych z rekomendacjami"
    )
    print(f"Dostawca: {response.provider.value}")
    print(f"Koszt: ${response.cost:.6f}")

asyncio.run(main())
```

### Zaawansowane użycie

```python
from llm_router import CloudLLMRouter, Provider

router = CloudLLMRouter()

# Konfiguracja dostępności dostawców
router.set_provider_availability(Provider.GEMINI_FLASH, False)

# Aktualizacja konfiguracji dostawcy
router.update_provider_config(
    Provider.CLAUDE_HAIKU, 
    api_key="your-api-key",
    base_url="https://api.anthropic.com"
)

# Raport kosztów
report = router.get_cost_report()
print(f"Całkowity koszt: ${report['total_cost']:.6f}")
print(f"Liczba zapytań: {report['total_requests']}")
```

## 📊 Typy zadań

### 1. Simple Categorization
- **Słowa kluczowe**: categorize, classify, tag, label, sort, group, yes/no
- **Charakterystyka**: < 50 słów, ≤ 2 zdania
- **Wybrany model**: Gemini Flash (free)

### 2. Medium Analysis  
- **Charakterystyka**: 50-200 słów, 3-10 zdań
- **Wybrany model**: Claude Haiku / GPT-4o-mini

### 3. Complex Thread
- **Słowa kluczowe**: analyze, explain, comprehensive, detailed, step by step
- **Charakterystyka**: > 200 słów, > 10 zdań
- **Wybrany model**: Claude Sonnet / GPT-4o

## 💸 Koszty dostawców (na 1k tokenów)

| Dostawca | Koszt | Użycie |
|----------|-------|---------|
| Gemini Flash | $0.000 | Proste kategoryzacje |
| Claude Haiku | $0.0015 | Średnie analizy |
| GPT-4o Mini | $0.0006 | Alternatywa dla Haiku |
| Claude Sonnet | $0.006 | Kompleksowe analizy |
| GPT-4o | $0.015 | Najbardziej złożone |
| Local | $0.000 | Emergency fallback |

## 🔧 Konfiguracja

### Dostępni dostawcy

```python
class Provider(Enum):
    GEMINI_FLASH = "gemini_flash"
    CLAUDE_HAIKU = "claude_haiku"
    CLAUDE_SONNET = "claude_sonnet"
    GPT_4O_MINI = "gpt_4o_mini"
    GPT_4O = "gpt_4o"
    LOCAL = "local"
```

### Łańcuch fallback

```python
FALLBACK_CHAIN = [
    Provider.GEMINI_FLASH,  # Primary - free
    Provider.CLAUDE_HAIKU,  # Fallback - cheap
    Provider.CLAUDE_SONNET, # Backup - capable
    Provider.LOCAL          # Emergency - always available
]
```

## 📈 Monitorowanie

### Raport kosztów

```python
report = router.get_cost_report()
# {
#     "total_cost": 0.000194,
#     "total_requests": 4,
#     "average_cost_per_request": 4.9e-05,
#     "provider_usage": {
#         "gemini_flash": 1,
#         "claude_haiku": 2,
#         "gpt_4o_mini": 1
#     },
#     "cost_by_provider": {
#         "gemini_flash": 0.0,
#         "claude_haiku": 0.003,
#         "gpt_4o_mini": 0.0006
#     }
# }
```

### Logowanie

```python
import logging
logging.basicConfig(level=logging.INFO)

# Logi zawierają informacje o:
# - Klasyfikacji zadań
# - Wyborze dostawcy
# - Próbach fallback
# - Błędach API
```

## 🛠️ Implementacja w API

```python
# W rzeczywistej implementacji zamień mock na prawdziwe API calls
async def call_provider(self, provider: Provider, prompt: str, **kwargs):
    if provider == Provider.GEMINI_FLASH:
        # Integracja z Google Gemini API
        pass
    elif provider == Provider.CLAUDE_HAIKU:
        # Integracja z Anthropic API
        pass
    # ... etc
```

## 🎯 Przykłady użycia

### Klasyfikacja emaili
```python
response = await router.route_request("Czy ten email to spam?")
# Użyje: Gemini Flash (free)
```

### Analiza sentymentu
```python
response = await router.route_request("Przeanalizuj sentyment tej recenzji")
# Użyje: Claude Haiku (tani, dokładny)
```

### Kompleksowa analiza
```python
response = await router.route_request(
    "Przeprowadź szczegółową analizę strategii marketingowej z rekomendacjami"
)
# Użyje: Claude Sonnet (mocny model)
```

## 📋 Wymagania

- Python 3.7+
- asyncio
- logging
- dataclasses
- enum

## 🔮 Przyszłe rozszerzenia

- Integracja z rzeczywistymi API
- Load balancing między dostawcami
- Cachowanie odpowiedzi
- Batch processing
- Metrics i monitoring
- Rate limiting
- Retry z exponential backoff 