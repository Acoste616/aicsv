# aicsv - Analizator zakładek z Twittera z użyciem AI

**aicsv** to zaawansowany system w języku Python, który automatyzuje proces analizy zakładek z Twittera (X) zapisanych w pliku CSV. Skrypt wykorzystuje lokalny model językowy (LLM) do głębokiej analizy treści tweetów oraz powiązanych z nimi artykułów, budując w ten sposób przeszukiwalną bazę wiedzy w formacie JSON.

Projekt został stworzony, aby poradzić sobie z typowymi problemami, takimi jak parsowanie złożonych plików CSV, podążanie za skróconymi linkami `t.co` i zapewnienie stabilnej komunikacji z lokalnym serwerem AI.

## Kluczowe funkcje

*   **Robustowe parsowanie CSV:** Wydajnie przetwarza duże pliki CSV z zakładkami z Twittera.
*   **Ekstrakcja treści z linków:** Używa `Selenium` do nawigowania za przekierowaniami (w tym `t.co`) i pobierania treści z docelowych artykułów.
*   **Analiza za pomocą lokalnego LLM:** Wysyła zebrany kontekst (tweet + treść artykułu) do lokalnego modelu LLM (obsługuje np. Llama 3.1 przez LM Studio) w celu wygenerowania ustrukturyzowanego raportu.
*   **Generowanie bazy wiedzy:** Tworzy plik `knowledge_base.json` zawierający szczegółowe analizy każdego tweeta, w tym:
    *   Tytuł i podsumowanie
    *   Słowa kluczowe i kategorie
    *   Sentyment i szacowany czas czytania
    *   Kluczowe wnioski
*   **System checkpointów:** Zapisuje postępy, aby można było bezpiecznie przerwać i wznowić proces w dowolnym momencie.
*   **Odporność na błędy:** Posiada wbudowaną logikę ponawiania prób i obsługi błędów, aby zapewnić płynne działanie.

## Instalacja

1.  **Sklonuj repozytorium:**
    ```bash
    git clone https://github.com/Acoste616/aicsv.git
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

## Konfiguracja

1.  **Uruchom serwer LLM:** Upewnij się, że Twój lokalny serwer (np. LM Studio) jest uruchomiony i nasłuchuje na porcie `1234`. Załaduj model, którego chcesz używać (np. `meta-llama-3.1-8b-instruct-hf`).

2.  **Przygotuj plik z zakładkami:** Umieść swój plik `bookmarks.csv` (lub o podobnej nazwie) w głównym folderze projektu. Upewnij się, że nazwa pliku jest poprawnie ustawiona w `bookmark_processor.py`.

## Uruchomienie

Aby rozpocząć proces analizy, uruchom główny skrypt z terminala:

```bash
python bookmark_processor.py
```

Skrypt rozpocznie przetwarzanie tweetów, a postęp będzie widoczny w konsoli. Wyniki zostaną zapisane w `knowledge_base.json`, a ewentualne problematyczne tweety w `failed_tweets.json`.

---
*Projekt stworzony przy wsparciu Asystenta AI.* 