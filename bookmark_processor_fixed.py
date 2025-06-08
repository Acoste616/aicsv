#!/usr/bin/env python3
"""
POPRAWIONY Automatyczny System Przetwarzania Zakładek
Zoptymalizowany dla RTX 4050 + 16GB RAM
Wersja: 4.0 - Znacznie lepsza stabilność i jakość analiz
"""

import pandas as pd
import json
import time
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re
import sys
import os
import codecs
from content_extractor import ContentExtractor

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

class OptimizedBookmarkProcessor:
    """Zoptymalizowana klasa do przetwarzania zakładek z ulepszonymi ustawieniami LLM."""
    
    def __init__(self, csv_file=None):
        """Inicjalizacja z optymalnymi ustawieniami dla stabilności."""
        self.csv_file = csv_file
        self.api_url = "http://localhost:1234/v1/chat/completions"
        self.knowledge_base = {}
        self.failed_tweets = []
        self.processed_tweets = set()
        self.logger = logging.getLogger(__name__)
        
        self.knowledge_checkpoint_file = "knowledge_base_optimized.json"
        self.failed_checkpoint_file = "failed_tweets_optimized.json"

        self.load_checkpoint()

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.extractor = ContentExtractor()
        
        # Zoptymalizowane ustawienia LLM
        self.llm_config = {
            "model_name": "mistralai/mistral-7b-instruct-v0.3",  # Mistral 7B - najlepszy dla RTX 4050!
            "temperature": 0.2,  # Bardzo niska dla konsystentności
            "max_tokens": 750,   # Optimum dla JSON response
            "timeout": 45,       # Krótszy timeout
            "max_retries": 2,    # Mniej prób, szybsze recovery
            "stop_sequences": ["```", "\n\n---", "Podsumowanie:", "```json"]
        }

    def load_checkpoint(self):
        """Wczytuje stan z plików checkpoint."""
        try:
            if os.path.exists(self.knowledge_checkpoint_file):
                with open(self.knowledge_checkpoint_file, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
                    self.processed_tweets = {str(item.get('tweet_id')) for item in self.knowledge_base.values() 
                                           if item and item.get('tweet_id')}
                    self.logger.info(f"[CHECKPOINT] Wczytano {len(self.knowledge_base)} wpisów. "
                                   f"Unikalnych ID: {len(self.processed_tweets)}.")
            
            if os.path.exists(self.failed_checkpoint_file):
                with open(self.failed_checkpoint_file, 'r', encoding='utf-8') as f:
                    self.failed_tweets = json.load(f)
                    self.logger.info(f"[CHECKPOINT] Wczytano {len(self.failed_tweets)} nieudanych wpisów.")

        except Exception as e:
            self.logger.error(f"[CHECKPOINT] Błąd wczytywania: {e}")

    def save_checkpoint(self):
        """Zapisuje aktualny stan do plików checkpoint."""
        try:
            with open(self.knowledge_checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)
            
            with open(self.failed_checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_tweets, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"[CHECKPOINT] Błąd zapisu: {e}")

    def create_ultra_optimized_prompt(self, tweet_text, article_content):
        """Tworzy maksymalnie zoptymalizowany prompt z przykładem."""
        
        # Przygotuj kontekst - skrócony ale zawierający istotę
        context = f"Tweet: {tweet_text[:250]}"
        if article_content and len(article_content) > 100:
            # Weź tylko najważniejsze fragmenty
            context += f"\n\nArtykuł: {article_content[:1200]}"
        
        prompt = f"""Przeanalizuj tweet i zwróć TYLKO poprawny JSON.

{context}

PRZYKŁAD poprawnej analizy:
{{
    "title": "Przewodnik budowania systemów RAG z LangChain",
    "summary": "Artykuł przedstawia szczegółowe podejście do tworzenia systemów RAG używając LangChain. Skupia się na strategiach chunking i optymalizacji wyszukiwania.",
    "keywords": ["RAG", "LangChain", "chunking", "AI", "wyszukiwanie"],
    "category": "Technologia",
    "sentiment": "Pozytywny",
    "estimated_reading_time_minutes": 8,
    "difficulty": "Średni",
    "key_takeaways": [
        "Chunking strategy jest kluczowa dla jakości RAG",
        "LangChain oferuje gotowe narzędzia do implementacji"
    ]
}}

Teraz przeanalizuj podany tweet w tym samym formacie. TYLKO JSON:"""
        
        return prompt.strip()

    def extract_json_robust(self, text):
        """Wzmocniona ekstrakcja JSON z wieloma metodami fallback."""
        if not text or len(text.strip()) < 10:
            return None
            
        # Metoda 1: Znajdź pierwszy kompletny JSON object
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    try:
                        json_str = text[start_idx:i + 1]
                        return json.loads(json_str)
                    except:
                        continue
        
        # Metoda 2: Szukaj między standardowymi delimiters
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*?\}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    content = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    return json.loads(content)
                except:
                    continue
                    
        return None

    def validate_analysis_strict(self, analysis):
        """Bardzo rygorystyczna walidacja analizy."""
        if not analysis or not isinstance(analysis, dict):
            return False
            
        # Sprawdź wymagane pola
        required_fields = {
            'title': str,
            'summary': str, 
            'keywords': list,
            'category': str,
            'sentiment': str
        }
        
        for field, field_type in required_fields.items():
            if field not in analysis:
                self.logger.warning(f"[VALIDATION] Brak pola: {field}")
                return False
            if not isinstance(analysis[field], field_type):
                self.logger.warning(f"[VALIDATION] Niepoprawny typ pola {field}")
                return False
        
        # Walidacja zawartości
        title = analysis['title'].strip()
        summary = analysis['summary'].strip()
        keywords = analysis['keywords']
        
        # Sprawdź czy nie są generyczne/puste
        if len(title) < 5 or len(summary) < 30:
            self.logger.warning(f"[VALIDATION] Za krótka treść")
            return False
            
        if len(keywords) < 3 or any(len(k.strip()) < 2 for k in keywords):
            self.logger.warning(f"[VALIDATION] Za mało lub za krótkie keywords")
            return False
            
        # Sprawdź czy kategoria jest rozsądna
        valid_categories = ['Technologia', 'Biznes', 'Nauka', 'Rozrywka', 'Inne', 'Polityka', 'Sport']
        if analysis['category'] not in valid_categories:
            self.logger.warning(f"[VALIDATION] Niepoprawna kategoria: {analysis['category']}")
            return False
            
        # Sprawdź sentiment
        valid_sentiments = ['Pozytywny', 'Neutralny', 'Negatywny']
        if analysis['sentiment'] not in valid_sentiments:
            self.logger.warning(f"[VALIDATION] Niepoprawny sentiment: {analysis['sentiment']}")
            return False
            
        return True

    def query_llm_optimized(self, prompt: str) -> Optional[str]:
        """Zoptymalizowane zapytanie do LLM z lepszymi ustawieniami."""
        
        payload = {
            "model": self.llm_config["model_name"],  # Model z konfiguracji
            "messages": [
                {
                    "role": "system", 
                    "content": "Jesteś ekspertem analizy treści. Zawsze zwracasz WYŁĄCZNIE poprawny JSON bez dodatkowego tekstu, komentarzy czy formatowania markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.llm_config["temperature"],
            "max_tokens": self.llm_config["max_tokens"],
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = self.session.post(
                self.api_url,
                json=payload,
                timeout=self.llm_config["timeout"]
            )
            response_time = time.time() - start_time
            
            response.raise_for_status()
            
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            
            if content:
                self.logger.info(f"[LLM] Odpowiedź w {response_time:.1f}s, {len(content)} znaków")
                return content
            else:
                self.logger.warning("[LLM] Pusta odpowiedź od modelu")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"[LLM] Timeout po {self.llm_config['timeout']}s")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[LLM] Błąd połączenia: {e}")
        except Exception as e:
            self.logger.error(f"[LLM] Nieoczekiwany błąd: {e}")
            
        return None

    def analyze_tweet_optimized(self, tweet):
        """Wykonuje analizę tweeta z ulepszonym promptem i walidacją."""
        tweet_id = str(tweet.get('id', 'unknown'))
        
        # Sprawdź czy już przetworzono
        if tweet_id in self.processed_tweets:
            self.logger.info(f"[SKIP] Tweet {tweet_id} już przetworzony")
            return None
            
        self.logger.info(f"[ANALIZA] Rozpoczynam analizę tweeta: {tweet_id}")
        
        # Wyciągnij URL i pobierz treść (z timeout)
        urls = re.findall(r'https?://[^\s]+', tweet.get('full_text', ''))
        article_content = ""
        
        if urls:
            self.logger.info(f"[CONTENT] Pobieram treść z: {urls[0]}")
            try:
                # Krótsza próba pobrania treści
                article_content = self.extractor.extract_with_retry(urls[0], max_retries=1)
                if article_content:
                    self.logger.info(f"[CONTENT] Pobrano {len(article_content)} znaków")
                else:
                    self.logger.warning(f"[CONTENT] Nie udało się pobrać treści")
            except Exception as e:
                self.logger.warning(f"[CONTENT] Błąd pobierania: {e}")
        
        # Stwórz zoptymalizowany prompt
        prompt = self.create_ultra_optimized_prompt(tweet.get('full_text', ''), article_content)
        
        # Spróbuj z zoptymalizowanymi ustawieniami
        for attempt in range(self.llm_config["max_retries"]):
            self.logger.info(f"[LLM] Próba {attempt + 1}/{self.llm_config['max_retries']}...")
            
            # Dalej obniżaj temperature z każdą próbą
            original_temp = self.llm_config["temperature"]
            self.llm_config["temperature"] = max(0.1, original_temp - (attempt * 0.1))
            
            response_text = self.query_llm_optimized(prompt)
            
            # Przywróć oryginalną temperature
            self.llm_config["temperature"] = original_temp
            
            if response_text:
                analysis = self.extract_json_robust(response_text)
                
                if analysis and self.validate_analysis_strict(analysis):
                    # Dodaj metadane
                    analysis['tweet_id'] = tweet_id
                    analysis['source_url'] = urls[0] if urls else 'N/A'
                    analysis['created_at'] = tweet.get('created_at', '')
                    analysis['has_article'] = bool(article_content)
                    analysis['processing_attempt'] = attempt + 1
                    
                    # Zapisz do bazy
                    self.knowledge_base[tweet_id] = analysis
                    self.processed_tweets.add(tweet_id)
                    
                    self.logger.info(f"[SUCCESS] ✅ Pomyślnie przeanalizowano: {analysis['title'][:50]}...")
                    return analysis
                else:
                    self.logger.warning(f"[LLM] Próba {attempt + 1} - JSON niepoprawny lub niekompletny")
                    if response_text:
                        self.logger.info(f"[DEBUG] Fragment odpowiedzi: {response_text[:150]}...")
            else:
                self.logger.warning(f"[LLM] Próba {attempt + 1} - brak odpowiedzi")
            
            time.sleep(1)  # Krótka przerwa między próbami
        
        # Jeśli wszystkie próby zawiodły
        self.logger.error(f"[FAILED] ❌ Nie udało się przeanalizować tweeta {tweet_id}")
        self.failed_tweets.append({
            'tweet_id': tweet_id,
            'tweet_text': tweet.get('full_text', '')[:200],
            'urls': urls,
            'reason': f'LLM analysis failed after {self.llm_config["max_retries"]} attempts',
            'timestamp': datetime.now().isoformat()
        })
        
        return None

    def process_bookmarks_advanced(self, csv_file: str):
        """Zaawansowana metoda przetwarzania z lepszym zarządzaniem błędami."""
        self.logger.info(f"[START] 🚀 Rozpoczynam przetwarzanie pliku: {csv_file}")
        
        try:
            # Wczytaj dane z zaawansowanym parsowaniem
            df = self.advanced_csv_parsing(csv_file)
            if df is None:
                return
                
            self.logger.info(f"[DATA] 📊 Wczytano {len(df)} wierszy")
            
            # Filtruj tylko tweety z linkami
            tweets_with_links = df[df['full_text'].str.contains('http', na=False)]
            self.logger.info(f"[DATA] 🔗 Znaleziono {len(tweets_with_links)} tweetów z linkami")
            
            # Filtruj już przetworzone
            to_process = tweets_with_links[~tweets_with_links['id'].astype(str).isin(self.processed_tweets)]
            self.logger.info(f"[DATA] ✨ Pozostało do przetworzenia: {len(to_process)}")
            
            if len(to_process) == 0:
                self.logger.info("[DONE] ✅ Wszystkie tweety już przetworzone!")
                return
            
            # Przetwarzaj w małych partiach z lepszym progress tracking
            batch_size = 3  # Mniejsze batch size dla stabilności
            total_processed = 0
            successful_analyses = 0
            start_time = time.time()
            
            for i in range(0, len(to_process), batch_size):
                batch = to_process.iloc[i:i+batch_size]
                
                self.logger.info(f"\n[BATCH] 📦 Przetwarzam batch {i//batch_size + 1}")
                
                for _, tweet in batch.iterrows():
                    try:
                        result = self.analyze_tweet_optimized(tweet.to_dict())
                        total_processed += 1
                        
                        if result:
                            successful_analyses += 1
                            
                        # Progress report co 5 tweetów
                        if total_processed % 5 == 0:
                            elapsed = time.time() - start_time
                            rate = total_processed / elapsed * 60  # per minute
                            success_rate = (successful_analyses / total_processed) * 100
                            
                            self.logger.info(f"[PROGRESS] 📈 {total_processed}/{len(to_process)} "
                                           f"({success_rate:.1f}% sukces, {rate:.1f}/min)")
                            self.save_checkpoint()
                            
                    except KeyboardInterrupt:
                        self.logger.warning("[INTERRUPT] ⚠️ Przerwano przez użytkownika")
                        self.save_checkpoint()
                        return
                    except Exception as e:
                        self.logger.error(f"[ERROR] ❌ Błąd przetwarzania tweeta: {e}")
                        continue
                
                # Przerwa między batchami
                if i + batch_size < len(to_process):
                    self.logger.info("[BATCH] 😴 Przerwa 3 sekundy...")
                    time.sleep(3)
            
            # Zapisz końcowy stan i statystyki
            self.save_checkpoint()
            
            elapsed_total = time.time() - start_time
            self.logger.info(f"\n[DONE] 🎉 Zakończono przetwarzanie!")
            self.logger.info(f"[STATS] 📊 Przetworzone: {total_processed}")
            self.logger.info(f"[STATS] ✅ Udane: {successful_analyses}")
            self.logger.info(f"[STATS] ❌ Nieudane: {len(self.failed_tweets)}")
            self.logger.info(f"[STATS] ⏱️ Czas: {elapsed_total/60:.1f} minut")
            self.logger.info(f"[STATS] 📈 Sukces: {(successful_analyses/total_processed)*100:.1f}%")
            
        except Exception as e:
            self.logger.error(f"[CRITICAL] 💥 Błąd krytyczny: {e}")
            self.save_checkpoint()
            raise

    def advanced_csv_parsing(self, csv_file: str) -> Optional[pd.DataFrame]:
        """Zaawansowane parsowanie CSV z wieloma metodami fallback."""
        self.logger.info(f"[CSV] Rozpoczynam zaawansowane parsowanie: {csv_file}")
        
        parsing_options = [
            {'encoding': 'utf-8'},
            {'encoding': 'utf-8', 'quoting': 1},
            {'encoding': 'utf-8', 'engine': 'python'},
            {'encoding': 'utf-8', 'on_bad_lines': 'skip'},
            {'encoding': 'cp1252'},
        ]
        
        best_df = None
        best_score = 0
        
        for i, options in enumerate(parsing_options):
            try:
                self.logger.info(f"[CSV] Próbuję opcję {i+1}: {options}")
                df = pd.read_csv(csv_file, **options)
                
                # Oceń jakość parsowania
                score = self.evaluate_dataframe_quality(df)
                self.logger.info(f"[CSV] Opcja {i+1}: {len(df)} wierszy, score: {score}")
                
                if score > best_score:
                    best_score = score
                    best_df = df
                    
            except Exception as e:
                self.logger.warning(f"[CSV] Opcja {i+1} failed: {e}")
                continue
        
        if best_df is not None:
            self.logger.info(f"[CSV] ✅ Najlepsza opcja dała: {len(best_df)} wierszy")
            return best_df
        else:
            self.logger.error(f"[CSV] ❌ Wszystkie opcje parsowania zawiodły!")
            return None

    def evaluate_dataframe_quality(self, df: pd.DataFrame) -> int:
        """Ocenia jakość sparsowanego DataFrame."""
        score = 0
        
        # Podstawowe sprawdzenia
        if 'full_text' in df.columns:
            score += 100
        if 'id' in df.columns:
            score += 100
            
        # Sprawdź ile wierszy ma linki
        if 'full_text' in df.columns:
            links_count = df['full_text'].str.contains('http', na=False).sum()
            score += links_count
            
        return score

def main():
    """Główna funkcja uruchamiająca zoptymalizowany system."""
    processor = OptimizedBookmarkProcessor()
    
    print("🔧 ZOPTYMALIZOWANY BOOKMARK PROCESSOR v4.0")
    print("=" * 50)
    print("Optymalizacje:")
    print("• Niższa temperature dla konsystentności")
    print("• Lepsze prompty z przykładami") 
    print("• Rygorystyczna walidacja JSON")
    print("• Szybsze recovery po błędach")
    print("• Lepsza obsługa timeoutów")
    print()
    
    # Test połączenia z LLM
    if not test_llm_connection():
        print("❌ LM Studio nie jest dostępne. Sprawdź czy serwer jest uruchomiony.")
        return
    
    # Przetwarzaj zakładki
    csv_file = 'bookmarks1.csv'
    
    if not os.path.exists(csv_file):
        print(f"❌ Plik {csv_file} nie istnieje!")
        return
        
    print(f"📁 Przetwarzam plik: {csv_file}")
    print("💡 Naciśnij Ctrl+C aby przerwać w dowolnym momencie")
    print()
    
    try:
        processor.process_bookmarks_advanced(csv_file)
    except KeyboardInterrupt:
        print("\n⚠️ Przerwano przez użytkownika")
    finally:
        if processor.extractor:
            processor.extractor.close()
        print("✅ Zakończono pracę")

def test_llm_connection():
    """Testuje połączenie z LM Studio."""
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            if models.get('data'):
                print(f"✅ Połączono z modelem: {models['data'][0]['id']}")
                return True
    except:
        pass
    return False

if __name__ == '__main__':
    main() 