# Streamlit Web Interface - Dokumentacja

## 📋 Opis

Aplikacja webowa stworzona w Streamlit do analizy zakładek i treści z wykorzystaniem różnych modeli LLM. Oferuje:

- 📤 Upload plików CSV z drag&drop
- 🤖 Wybór różnych providerów LLM (lokalny Mistral, OpenAI, Anthropic)
- 📊 Real-time progress analizy
- 📈 Zaawansowany dashboard z wizualizacjami
- 💾 Export do różnych formatów (JSON, Excel, Notion)

## 🚀 Uruchomienie

### 1. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 2. Uruchomienie aplikacji

```bash
streamlit run streamlit_app.py
```

Aplikacja zostanie uruchomiona na `http://localhost:8501`

## 🎯 Funkcjonalności

### Upload danych
- Drag & drop lub wybór pliku CSV
- Automatyczna walidacja danych
- Podgląd pierwszych rekordów
- Estymacja kosztów i czasu analizy

### Analiza
- Real-time progress bar
- Równoległa analiza wielu elementów
- Automatyczne zapisywanie checkpointów
- Obsługa błędów z raportowaniem

### Dashboard
- **Metryki główne**: liczba przeanalizowanych, średnia wartość edukacyjna, pewność analizy
- **Pie chart kategorii**: rozkład tematyczny analizowanych treści
- **Word cloud tagów**: wizualizacja najczęstszych tagów
- **Timeline aktywności**: wykres czasowy dodawania zakładek
- **Tabela z filtrami**: przeglądanie wyników z możliwością filtrowania

### Export danych
- **JSON**: pełne dane w formacie strukturalnym
- **Excel**: sformatowany arkusz z wynikami
- **Notion**: bezpośredni export do bazy danych Notion (wymaga API token)

## 🔧 Konfiguracja

### Providery LLM

#### Local (Mistral 7B)
- Darmowy, działa lokalnie
- Wymaga uruchomionego serwera LLM na `localhost:1234`
- Dobra jakość dla podstawowych analiz

#### OpenAI GPT-3.5/GPT-4
- Wymaga klucza API OpenAI
- GPT-3.5: szybki i ekonomiczny ($0.002/1k tokenów)
- GPT-4: najwyższa jakość analizy ($0.03/1k tokenów)

#### Anthropic Claude
- Wymaga klucza API Anthropic
- Dobra równowaga między jakością a kosztem ($0.008/1k tokenów)

### Ustawienia analizy
- **Batch size**: liczba elementów przetwarzanych równolegle (1-50)
- **OCR dla obrazów**: ekstrakcja tekstu z obrazów
- **Zbieranie wątków Twitter**: łączenie powiązanych tweetów

## 📊 Format danych wejściowych

Plik CSV powinien zawierać kolumny:
- `url` - adres URL do analizy
- `title` - tytuł/nazwa zakładki
- `created_at` - data utworzenia (opcjonalne)

Przykład:
```csv
url,title,created_at
https://example.com/article1,"Wprowadzenie do AI",2024-01-15
https://twitter.com/user/status/123,"Thread o ML",2024-01-16
```

## 🔍 Struktura wyników

Każdy przeanalizowany element zawiera:
```json
{
  "url": "https://example.com",
  "title": "Tytuł",
  "category": "Technologia",
  "tags": ["AI", "Python", "ML"],
  "summary": "Krótkie podsumowanie treści",
  "educational_value": 8,
  "key_points": ["Punkt 1", "Punkt 2"],
  "technologies": ["Python", "TensorFlow"],
  "confidence": 0.85,
  "worth_revisiting": true,
  "analyzed_at": "2024-01-20T10:30:00"
}
```

## 🛠️ Rozszerzanie funkcjonalności

### Dodawanie nowego providera LLM

W pliku `streamlit_app.py` dodaj do słownika `LLM_PROVIDERS`:

```python
"Nowy Provider": {
    "api_url": "https://api.provider.com/v1/chat",
    "cost_per_1k_tokens": 0.01,
    "description": "Opis providera",
    "requirements": "Wymaga klucza API"
}
```

### Dodawanie nowych wizualizacji

Użyj biblioteki Plotly do tworzenia interaktywnych wykresów:

```python
import plotly.express as px

fig = px.scatter(df, x='educational_value', y='confidence', 
                 color='category', size='content_length')
st.plotly_chart(fig)
```

## 📝 Uwagi

- Aplikacja zapisuje checkpointy co 5 elementów w pliku `analysis_checkpoint.json`
- Wyniki są cachowane w sesji Streamlit
- Dla dużych plików CSV (>1000 rekordów) zaleca się użycie batch processing
- Export do Notion wymaga utworzenia integracji i bazy danych w Notion

## 🐛 Rozwiązywanie problemów

### "Connection refused" dla lokalnego LLM
- Upewnij się, że serwer LLM działa na porcie 1234
- Sprawdź logi serwera LLM

### Błędy importu pakietów
- Zainstaluj wszystkie zależności: `pip install -r requirements.txt`
- Dla problemów z wordcloud na Windows: `pip install wordcloud --no-deps`

### Timeout podczas analizy
- Zmniejsz batch size w ustawieniach
- Zwiększ timeout w konfiguracji (domyślnie 45s)

## 📚 Dodatkowe zasoby

- [Dokumentacja Streamlit](https://docs.streamlit.io/)
- [Plotly Python](https://plotly.com/python/)
- [Notion API](https://developers.notion.com/)