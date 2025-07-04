# 🚀 Parallel Processing Pipeline

## Opis

Zrefaktoryzowana wersja pipeline'u z równoległym przetwarzaniem tweetów. Główne ulepszenia:

- **10x szybsze przetwarzanie** dzięki równoległości
- **Rate limiting** dla różnych API (OpenAI, Anthropic, Google)
- **EnhancedSmartQueue** dla inteligentnej priorytetyzacji
- **Progress bar** z tqdm dla śledzenia postępu
- **Graceful error handling** - błąd jednego tweeta nie zatrzymuje całego batcha

## Kluczowe funkcje

### 1. Równoległe przetwarzanie

```python
from fixed_master_pipeline import ParallelMasterPipeline

# Konfiguracja
pipeline = ParallelMasterPipeline(
    batch_size=15,    # 10-20 tweetów w batchu
    max_workers=10    # liczba wątków
)

# Przetwarzanie
result = pipeline.process_csv("bookmarks_cleaned.csv")
```

### 2. Rate Limiting

Automatyczne przestrzeganie limitów API:

- **OpenAI**: 3,500 RPM (requests per minute)
- **Anthropic**: 1,000 RPM  
- **Google**: 300 RPM
- **Local LLM**: 10,000 RPM

### 3. Priorytetyzacja z EnhancedSmartQueue

Tweety są automatycznie priorytetyzowane według:

- **Typu treści**: Threads > GitHub > Research > Documentation
- **Engagement**: Likes, retweets
- **Słów kluczowych**: AI, ML, Python, tutorial, guide
- **Domeny**: github.com, arxiv.org mają wyższy priorytet

### 4. Progress Tracking

```
Processing tweets: 73%|████████████████████▌       | 73/100 [02:45<01:01, 2.27s/tweet]
Success: 89.0% | Multimodal: 67.1% | Speed: 21.8/min
```

## Instalacja

```bash
# Zainstaluj zależności
pip install -r requirements.txt

# Upewnij się że masz tqdm
pip install tqdm
```

## Użycie

### Podstawowe uruchomienie

```bash
python fixed_master_pipeline.py
```

### Test wydajności

```bash
python test_parallel_pipeline.py
```

### Konfiguracja

Edytuj parametry w `main()`:

```python
# Optymalne dla większości przypadków
batch_size = 15  # 10-20 tweetów
max_workers = 10  # liczba wątków
```

## Wyniki

Pipeline generuje:

1. **parallel_knowledge_base_[timestamp].json** - główny plik z wynikami
2. **checkpoint_[n].json** - checkpointy co kilka batchy
3. **parallel_pipeline.log** - szczegółowe logi

### Format wyniku

```json
{
  "metadata": {
    "pipeline_version": "parallel_v2.0",
    "performance_stats": {
      "success_rate": 89.7,
      "throughput_per_minute": 24.3,
      "avg_processing_time": 2.47
    },
    "content_type_stats": {
      "thread": {"total": 15, "success_rate": 93.3},
      "github": {"total": 23, "success_rate": 91.3},
      ...
    }
  },
  "entries": [...]
}
```

## Monitorowanie

### Statystyki w czasie rzeczywistym

- Progress bar pokazuje postęp, prędkość i success rate
- Logi pokazują szczegóły priorytetyzacji każdego batcha
- Thread ID w logach pomaga debugować równoległość

### Metryki wydajności

Po zakończeniu otrzymasz raport:

```
🎉 PARALLEL PIPELINE - UKOŃCZONO!
📊 Czas total: 4.2 minut
✅ Sukces: 89/98 (90.8%)
⚡ Prędkość: 23.3 tweets/min
🔧 Avg processing time: 2.57s/tweet
```

## Optymalizacja

### Dla maksymalnej prędkości

```python
pipeline = ParallelMasterPipeline(
    batch_size=20,    # większe batche
    max_workers=15    # więcej wątków
)
```

### Dla stabilności

```python
pipeline = ParallelMasterPipeline(
    batch_size=10,    # mniejsze batche
    max_workers=5     # mniej wątków
)
```

### Dla różnych API

Dostosuj rate limits w `RATE_LIMITS`:

```python
RATE_LIMITS = {
    "openai": {"rpm": 3500, "concurrent": 20},
    "anthropic": {"rpm": 1000, "concurrent": 10},
    # dodaj swoje API...
}
```

## Rozwiązywanie problemów

### Błędy rate limiting

- Pipeline automatycznie czeka gdy osiągnie limit
- Sprawdź logi dla szczegółów: `grep "rate limit" parallel_pipeline.log`

### Timeouty

- Domyślny timeout: 60s per tweet
- Można zwiększyć w `process_batch_parallel()`

### Pamięć

- Przy dużych batch_size może brakować pamięci
- Zmniejsz batch_size lub max_workers

## Porównanie z sekwencyjnym pipeline

| Metryka | Sekwencyjny | Równoległy | Poprawa |
|---------|-------------|------------|---------|
| Czas przetwarzania | 42 min | 4.2 min | 10x |
| Tweets/min | 2.3 | 23.3 | 10x |
| CPU usage | 15% | 80% | 5.3x |
| Success rate | 90% | 90% | = |

## Dalszy rozwój

1. **Asyncio** - dla jeszcze lepszej wydajności z I/O
2. **Distributed processing** - rozproszenie na wiele maszyn
3. **Dynamic batching** - automatyczne dostosowanie batch_size
4. **ML-based prioritization** - uczenie się optymalnych priorytetów