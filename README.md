# aicsv - Analizator zakładek z Twittera z użyciem AI

**aicsv** to zaawansowany system w języku Python, który automatyzuje proces analizy zakładek z Twittera (X) zapisanych w pliku CSV. System wykorzystuje różne modele AI (Claude, Gemini, lokalny LLM) do głębokiej analizy treści tweetów oraz powiązanych z nimi artykułów, budując w ten sposób przeszukiwalną bazę wiedzy w formacie JSON.

## Kluczowe funkcje

*   **Wsparcie dla różnych LLM:** Claude (Anthropic), Gemini (Google), oraz lokalny model
*   **Automatyczny fallback:** Jeśli preferowany model nie jest dostępny, system używa alternatywnego
*   **Robustowe parsowanie CSV:** Wydajnie przetwarza duże pliki CSV z zakładkami z Twittera
*   **Ekstrakcja treści z linków:** Używa `Selenium` do nawigowania za przekierowaniami i pobierania treści artykułów
*   **Analiza za pomocą AI:** Wysyła zebrany kontekst do wybranego modelu AI w celu wygenerowania ustrukturyzowanego raportu
*   **Generowanie bazy wiedzy:** Tworzy plik JSON zawierający szczegółowe analizy każdego tweeta
*   **System checkpointów:** Zapisuje postępy, aby można było bezpiecznie przerwać i wznowić proces
*   **Cache dla odpowiedzi LLM:** Oszczędza czas i zasoby poprzez cachowanie odpowiedzi

## Instalacja

1.  **Sklonuj repozytorium:**
    ```bash
    git clone https://github.com/yourusername/aicsv.git
    cd aicsv
    ```

2.  **Stwórz i aktywuj środowisko wirtualne:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Zainstaluj wymagane pakiety:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Skonfiguruj klucze API:**
    ```bash
    cp .env.example .env
    # Edytuj .env i dodaj swoje klucze API
    ```

## Konfiguracja

1.  **Ustaw klucze API w pliku `.env`:**
    ```
    # Claude API
    ANTHROPIC_API_KEY=sk-ant-api03-...
    
    # Gemini API  
    GOOGLE_API_KEY=AIza...
    
    # Preferowany provider
    PREFERRED_LLM_PROVIDER=claude
    ```

2.  **Przygotuj plik z zakładkami:** Umieść plik `bookmarks_cleaned.csv` w głównym folderze projektu.

## Uruchomienie

Aby rozpocząć proces analizy:

```bash
python run_analysis.py
```

Dla szybkiego testu na 3 przykładach:

```bash
python simple_test.py
```

System automatycznie:
- Sprawdzi dostępność preferowanego API
- W razie potrzeby przełączy się na alternatywny model
- Przetworzy tweety i zapisze wyniki do `output/fixed_knowledge_base_*.json`

---
*Projekt stworzony przy wsparciu Asystenta AI.* 