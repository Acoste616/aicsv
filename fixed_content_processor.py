#!/usr/bin/env python3
"""
FIXED CONTENT PROCESSOR
Naprawiona wersja z poprawionym parsowaniem LLM i error handling

NAPRAWIONE PROBLEMY:
1. LLM Response parsing - lepsze wykrywanie i parsowanie JSON
2. None handling - sprawdzanie czy LLM zwróciło cokolwiek
3. Error handling - lepsza obsługa błędów
4. Fallback strategies - działanie nawet przy problemach z ekstrcją

NOWE FUNKCJE:
1. Obsługa wielu providerów cloud API (OpenAI, Anthropic, Google)
2. Kompatybilność wsteczna z lokalnym LLM
3. Konfiguracja przez zmienne środowiskowe
4. Retry logic z exponential backoff
5. Rate limiting
6. Cache responses
"""

import json
import re
import requests
import logging
import hashlib
import time
import random
import threading
import os
from pathlib import Path
from typing import Dict, List, Optional, Union
from config import LLM_CONFIG, EXTRACTION_CONFIG


class RateLimiter:
    """Rate limiter dla API calls z różnymi limitami dla różnych providerów."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = threading.Lock()
    
    def acquire(self):
        """Czeka aż będzie możliwe wykonanie requestu."""
        with self.lock:
            now = time.time()
            # Usuń stare requesty (starsze niż 1 minuta)
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            if len(self.requests) >= self.requests_per_minute:
                # Oblicz czas do czekania
                oldest_request = min(self.requests)
                wait_time = 60 - (now - oldest_request)
                if wait_time > 0:
                    time.sleep(wait_time)
                    # Aktualizuj listę po czekaniu
                    now = time.time()
                    self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            self.requests.append(now)


class CloudAPIProvider:
    """Bazowa klasa dla providerów cloud API."""
    
    def __init__(self, api_key: str, rate_limit: int = 60):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(rate_limit)
        self.logger = logging.getLogger(__name__)
    
    def make_request(self, prompt: str, **kwargs) -> Optional[str]:
        """Implementacja specyficzna dla providera."""
        raise NotImplementedError
    
    def _retry_with_backoff(self, func, max_retries: int = 3, *args, **kwargs) -> Optional[str]:
        """Implementuje retry logic z exponential backoff."""
        for attempt in range(max_retries):
            try:
                self.rate_limiter.acquire()
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Final attempt failed: {e}")
                    return None
                
                # Exponential backoff z jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying in {wait_time:.2f}s")
                time.sleep(wait_time)
        
        return None


class OpenAIProvider(CloudAPIProvider):
    """Provider dla OpenAI API."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, rate_limit=60)  # 60 requests per minute for tier 1
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def make_request(self, prompt: str, **kwargs) -> Optional[str]:
        """Wykonuje request do OpenAI API."""
        def _make_request():
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.1),
                "max_tokens": kwargs.get("max_tokens", 2000)
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 30)
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    self.logger.error("OpenAI response missing choices")
                    return None
            else:
                self.logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"OpenAI API error: {response.status_code}")
        
        return self._retry_with_backoff(_make_request)


class AnthropicProvider(CloudAPIProvider):
    """Provider dla Anthropic Claude API."""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        super().__init__(api_key, rate_limit=50)  # 50 requests per minute
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"
    
    def make_request(self, prompt: str, **kwargs) -> Optional[str]:
        """Wykonuje request do Anthropic API."""
        def _make_request():
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", 2000),
                "temperature": kwargs.get("temperature", 0.1),
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 30)
            )
            
            if response.status_code == 200:
                result = response.json()
                if "content" in result and len(result["content"]) > 0:
                    return result["content"][0]["text"]
                else:
                    self.logger.error("Anthropic response missing content")
                    return None
            else:
                self.logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
                raise Exception(f"Anthropic API error: {response.status_code}")
        
        return self._retry_with_backoff(_make_request)


