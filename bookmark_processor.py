#!/usr/bin/env python3
"""
Automatyczny System Przetwarzania Zakładek z X/Twitter
Używa Llama 3.1 8B Instruct przez LM Studio API
Wersja: 3.0 - Ulepszona jakość analiz
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

class BookmarkProcessor:
    """Główna klasa do przetwarzania zakładek z użyciem LLM."""
    
    def __init__(self, csv_file=None):
        """Inicjalizacja z opcjonalnym plikiem CSV i wczytywaniem checkpointu."""
        self.csv_file = csv_file
        self.api_url = "http://localhost:1234/v1/chat/completions"
        self.knowledge_base = {}
        self.failed_tweets = []
        self.processed_tweets = set()
        self.logger = logging.getLogger(__name__)
        
        self.knowledge_checkpoint_file = "knowledge_base.json"
        self.failed_checkpoint_file = "failed_tweets.json"

        self.load_checkpoint()

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.extractor = ContentExtractor()

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

    def _create_enhanced_prompt(self, tweet_text, article_content):
        """Tworzy ulepszony prompt z przykładami i jasnymi instrukcjami."""
        
        # Przygotuj kontekst
        context = f"Tweet: {tweet_text[:500]}"
        if article_content and len(article_content) > 50:
            # Weź pierwsze 2000 znaków z artykułu
            context += f"\\n\\nTreść artykułu/strony:\\n{article_content[:2000]}"
        
        prompt = f"""Jesteś ekspertem w analizie treści. Przeanalizuj poniższy tweet i powiązaną treść.

{context}

ZADANIE: Na podstawie powyższych informacji, stwórz szczegółową analizę w formacie JSON.

PRZYKŁAD dobrej analizy:
{{
    "title": "Nowe możliwości GPT-4 w kodowaniu Python",
    "summary": "Artykuł prezentuje zaawansowane techniki wykorzystania GPT-4 do generowania i debugowania kodu Python. Autor pokazuje konkretne przykłady refaktoryzacji kodu i automatyzacji testów jednostkowych przy użyciu promptów.",
    "keywords": ["GPT-4", "Python", "AI coding", "automatyzacja", "testy jednostkowe", "refaktoryzacja"],
    "category": "Technologia",
    "sentiment": "Pozytywny",
    "estimated_reading_time_minutes": 8,
    "difficulty": "Średni",
    "key_takeaways": [
        "GPT-4 może generować wysokiej jakości kod Python z dokładnymi komentarzami",
        "Model skutecznie identyfikuje i naprawia bugi w istniejącym kodzie",
        "Automatyzacja testów jednostkowych oszczędza 70% czasu developera"
    ]
}}

Teraz stwórz podobną analizę dla podanego tweeta. Pamiętaj:
- Tytuł musi być konkretny i opisowy (nie ogólnikowy)
- Summary powinno zawierać faktyczne informacje z treści
- Keywords muszą być specyficzne dla tematu
- Key_takeaways to konkretne, praktyczne wnioski

