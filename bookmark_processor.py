#!/usr/bin/env python3
"""
Automatyczny System Przetwarzania Zakładek z X/Twitter
Używa Llama 3.1 8B Instruct przez LM Studio API

Autor: AI Assistant
Wersja: 2.0 - Refactored for LLM Analysis
"""

import pandas as pd
import json
import time
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
import sys
import os
import codecs
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.request import urlopen, Request
import ssl
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import tweepy
from transformers import pipeline
from dotenv import load_dotenv
from content_extractor import ContentExtractor

# WAŻNE: Wczytaj zmienne środowiskowe z pliku .env
load_dotenv()

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

class BookmarkProcessor:
    """Główna klasa do przetwarzania zakładek z użyciem LLM."""
    
    def __init__(self, csv_file=None):
        """Inicjalizacja z opcjonalnym plikiem CSV i wczytywaniem checkpointu."""
        self.csv_file = csv_file
        self.api_url = "http://localhost:1234/v1/chat/completions"
        self.knowledge_base = {}
        self.failed_tweets = set()
        self.processed_tweets = set()
        self.logger = logging.getLogger(__name__)
        
        self.knowledge_checkpoint_file = "knowledge_base.json"
        self.failed_checkpoint_file = "failed_tweets.json"

        self.load_checkpoint()

        self.session = requests.Session()
        self.session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.extractor = ContentExtractor()

    def load_checkpoint(self):
        """Wczytuje stan z plików checkpoint i poprawnie zlicza ID."""
        try:
            if os.path.exists(self.knowledge_checkpoint_file):
                with open(self.knowledge_checkpoint_file, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
                    # Poprawka: Zliczaj tylko istniejące, niepuste ID
                    self.processed_tweets = {item.get('tweet_id') for item in self.knowledge_base.values() if item and item.get('tweet_id')}
                    self.logger.info(f"[CHECKPOINT] Wczytano {len(self.knowledge_base)} wpisów z bazy wiedzy. Unikalnych ID: {len(self.processed_tweets)}.")
            
            if os.path.exists(self.failed_checkpoint_file):
                with open(self.failed_checkpoint_file, 'r', encoding='utf-8') as f:
                    self.failed_tweets = json.load(f)
                    # Poprawka: Zliczaj tylko istniejące, niepuste ID
                    failed_ids = {item.get('tweet_id') for item in self.failed_tweets if item and item.get('tweet_id')}
                    self.processed_tweets.update(failed_ids)
                    self.logger.info(f"[CHECKPOINT] Wczytano {len(self.failed_tweets)} nieudanych wpisów. Łącznie unikalnych ID: {len(self.processed_tweets)}.")

        except json.JSONDecodeError:
            self.logger.error("[CHECKPOINT] Błąd odczytu pliku checkpoint. Zaczynam od nowa.")
            self.knowledge_base, self.failed_tweets, self.processed_tweets = {}, set(), set()
        except Exception as e:
            self.logger.error(f"[CHECKPOINT] Nie udało się wczytać checkpointu: {e}")

    def save_checkpoint(self, data, file_path):
        """Zapisuje dane do pliku JSON."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"[CHECKPOINT] Błąd zapisu do pliku {file_path}: {e}")

    def _create_llm_prompt(self, tweet_text, article_content):
        """Tworzy bardzo rygorystyczny prompt dla LLM, aby uzyskać wyłącznie JSON."""
        prompt = f"""
SYSTEM: Jesteś precyzyjnym analitykiem danych. Twoim zadaniem jest analiza tweeta i powiązanego z nim artykułu. Twoja odpowiedź MUSI być wyłącznie obiektem JSON, bez żadnych dodatkowych komentarzy, notatek, wyjaśnień czy znaczników markdown. Nie dodawaj "```json" ani nic podobnego. Zwróć tylko i wyłącznie czysty, kompletny JSON.

Oto dane do analizy:
--- TWEET ---
{tweet_text}
--- KONIEC TWEETA ---

--- TREŚĆ ARTYKUŁU ---
{article_content if article_content else "Brak treści artykułu. Analizuj tylko na podstawie tweeta."}
--- KONIEC TREŚCI ARTYKUŁU ---

ZADANIE: Wygeneruj raport w formacie JSON. Pola, które mają być uzupełnione:
- "title": (String) Chwytliwy, ale trafny tytuł (max. 10 słów).
- "summary": (String) Zwięzłe streszczenie (3-5 zdań).
- "keywords": (Array of Strings) 5-7 kluczowych słów lub fraz.
- "category": (String) Jedna z kategorii: "Technologia", "Nauka", "Biznes", "Rozrywka", "Polityka", "Społeczne", "Inne".
- "sentiment": (String) "Pozytywny", "Negatywny", "Neutralny".
- "estimated_reading_time_minutes": (Integer) Szacowany czas czytania w minutach.
- "difficulty": (String) "Łatwy", "Średni", "Trudny".
- "key_takeaways": (Array of Strings) 3-5 kluczowych wniosków w formie listy.

Twoja odpowiedź musi być idealnie sformatowanym obiektem JSON i niczym więcej.
"""
        return prompt.strip()

    def _extract_json_from_response(self, text):
        """
        Agresywnie wyciąga JSON z różnych formatów.
        Najpierw szuka bloku ```json, a jeśli go nie ma, szuka pierwszego '{' i ostatniego '}'.
        """
        if self.logger.isEnabledFor(logging.DEBUG): self.logger.info(f"[DEBUG] Próbuję wyciągnąć JSON z: '{text[:150]}...'")
        
        # Metoda 1: Spróbuj znaleźć blok kodu markdown
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            json_str = match.group(1)
            self.logger.info("[DEBUG] Znaleziono blok JSON w markdown. Próbuję parsować.")
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"[DEBUG] JSON w bloku markdown, ale niepoprawny: {e}")
                # Nie kontynuuj, jeśli znaleziono blok, ale jest zły
                return None

        # Metoda 2: Jeśli nie ma bloku markdown, znajdź pierwszy '{' i ostatni '}'
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx:end_idx + 1]
            try:
                result = json.loads(json_str)
                if self.logger.isEnabledFor(logging.DEBUG): self.logger.info("[DEBUG] Pomyślnie sparsowano JSON znajdując nawiasy klamrowe.")
                return result
            except json.JSONDecodeError as e:
                if self.logger.isEnabledFor(logging.DEBUG): self.logger.error(f"[DEBUG] Błąd parsowania JSON '{json_str[:100]}...': {e}")
                
        # Ostateczna próba - jeśli tekst wygląda jak JSON, próbuj go załadować
        if text.strip().startswith('{'):
            parsed_json = json.loads(text)
            if self.logger.isEnabledFor(logging.DEBUG): self.logger.info("[DEBUG] Udało się sparsować surowy tekst jako JSON.")
            return parsed_json
        return None

    def diagnose_llm_connection(self):
        """Ulepszona diagnostyka z prostym testem odpowiedzi."""
        self.logger.info("[DIAG] Rozpoczynam diagnostykę LM Studio...")
        
        # Test 1: Sprawdź czy serwer działa
        try:
            r = self.session.get("http://localhost:1234/v1/models", timeout=10)
            r.raise_for_status()
            models = r.json()
            self.logger.info(f"[DIAG] ✅ Połączenie z serwerem LM Studio udane. Dostępne modele: {models.get('data', [])[0].get('id')}")
        except Exception as e:
            self.logger.error(f"[DIAG] ❌ Krytyczny błąd: Nie mogę połączyć się z serwerem LM Studio: {e}")
            self.logger.error("[DIAG] Upewnij się, że LM Studio jest uruchomione, a serwer jest włączony na porcie 1234.")
            return False

        # Test 2: Sprawdź, czy model zwraca odpowiedź
        self.logger.info("[DIAG] Test prostego zapytania do modelu...")
        try:
            payload = {
                "model": "meta-llama-3.1-8b-instruct-hf",
                "messages": [{"role": "user", "content": "Say only this: Hello"}],
                "max_tokens": 10
            }
            response = self.session.post(
                self.api_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            text = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()

            if text:
                self.logger.info(f"[DIAG] ✅ Model odpowiedział: '{text}'. Wygląda na to, że działa poprawnie.")
                return True
            else:
                self.logger.error("[DIAG] ❌ Krytyczny błąd: Model zwrócił PUSTĄ odpowiedź.")
                self.logger.error("[DIAG] Sprawdź konsolę serwera LM Studio w poszukiwaniu błędów. Model mógł się nie załadować poprawnie.")
                return False
        except Exception as e:
            self.logger.error(f"[DIAG] ❌ Krytyczny błąd podczas testu odpowiedzi modelu: {e}")
            return False

    def load_tweets(self):
        """Załaduj tweety z CSV"""
        if not self.csv_file:
            raise ValueError("No CSV file specified")
            
        self.logger.info(f"[DATA] Ładowanie pliku: {self.csv_file}")
        
        try:
            # Dodajemy więcej informacji o pliku
            file_size = os.path.getsize(self.csv_file)
            self.logger.info(f"[DATA] Rozmiar pliku: {file_size / 1024 / 1024:.2f} MB")
            
            # Używamy chunksize dla dużych plików
            chunk_size = 10000
            tweets = []
            total_rows = 0
            rows_with_links = 0
            
            for chunk in pd.read_csv(self.csv_file, encoding='utf-8', chunksize=chunk_size):
                total_rows += len(chunk)
                self.logger.info(f"[DATA] Przetwarzanie chunk'a, aktualnie {total_rows} wierszy...")
                
                # Sprawdzamy kolumny
                self.logger.info(f"[DATA] Dostępne kolumny: {chunk.columns.tolist()}")
                
                for _, row in chunk.iterrows():
                    # Konwertujemy wszystkie wartości na stringi
                    row_dict = {col: str(val) for col, val in row.items()}
                    
                    # Sprawdzamy czy mamy wymagane kolumny
                    if 'full_text' not in row_dict:
                        self.logger.warning(f"[DATA] Brak kolumny 'full_text' w wierszu: {row_dict}")
                        continue
                        
                    if 't.co/' in row_dict['full_text']:
                        tweets.append({
                            'id': row_dict.get('id', ''),
                            'text': row_dict['full_text'],
                            'created_at': row_dict.get('created_at', '')
                        })
                        rows_with_links += 1
                        
            self.logger.info(f"[DATA] Przetworzono {total_rows} wierszy")
            self.logger.info(f"[DATA] Znaleziono {rows_with_links} tweetów z linkami")
            self.logger.info(f"[DATA] Załadowano {len(tweets)} tweetów do przetworzenia")
            
            return tweets
            
        except Exception as e:
            self.logger.error(f"[ERROR] Błąd ładowania CSV: {str(e)}")
            self.logger.error(f"[ERROR] Szczegóły błędu: {type(e).__name__}")
            import traceback
            self.logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
            return []
            
    def get_linked_page_metadata(self, url):
        """Pobiera tytuł i opis z podanego URL."""
        try:
            # Używamy sesji z ustawionym User-Agent
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Sprawdzamy, czy treść to HTML
            if 'text/html' not in response.headers.get('Content-Type', ''):
                self.logger.warning(f"[Scraper] Zawartość pod URL {url} nie jest typu HTML.")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.title.string if soup.title else ''
            
            description = ''
            desc_meta = soup.find('meta', attrs={'name': 'description'})
            if desc_meta and desc_meta.get('content'):
                description = desc_meta.get('content')
            
            self.logger.info(f"[Scraper] Pomyślnie pobrano metadane dla {url}")
            return {'title': title.strip(), 'description': description.strip()}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Scraper] Błąd podczas pobierania {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"[Scraper] Nieoczekiwany błąd podczas parsowania {url}: {e}")
            return None

    def analyze_tweet_with_llm(self, tweet):
        """Wykonuje pełną analizę tweeta z użyciem LLM i wzbogaconego kontekstu."""
        self.logger.info(f"Rozpoczynam analizę LLM dla tweeta: {tweet['id']}")
        
        urls = re.findall(r'https?://[^\s]+', tweet['full_text'])
        page_content = ""
        if urls:
            page_content = self.extractor.get_webpage_content(urls[0])

        prompt = self._create_llm_prompt(tweet['full_text'], page_content)
        
        response_text = self.query_llm(prompt)
        
        if not response_text:
            self.logger.error(f"[LLM] Nie otrzymano odpowiedzi od modelu dla tweeta {tweet['id']}.")
            self.failed_tweets.add(tweet['id'])
            return None

        json_data = self._extract_json_from_response(response_text)
        
        if json_data:
            self.knowledge_base[tweet['id']] = json_data
            json_data['tweet_id'] = tweet['id']
            json_data['source_url'] = urls[0] if urls else 'N/A'
            return json_data
        else:
            self.logger.error(f"[LLM] Nie udało się sparsować JSON z odpowiedzi modelu dla tweeta {tweet['id']}.")
            self.failed_tweets.add(tweet['id'])
            # Zapisz pełną, nieudaną odpowiedź do diagnostyki
            with open("failed_llm_responses.txt", "a", encoding="utf-8") as f:
                f.write(f"--- FAILED TWEET ID: {tweet['id']} ---\n")
                f.write(response_text + "\n\n")
            return None

    def query_llm(self, prompt: str) -> Optional[str]:
        """Wysyła zapytanie do LLM z dłuższym timeoutem i logiką prób."""
        payload = {
            "model": "meta-llama-3.1-8b-instruct-hf",
            "messages": [{"role": "system", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": False
        }
        
        for attempt in range(3):
            self.logger.info(f"[LLM Query] Próba {attempt + 1}/3 z max_tokens=2048...")
            try:
                response = self.session.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=300  # Zwiększony timeout do 5 minut
                )
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
            except requests.exceptions.RequestException as e:
                self.logger.error(f"[LLM Query] Błąd połączenia przy próbie {attempt + 1}: {e}")
                if attempt < 2:
                    time.sleep(10) # Czekaj 10s przed kolejną próbą
            except (KeyError, IndexError) as e:
                 self.logger.error(f"[LLM Query] Nieoczekiwana struktura odpowiedzi od API: {e}")
                 return None
        
        return None

class SimpleBookmarkProcessor:
    def __init__(self):
        self.categories = {
            'AI': ['ai', 'chatgpt', 'llm', 'machine learning', 'neural', 'gpt', 'agentic'],
            'Programming': ['python', 'javascript', 'code', 'programming', 'dev', 'nginx', 'docker', 'kubernetes'],
            'Tutorial': ['tutorial', 'guide', 'how to', 'learn', 'course', 'masterclass'],
            'News': ['breaking', 'news', 'update', 'announced', 'leaked'],
            'Tools': ['tool', 'app', 'software', 'platform', 'service', 'n8n', 'rag'],
            'Finance': ['trading', 'quant', 'finance', 'risk management']
        }
        
    def analyze_tweet(self, tweet):
        # Używamy klucza 'text', który dostarcza nasz loader
        text = tweet['text'].lower()
        
        # Wyciągnij domenę z linku
        domain = self.extract_domain(text)
        
        # Kategoryzacja na podstawie słów kluczowych
        detected_categories = []
        for category, keywords in self.categories.items():
            if any(keyword in text for keyword in keywords):
                detected_categories.append(category)
                
        # Wyciągnij hashtagi jako tagi
        detected_tags = re.findall(r'#(\w+)', text)
        
        # Wyciągnij @mentions
        mentions = re.findall(r'@(\w+)', text)
        
        return {
            'title': self.generate_title(text),
            'summary': text[:250] + '...' if len(text) > 250 else text,
            'categories': detected_categories or ['Uncategorized'],
            'tags': detected_tags[:5],
            'domain': domain,
            'mentions': mentions,
            'content_type': 'tweet',
            'tweet_id': tweet['id'],
            'created_at': tweet['created_at']
        }
        
    def generate_title(self, text):
        first_line = text.split('\n')[0]
        return first_line[:80] + '...' if len(first_line) > 80 else first_line
        
    def extract_domain(self, text):
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            try:
                # Poprawnie obsługujemy linki, zwracając domenę
                return urlparse(urls[0]).netloc.replace('www.', '')
            except Exception:
                pass
        return None

def main():
    """Główna funkcja orkiestrująca proces."""
    # setup_logging() - Usunięto, konfiguracja jest na górze pliku
    
    # Tworzymy jedną instancję ekstraktora
    extractor = ContentExtractor()
    # Jeśli inicjalizacja się nie powiodła, zakończ pracę
    if not extractor.driver:
        logging.critical("Zakończenie pracy z powodu błędu inicjalizacji ContentExtractor.")
        return

    loader_processor = None
    try:
        # Przekazujemy ekstraktor do procesora LLM
        loader_processor = BookmarkProcessor()
        loader_processor.load_checkpoint()

        csv_file_path = 'bookmarks1.csv'
        tweets_df = pd.read_csv(csv_file_path, encoding='utf-8')
        
        if tweets_df.empty:
            logging.info("Wszystkie tweety zostały już przetworzone.")
            return

        logging.info("--- Uruchamiam zaawansowane przetwarzanie z użyciem lokalnego LLM ---")
        
        if not loader_processor.diagnose_llm_connection():
             logging.error("Diagnostyka LLM nie powiodła się. Sprawdź czy LM Studio jest uruchomione i poprawnie skonfigurowane.")
             return

        total_tweets = len(tweets_df)
        logging.info(f"Pozostało tweetów do przetworzenia przez LLM: {total_tweets}")
        
        for i, tweet in enumerate(tweets_df.iterrows()):
            # Poprawka: iterrows() zwraca krotkę (indeks, seria), bierzemy serię
            tweet = tweet[1] 
            result = loader_processor.analyze_tweet_with_llm(tweet)
            
            if result:
                logging.info(f"Postęp LLM: {i+1}/{total_tweets}")
            
            # Zapisuj postęp co 5 tweetów
            if (i + 1) % 5 == 0:
                loader_processor.save_checkpoint(loader_processor.knowledge_base, loader_processor.knowledge_checkpoint_file)

    except KeyboardInterrupt:
        logging.warning("\nPrzerwano przez użytkownika. Zapisywanie postępu...")
    except Exception as e:
        logging.critical(f"Wystąpił nieoczekiwany błąd w głównej pętli: {e}", exc_info=True)
    finally:
        if loader_processor:
            loader_processor.save_checkpoint(loader_processor.knowledge_base, loader_processor.knowledge_checkpoint_file)
        # Bezpiecznie zamknij ekstraktor na końcu
        extractor.close()
        logging.info("Zakończono przetwarzanie.")

if __name__ == '__main__':
    main()