class GoogleProvider(CloudAPIProvider):
    """Provider dla Google Gemini API."""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        super().__init__(api_key, rate_limit=60)  # 60 requests per minute
        self.model = model
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    def make_request(self, prompt: str, **kwargs) -> Optional[str]:
        """Wykonuje request do Google Gemini API."""
        def _make_request():
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": kwargs.get("temperature", 0.1),
                    "maxOutputTokens": kwargs.get("max_tokens", 2000)
                }
            }
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 30)
            )
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        return candidate["content"]["parts"][0]["text"]
                else:
                    self.logger.error("Google response missing candidates")
                    return None
            else:
                self.logger.error(f"Google API error: {response.status_code} - {response.text}")
                raise Exception(f"Google API error: {response.status_code}")
        
        return self._retry_with_backoff(_make_request)


class LocalLLMProvider:
    """Provider dla lokalnego LLM (zachowuje kompatybilność wsteczną)."""
    
    def __init__(self, api_url: str, model_name: str):
        self.api_url = api_url
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
    
    def make_request(self, prompt: str, **kwargs) -> Optional[str]:
        """Wykonuje request do lokalnego LLM."""
        try:
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.1),
                "max_tokens": kwargs.get("max_tokens", 2000)
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=kwargs.get("timeout", 45)
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    self.logger.error("Local LLM response missing choices")
                    return None
            else:
                self.logger.error(f"Local LLM API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Local LLM call error: {e}")
            return None