Odpowiedź (tylko JSON, bez dodatkowego tekstu):"""
        
        return prompt.strip()

    def _extract_json_from_response(self, text):
        """Wyciąga JSON z odpowiedzi, obsługując różne formaty."""
        if not text:
            return None
            
        # Metoda 1: Markdown code block
        match = re.search(r'```(?:json)?\\s*(\\{.*?\\})\\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                self.logger.error(f"[JSON] Błąd parsowania z markdown: {e}")
        
        # Metoda 2: Znajdź JSON po pierwszym {
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"[JSON] Błąd parsowania: {e}")
                
        # Metoda 3: Może cały tekst to JSON?
        try:
            return json.loads(text.strip())
        except:
            pass
            
        return None

    def validate_analysis(self, analysis):
        """Waliduje czy analiza ma sens i nie jest generyczna."""
        if not analysis:
            return False
            
        # Sprawdź czy nie ma generycznych fraz
        generic_phrases = [
            "javascript nie dostępny",
            "brak treści",
            "nie można załadować",
            "błąd strony"
        ]
        
        title = analysis.get('title', '').lower()
        summary = analysis.get('summary', '').lower()
        
        for phrase in generic_phrases:
            if phrase in title or phrase in summary:
                self.logger.warning(f"[VALIDATION] Odrzucono generyczną analizę: {title}")
                return False
                
        # Sprawdź minimalne wymagania
        if len(analysis.get('keywords', [])) < 3:
            return False
        if len(analysis.get('key_takeaways', [])) < 2:
            return False
        if len(summary) < 50:
            return False
            
        return True

    def analyze_tweet_with_llm(self, tweet):
        """Wykonuje analizę tweeta z ulepszonym promptem i walidacją."""
        tweet_id = str(tweet.get('id', 'unknown'))
        
        # Sprawdź czy już przetworzono
        if tweet_id in self.processed_tweets:
            self.logger.info(f"[SKIP] Tweet {tweet_id} już przetworzony")
            return None
            
        self.logger.info(f"[ANALIZA] Rozpoczynam analizę tweeta: {tweet_id}")
        
        # Wyciągnij URL i pobierz treść
        urls = re.findall(r'https?://[^\\s]+', tweet.get('full_text', ''))
        article_content = ""
        
        if urls:
            self.logger.info(f"[CONTENT] Pobieram treść z: {urls[0]}")
            article_content = self.extractor.extract_with_retry(urls[0])
            if article_content:
                self.logger.info(f"[CONTENT] Pobrano {len(article_content)} znaków")
        
        # Stwórz prompt i zapytaj LLM
        prompt = self._create_enhanced_prompt(tweet.get('full_text', ''), article_content)
        
        # Spróbuj kilka razy z różnymi parametrami
        for attempt in range(3):
            self.logger.info(f"[LLM] Próba {attempt + 1}/3...")
            
            response_text = self.query_llm(
                prompt, 
                temperature=0.7 - (attempt * 0.2),  # Zmniejszaj temperaturę z każdą próbą
                max_tokens=1024
            )
            
            if response_text:
                analysis = self._extract_json_from_response(response_text)
                
                if analysis and self.validate_analysis(analysis):
                    # Dodaj metadane
                    analysis['tweet_id'] = tweet_id
                    analysis['source_url'] = urls[0] if urls else 'N/A'
                    analysis['created_at'] = tweet.get('created_at', '')
                    analysis['has_article'] = bool(article_content)
                    
                    # Zapisz do bazy
                    self.knowledge_base[tweet_id] = analysis
                    self.processed_tweets.add(tweet_id)
                    
                    self.logger.info(f"[SUCCESS] Pomyślnie przeanalizowano: {analysis['title']}")
                    return analysis
                else:
                    self.logger.warning(f"[LLM] Próba {attempt + 1} - niepoprawna analiza")
            
            time.sleep(2)  # Krótka przerwa między próbami
        
        # Jeśli wszystkie próby zawiodły
        self.logger.error(f"[FAILED] Nie udało się przeanalizować tweeta {tweet_id}")
        self.failed_tweets.append({
            'tweet_id': tweet_id,
            'tweet_text': tweet.get('full_text', '')[:200],
            'reason': 'LLM analysis failed after 3 attempts'
        })
        
        return None

    def query_llm(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> Optional[str]:
        """Wysyła zapytanie do LLM z lepszą obsługą błędów."""
        payload = {
            "model": "meta-llama-3.1-8b-instruct-hf",
            "messages": [
                {
                    "role": "system", 
                    "content": "Jesteś ekspertem w analizie treści. Zawsze odpowiadasz wyłącznie poprawnym JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "stop": ["```", "\\n\\n\\n"]  # Stop po bloku kodu lub pustych liniach
        }
        
        try:
            response = self.session.post(
                self.api_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if content:
                return content
            else:
                self.logger.error("[LLM] Pusta odpowiedź od modelu")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("[LLM] Timeout - model potrzebuje więcej czasu")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[LLM] Błąd połączenia: {e}")
        except Exception as e:
            self.logger.error(f"[LLM] Nieoczekiwany błąd: {e}")
            
        return None

    def process_bookmarks(self, csv_file: str):
        """Główna metoda przetwarzająca wszystkie zakładki."""
        self.logger.info(f"[START] Rozpoczynam przetwarzanie pliku: {csv_file}")
        
        try:
            # Wczytaj dane
            df = pd.read_csv(csv_file, encoding='utf-8')
            self.logger.info(f"[DATA] Wczytano {len(df)} wierszy")
            
            # Filtruj tylko tweety z linkami
            tweets_with_links = df[df['full_text'].str.contains('http', na=False)]
            self.logger.info(f"[DATA] Znaleziono {len(tweets_with_links)} tweetów z linkami")
            
            # Filtruj już przetworzone
            to_process = tweets_with_links[~tweets_with_links['id'].astype(str).isin(self.processed_tweets)]
            self.logger.info(f"[DATA] Pozostało do przetworzenia: {len(to_process)}")
            
            if len(to_process) == 0:
                self.logger.info("[DONE] Wszystkie tweety już przetworzone!")
                return
            
            # Przetwarzaj w małych partiach
            batch_size = 5
            total_processed = 0
            
            for i in range(0, len(to_process), batch_size):
                batch = to_process.iloc[i:i+batch_size]
                
                for _, tweet in batch.iterrows():
                    try:
                        result = self.analyze_tweet_with_llm(tweet.to_dict())
                        total_processed += 1
                        
                        # Log postępu
                        if total_processed % 10 == 0:
                            self.logger.info(f"[PROGRESS] Przetworzono {total_processed}/{len(to_process)}")
                            self.save_checkpoint()
                            
                    except KeyboardInterrupt:
                        self.logger.warning("[INTERRUPT] Przerwano przez użytkownika")
                        self.save_checkpoint()
                        return
                    except Exception as e:
                        self.logger.error(f"błąd przetwarzania tweeta: {e}")
                        continue
                
                # Przerwa między partiami
                time.sleep(5)
            
            # Zapisz końcowy stan
            self.save_checkpoint()
            self.logger.info(f"[DONE] Zakończono! Przetworzono {len(self.knowledge_base)} tweetów")
            
        except Exception as e:
            self.logger.error(f"[CRITICAL] Błąd krytyczny: {e}")
            self.save_checkpoint()
            raise

def main():
    """Główna funkcja uruchamiająca system."""
    processor = BookmarkProcessor()
    
    # Test połączenia z LLM
    if not test_llm_connection():
        logging.error("LM Studio nie jest dostępne. Sprawdź czy serwer jest uruchomiony.")
        return
    
    # Przetwarzaj zakładki
    csv_file = 'bookmarks1.csv'  # Zmień na swoją nazwę pliku
    
    if not os.path.exists(csv_file):
        logging.error(f"Plik {csv_file} nie istnieje!")
        return
        
    try:
        processor.process_bookmarks(csv_file)
    except KeyboardInterrupt:
        logging.info("Przerwano przez użytkownika")
    finally:
        if processor.extractor:
            processor.extractor.close()
        logging.info("Zakończono pracę")

def test_llm_connection():
    """Testuje połączenie z LM Studio."""
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            if models.get('data'):
                logging.info(f"[LLM] Połączono z modelem: {models['data'][0]['id']}")
                return True
    except:
        pass
    return False

if __name__ == '__main__':
    main() 