class FixedContentProcessor:
    """
    Naprawiona klasa do przetwarzania treści z lepszym error handling i cachingiem.
    Obsługuje zarówno lokalne LLM jak i cloud APIs.
    """
    
    def __init__(self, provider: str = None, api_key: str = None, model: str = None):
        """
        Inicjalizuje processor z wybranym providerem.
        
        Args:
            provider: "openai", "anthropic", "google", "local" lub None (auto-detect z env)
            api_key: Klucz API dla cloud providera
            model: Model do użycia (opcjonalnie)
        """
        self.logger = logging.getLogger(__name__)
        
        # Zachowaj kompatybilność wsteczną z konfiguracją lokalną
        self.llm_config = LLM_CONFIG.copy()
        
        # Konfiguracja z zmiennych środowiskowych lub parametrów
        self.provider = provider or os.getenv("LLM_PROVIDER", "local")
        self.api_key = api_key or os.getenv("API_KEY")
        self.model = model
        
        # Inicjalizuj providera
        self.llm_provider = self._initialize_provider()
        
        # Cache dla LLM
        self.cache_file = Path(f"cache_llm_{self.provider}.json")
        self.llm_cache = self._load_cache()
        
        self.logger.info(f"Initialized FixedContentProcessor with provider: {self.provider}")
    
    def _initialize_provider(self) -> Union[CloudAPIProvider, LocalLLMProvider]:
        """Inicjalizuje odpowiedniego providera API."""
        if self.provider == "openai":
            if not self.api_key:
                raise ValueError("OpenAI API key is required. Set API_KEY environment variable.")
            model = self.model or "gpt-3.5-turbo"
            return OpenAIProvider(self.api_key, model)
        
        elif self.provider == "anthropic":
            if not self.api_key:
                raise ValueError("Anthropic API key is required. Set API_KEY environment variable.")
            model = self.model or "claude-3-haiku-20240307"
            return AnthropicProvider(self.api_key, model)
        
        elif self.provider == "google":
            if not self.api_key:
                raise ValueError("Google API key is required. Set API_KEY environment variable.")
            model = self.model or "gemini-pro"
            return GoogleProvider(self.api_key, model)
        
        elif self.provider == "local":
            api_url = self.llm_config.get("api_url", "http://localhost:1234/v1/chat/completions")
            model_name = self.llm_config.get("model_name", "local-model")
            return LocalLLMProvider(api_url, model_name)
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Use 'openai', 'anthropic', 'google', or 'local'.")

    def _load_cache(self) -> Dict:
        """Ładuje cache z pliku"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Nie udało się wczytać cache: {e}")
        return {}
    
    def _save_cache(self):
        """Zapisuje cache do pliku"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.llm_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Nie udało się zapisać cache: {e}")
    
    def _get_cache_key(self, prompt: str) -> str:
        """Tworzy klucz cache dla prompta (uwzględnia providera)"""
        cache_string = f"{self.provider}:{prompt}"
        return hashlib.md5(cache_string.encode('utf-8')).hexdigest()
    
    def _should_skip_processing(self, tweet_text: str, url: str) -> bool:
        """Sprawdza czy można pominąć przetwarzanie dla krótkich tweetów bez treści"""
        # Sprawdź czy tweet jest za krótki
        if len(tweet_text.strip()) < 50:
            # Sprawdź czy ma linki
            has_links = 'http' in tweet_text.lower()
            # Sprawdź czy ma obrazy (pośrednio przez URL do Twitter)
            has_images = 'pic.twitter.com' in url.lower() or 'pbs.twimg.com' in url.lower()
            
            # Pomiń tylko jeśli brak treści, linków i obrazów
            if not has_links and not has_images:
                self.logger.info(f"Pomijanie krótkiego tweeta bez treści: {tweet_text[:30]}...")
                return True
        
        return False

    def create_smart_prompt(self, url: str, tweet_text: str, extracted_content: str = "") -> str:
        """Uproszczony prompt do minimum."""
        # Przygotuj dane
        data = f"Tweet: {tweet_text}"
        if extracted_content and len(extracted_content) > 50:
            data += f"\nDodatkowa treść: {extracted_content[:500]}"
        
        prompt = f'''Przeanalizuj poniższe dane i zwróć TYLKO poprawny JSON (bez żadnego dodatkowego tekstu):

{data}

Zwróć dokładnie taki format JSON:
{{
    "title": "Krótki tytuł do 10 słów",
    "short_description": "Opis w 1-2 zdaniach",
    "category": "Technologia",
    "tags": ["tag1", "tag2", "tag3"],
    "url": "{url}"
}}

Przykład poprawnej odpowiedzi:
{{
    "title": "Budowanie systemów RAG z LangChain",
    "short_description": "Przewodnik pokazuje jak tworzyć systemy RAG używając LangChain z fokusem na strategie podziału tekstu.",
    "category": "Technologia",
    "tags": ["RAG", "LangChain", "AI"],
    "url": "https://example.com"
}}

JSON:'''
        return prompt

    def create_multimodal_prompt(self, tweet_data: Dict, extracted_contents: Dict) -> str:
        """
        Tworzy uproszczony prompt multimodalny z prostszym formatem JSON.
        """
        
        # Przygotuj dane wejściowe
        url = tweet_data.get('url', '')
        tweet_text = extracted_contents.get('tweet_text', '')
        article_content = extracted_contents.get('article_content', '')
        ocr_results = extracted_contents.get('ocr_results', [])
        thread_content = extracted_contents.get('thread_content', [])
        video_metadata = extracted_contents.get('video_metadata', {})
        
        # Skrócone treści dla prompta
        article_summary = article_content[:800] if article_content else "Brak artykułu"
        ocr_summary = " ".join([result.get('text', '')[:200] for result in ocr_results])[:400]
        thread_summary = " ".join([tweet.get('text', '')[:100] for tweet in thread_content])[:400]
        video_title = video_metadata.get('title', 'Brak wideo')[:100]
        
        prompt = f'''Przeanalizuj poniższe dane multimodalne i zwróć TYLKO poprawny JSON:

DANE WEJŚCIOWE:
URL: {url}
Tweet: {tweet_text}
Artykuł: {article_summary}
OCR tekst: {ocr_summary}
Thread: {thread_summary}
Wideo: {video_title}

Zwróć dokładnie taki uproszczony format JSON:
{{
    "tweet_url": "{url}",
    "title": "Krótki tytuł max 15 słów",
    "summary": "Zwięzły opis w 2-3 zdaniach", 
    "category": "jedna główna kategoria",
    "key_points": ["kluczowy punkt 1", "kluczowy punkt 2", "kluczowy punkt 3"],
    "content_types": ["article", "image", "thread"],
    "technical_level": "beginner",
    "has_code": false,
    "estimated_time": "5 min"
}}

WAŻNE ZASADY:
- Użyj TYLKO podanych kategorii: "Technologia", "Biznes", "Edukacja", "Nauka", "Inne"
- content_types: wybierz z "article", "image", "thread", "video", "tweet"
- technical_level: "beginner", "intermediate", "advanced"
- key_points: maksymalnie 3-5 punktów
- has_code: true tylko jeśli zawiera kod programistyczny
- estimated_time: "X min" gdzie X to szacowany czas

JSON:'''
        
        return prompt

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Wywołuje LLM z lepszym error handling i cachingiem."""
        
        # Sprawdź cache
        cache_key = self._get_cache_key(prompt)
        if cache_key in self.llm_cache:
            self.logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
            return self.llm_cache[cache_key]
        
        try:
            self.logger.debug(f"Calling {self.provider} LLM with prompt length: {len(prompt)}")
            
            # Wywołaj odpowiedniego providera
            response = self.llm_provider.make_request(
                prompt,
                temperature=self.llm_config.get("temperature", 0.1),
                max_tokens=self.llm_config.get("max_tokens", 2000),
                timeout=self.llm_config.get("timeout", 30)
            )
            
            if response:
                self.logger.debug(f"LLM response length: {len(response)}")
                
                # Zapisz do cache
                self.llm_cache[cache_key] = response
                self._save_cache()
                
                return response
            else:
                self.logger.error(f"LLM returned empty response")
                return None
                
        except Exception as e:
            self.logger.error(f"LLM call error: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """Ulepszone wyciąganie JSON z odpowiedzi LLM z obsługą niepełnych JSON-ów."""
        if not response:
            self.logger.error("Empty response from LLM")
            return None
            
        try:
            # Strategia 1: Całość to JSON
            try:
                return json.loads(response.strip())
            except:
                pass
                
            # Strategia 2: Spróbuj naprawić niepełny JSON
            try:
                from json_repair import repair_json
                repaired = repair_json(response.strip())
                return json.loads(repaired)
            except Exception as e:
                self.logger.debug(f"json-repair failed: {e}")
                pass
                
            # Strategia 3: Szukaj między { i } i napraw ręcznie
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end+1]
            elif start != -1:
                # Jeśli nie ma zamykającego }, spróbuj naprawić
                json_str = response[start:]
                
                # Policz nawiasy
                open_braces = json_str.count('{')
                close_braces = json_str.count('}')
                
                # Dodaj brakujące zamykające nawiasy
                if open_braces > close_braces:
                    json_str += '}' * (open_braces - close_braces)
                    self.logger.info(f"Added {open_braces - close_braces} closing braces to JSON")
            else:
                self.logger.warning("No JSON structure found in response")
                return None
                
            try:
                return json.loads(json_str)
            except Exception as e:
                self.logger.warning(f"Final JSON parse failed: {e}")
                
            # Strategia 4: Jeśli nadal nie działa, spróbuj wyciągnąć choć część informacji
            self.logger.warning(f"Could not parse JSON from response: {response[:200]}...")
            return None
            
        except Exception as e:
            self.logger.error(f"JSON extraction error: {e}")
            return None

    def _create_fallback_result(self, url: str, tweet_text: str) -> Dict:
        """Tworzy fallback result gdy LLM zawiedzie."""
        return {
            "title": tweet_text[:50] + "..." if len(tweet_text) > 50 else tweet_text,
            "short_description": "Analiza automatyczna na podstawie tweeta",
            "category": "Inne",
            "tags": ["tweet", "automatyczna"],
            "url": url,
            "fallback": True
        }

    def process_single_item(self, url: str, tweet_text: str = "", extracted_content: str = "") -> Optional[Dict]:
        """
        Przetwarza pojedynczy element z pełnym error handling i optymalizacjami.
        """
        self.logger.info(f"Fixed processing: {url[:50]}...")
        
        # Sprawdź czy można pominąć przetwarzanie
        if self._should_skip_processing(tweet_text, url):
            return self._create_quick_fallback_result(url, tweet_text)
        
        try:
            # Krok 1: Stwórz prompt
            prompt = self.create_smart_prompt(url, tweet_text, extracted_content)
            
            # Krok 2: Wywołaj LLM
            response = self._call_llm(prompt)
            
            if not response:
                self.logger.warning(f"LLM returned no response for {url}, using fallback")
                return self._create_fallback_result(url, tweet_text)
                
            # Krok 3: Parsuj JSON
            analysis = self._extract_json_from_response(response)
            
            if not analysis:
                self.logger.warning(f"Could not parse LLM response for {url}, using fallback")
                return self._create_fallback_result(url, tweet_text)
                
            # Krok 4: Waliduj wynik
            required_fields = ["title", "short_description", "category", "tags", "url"]
            for field in required_fields:
                if field not in analysis:
                    self.logger.warning(f"Missing field {field} in LLM response for {url}")
                    analysis[field] = f"Brak {field}" if field != "tags" else []
                    
            # Dodaj metadata
            analysis["processing_success"] = True
            
            self.logger.info(f"Successfully processed: {url[:50]}...")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Processing error for {url}: {e}")
            return self._create_fallback_result(url, tweet_text)

    def _create_quick_fallback_result(self, url: str, tweet_text: str) -> Dict:
        """Tworzy szybki fallback result dla pomijanych tweetów."""
        return {
            "title": tweet_text[:40] + "..." if len(tweet_text) > 40 else tweet_text or "Krótki tweet",
            "short_description": "Krótki tweet bez dodatkowej treści",
            "category": "Inne",
            "tags": ["tweet", "krótki"],
            "url": url,
            "fallback": True,
            "skipped": True,
            "processing_success": True
        }

    def process_multimodal_item(self, tweet_data: Dict, extracted_contents: Dict) -> Optional[Dict]:
        """
        Przetwarza element wykorzystując zaawansowany prompt multimodalny.
        
        Args:
            tweet_data: Podstawowe dane tweeta (zawiera URL)
            extracted_contents: Słownik z różnymi typami treści
        
        Returns:
            Pełną analizę uwzględniającą wszystkie typy treści
        """
        url = tweet_data.get('url', '')
        tweet_text = extracted_contents.get('tweet_text', '')
        
        self.logger.info(f"Multimodal processing: {url[:50]}...")
        
        try:
            # Krok 1: Stwórz zaawansowany prompt multimodalny
            prompt = self.create_multimodal_prompt(tweet_data, extracted_contents)
            
            # Krok 2: Wywołaj LLM
            response = self._call_llm(prompt)
            
            if not response:
                self.logger.warning(f"LLM returned no response for {url}, using fallback")
                return self._create_multimodal_fallback(url, tweet_text, extracted_contents)
                
            # Krok 3: Parsuj JSON
            analysis = self._extract_json_from_response(response)
            
            if not analysis:
                self.logger.warning(f"Could not parse LLM response for {url}, using fallback")
                return self._create_multimodal_fallback(url, tweet_text, extracted_contents)
                
            # Krok 4: Waliduj wynik z rozszerzonymi polami
            required_fields = ["tweet_url", "title", "short_description", "category", "content_type"]
            for field in required_fields:
                if field not in analysis:
                    self.logger.warning(f"Missing field {field} in LLM response for {url}")
                    if field == "tweet_url":
                        analysis[field] = url
                    elif field == "content_type":
                        analysis[field] = "mixed"
                    else:
                        analysis[field] = f"Brak {field}"
            
            # Dodaj dodatkowe pola jeśli nie ma
            optional_fields = {
                "detailed_analysis": "Szczegółowa analiza niedostępna",
                "tags": [],
                "extracted_from": {
                    "articles": [],
                    "images": [],
                    "videos": [],
                    "thread_length": 0
                },
                "knowledge": {
                    "main_topic": "Nieznany",
                    "key_insights": [],
                    "code_snippets": [],
                    "data_points": [],
                    "visual_elements": []
                },
                "thread_summary": {
                    "main_points": [],
                    "conclusion": "Brak wniosków",
                    "author_expertise": "Nieznana"
                },
                "media_analysis": {
                    "images": [],
                    "videos": []
                },
                "technical_level": "unknown",
                "has_tutorial": False,
                "has_data": False
            }
            
            for field, default_value in optional_fields.items():
                if field not in analysis:
                    analysis[field] = default_value
                    
            # Dodaj metadata
            analysis["processing_success"] = True
            analysis["multimodal_processing"] = True
            analysis["processed_content_types"] = list(extracted_contents.keys())
            
            self.logger.info(f"Successfully processed multimodal: {url[:50]}...")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Multimodal processing error for {url}: {e}")
            return self._create_multimodal_fallback(url, tweet_text, extracted_contents)

    def _create_multimodal_fallback(self, url: str, tweet_text: str, extracted_contents: Dict) -> Dict:
        """Tworzy rozszerzony fallback result dla przetwarzania multimodalnego."""
        
        # Zbierz wszystkie dostępne treści
        all_texts = []
        if tweet_text:
            all_texts.append(tweet_text)
        if extracted_contents.get("thread_content"):
            all_texts.append(extracted_contents["thread_content"][:100])
        if extracted_contents.get("article_contents"):
            all_texts.extend([content[:100] for content in extracted_contents["article_contents"][:2]])
        
        combined_text = " ".join(all_texts)[:200]
        
        # Wykryj typy treści
        content_types = ["tweet"]
        if extracted_contents.get("thread_content"):
            content_types.append("thread")
        if extracted_contents.get("image_texts"):
            content_types.append("image")
        if extracted_contents.get("video_metadata"):
            content_types.append("video")
        if extracted_contents.get("article_contents"):
            content_types.append("article")
        
        # Określ główny typ treści
        if len(content_types) > 2:
            main_content_type = "mixed"
        elif "thread" in content_types:
            main_content_type = "thread"
        elif "article" in content_types:
            main_content_type = "article"
        else:
            main_content_type = "multimedia"
        
        # Przygotuj dane extracted_from
        extracted_from = {
            "articles": extracted_contents.get("article_contents", [])[:2],  # Max 2 URLs
            "images": [img.get("url", "") for img in extracted_contents.get("images", [])][:3],  # Max 3 images
            "videos": [vid.get("url", "") for vid in extracted_contents.get("videos", [])][:2],  # Max 2 videos
            "thread_length": len(extracted_contents.get("thread_content", "").split("\n\n")) if extracted_contents.get("thread_content") else 0
        }
        
        return {
            "tweet_url": url,
            "title": combined_text[:50] + "..." if len(combined_text) > 50 else combined_text,
            "short_description": "Analiza automatyczna na podstawie dostępnych treści multimodalnych",
            "detailed_analysis": f"Przetworzono {len(content_types)} typów treści: {', '.join(content_types)}",
            "category": "Inne",
            "content_type": main_content_type,
            "tags": ["multimodal", "automatyczna"] + content_types,
            "extracted_from": extracted_from,
            "knowledge": {
                "main_topic": "Automatyczna analiza treści multimodalnych",
                "key_insights": ["Automatyczna analiza", "Różne typy mediów"],
                "code_snippets": [],
                "data_points": [],
                "visual_elements": []
            },
            "thread_summary": {
                "main_points": ["Fallback analiza"],
                "conclusion": "Analiza automatyczna",
                "author_expertise": "Nieznana"
            },
            "media_analysis": {
                "images": [{"type": "unknown", "content": "Automatyczna analiza", "key_concepts": []} for _ in extracted_contents.get("images", [])],
                "videos": [{"platform": "unknown", "title": "Video", "key_topics": []} for _ in extracted_contents.get("videos", [])]
            },
            "technical_level": "unknown",
            "has_tutorial": "tutorial" in combined_text.lower() or "kod" in combined_text.lower(),
            "has_data": any(char.isdigit() for char in combined_text),
            "fallback": True,
            "multimodal_processing": True,
            "processed_content_types": list(extracted_contents.keys())
        }

    def close(self):
        """Zamyka zasoby."""
        pass


# Test function
def test_fixed_processing():
    """Test naprawionego procesora."""
    print("=== TEST FIXED PROCESSING ===")
    print("Testowanie różnych providerów...\n")
    
    # Test z przykładem z CSV
    test_url = "https://x.com/aaditsh/status/1931041095317688786"
    test_tweet = "How to build an app from scratch using the latest AI workflows (76 mins)"
    test_content = "Some extracted content from the webpage..."
    
    print(f"URL: {test_url}")
    print(f"Tweet: {test_tweet}")
    print()
    
    # Test 1: Local LLM (domyślny)
    print("1. Test z lokalnym LLM...")
    try:
        processor_local = FixedContentProcessor()
        result_local = processor_local.process_single_item(test_url, test_tweet, test_content)
        
        if result_local:
            print("✅ WYNIK ANALIZY (Local LLM):")
            print(json.dumps(result_local, indent=2, ensure_ascii=False))
        else:
            print("❌ ANALIZA NIEUDANA (Local LLM)")
        
        processor_local.close()
    except Exception as e:
        print(f"❌ Error z lokalnym LLM: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: OpenAI (jeśli API key jest dostępny)
    print("2. Test z OpenAI...")
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            processor_openai = FixedContentProcessor(provider="openai", api_key=openai_key)
            result_openai = processor_openai.process_single_item(test_url, test_tweet, test_content)
            
            if result_openai:
                print("✅ WYNIK ANALIZY (OpenAI):")
                print(json.dumps(result_openai, indent=2, ensure_ascii=False))
            else:
                print("❌ ANALIZA NIEUDANA (OpenAI)")
            
            processor_openai.close()
        else:
            print("⚠️  OPENAI_API_KEY nie jest ustawiony - pomijanie testu")
    except Exception as e:
        print(f"❌ Error z OpenAI: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Anthropic (jeśli API key jest dostępny)
    print("3. Test z Anthropic...")
    try:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            processor_anthropic = FixedContentProcessor(provider="anthropic", api_key=anthropic_key)
            result_anthropic = processor_anthropic.process_single_item(test_url, test_tweet, test_content)
            
            if result_anthropic:
                print("✅ WYNIK ANALIZY (Anthropic):")
                print(json.dumps(result_anthropic, indent=2, ensure_ascii=False))
            else:
                print("❌ ANALIZA NIEUDANA (Anthropic)")
            
            processor_anthropic.close()
        else:
            print("⚠️  ANTHROPIC_API_KEY nie jest ustawiony - pomijanie testu")
    except Exception as e:
        print(f"❌ Error z Anthropic: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Google (jeśli API key jest dostępny)
    print("4. Test z Google...")
    try:
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            processor_google = FixedContentProcessor(provider="google", api_key=google_key)
            result_google = processor_google.process_single_item(test_url, test_tweet, test_content)
            
            if result_google:
                print("✅ WYNIK ANALIZY (Google):")
                print(json.dumps(result_google, indent=2, ensure_ascii=False))
            else:
                print("❌ ANALIZA NIEUDANA (Google)")
            
            processor_google.close()
        else:
            print("⚠️  GOOGLE_API_KEY nie jest ustawiony - pomijanie testu")
    except Exception as e:
        print(f"❌ Error z Google: {e}")
    
    print("\n" + "="*50)
    print("INSTRUKCJE UŻYCIA:")
    print("="*50)
    print("# Użycie z różnymi providerami:")
    print()
    print("# 1. Lokalny LLM (domyślny)")
    print("processor = FixedContentProcessor()")
    print()
    print("# 2. OpenAI")
    print("processor = FixedContentProcessor(provider='openai', api_key='your-api-key')")
    print("# lub ustaw zmienną środowiskową:")
    print("# export LLM_PROVIDER=openai")
    print("# export API_KEY=your-openai-api-key")
    print()
    print("# 3. Anthropic")
    print("processor = FixedContentProcessor(provider='anthropic', api_key='your-api-key')")
    print("# lub ustaw zmienną środowiskową:")
    print("# export LLM_PROVIDER=anthropic")
    print("# export API_KEY=your-anthropic-api-key")
    print()
    print("# 4. Google")
    print("processor = FixedContentProcessor(provider='google', api_key='your-api-key')")
    print("# lub ustaw zmienną środowiskową:")
    print("# export LLM_PROVIDER=google")
    print("# export API_KEY=your-google-api-key")
    print()
    print("# Przykład z parametrami:")
    print("processor = FixedContentProcessor(")
    print("    provider='anthropic',")
    print("    api_key=os.getenv('ANTHROPIC_API_KEY'),")
    print("    model='claude-3-haiku-20240307'")
    print(")")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_fixed_processing() 