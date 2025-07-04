#!/usr/bin/env python3
"""
FIXED CONTENT PROCESSOR - CLOUD API VERSION
Rozszerzona wersja z obsługą cloud API (OpenAI, Anthropic, Google)

NOWE FUNKCJE:
1. Obsługa wielu providerów cloud API
2. Retry logic z exponential backoff
3. Rate limiting dla każdego providera
4. Rozszerzony cache z TTL
5. Kompatybilność wsteczna z lokalnym LLM

WSPIERANE PROVIDERY:
- OpenAI (GPT-3.5/GPT-4)
- Anthropic (Claude)
- Google (Gemini)
- Local (poprzednia implementacja)
"""

import json
import re
import requests
import logging
import hashlib
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from functools import wraps
from config import LLM_CONFIG, EXTRACTION_CONFIG

# Cloud API imports
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    
try:
    import google.generativeai as genai
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

# Retry and rate limiting
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from ratelimit import limits, sleep_and_retry

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Rate limiting configuration per provider
RATE_LIMITS = {
    "openai": {"calls": 60, "period": 60},  # 60 calls per minute
    "anthropic": {"calls": 50, "period": 60},  # 50 calls per minute
    "google": {"calls": 60, "period": 60},  # 60 calls per minute
    "local": {"calls": 1000, "period": 60}  # No real limit for local
}


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.config = kwargs
        
    @abstractmethod
    def call(self, prompt: str, **kwargs) -> Optional[str]:
        """Make API call to the provider"""
        pass
        
    @abstractmethod
    def get_rate_limit(self) -> Dict[str, int]:
        """Get rate limiting configuration"""
        pass


class LocalLLMProvider(LLMProvider):
    """Provider for local LLM (backward compatibility)"""
    
    def __init__(self, api_url: Optional[str] = None, model_name: Optional[str] = None, **kwargs):
        super().__init__(api_key=None, **kwargs)
        self.api_url = api_url or LLM_CONFIG.get("api_url", "http://localhost:1234/v1/chat/completions")
        self.model_name = model_name or LLM_CONFIG.get("model_name", "mistralai/mistral-7b-instruct-v0.3")
        self.temperature = kwargs.get("temperature", LLM_CONFIG.get("temperature", 0.1))
        self.max_tokens = kwargs.get("max_tokens", LLM_CONFIG.get("max_tokens", 2000))
        self.timeout = kwargs.get("timeout", LLM_CONFIG.get("timeout", 45))
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException,)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
    )
    def call(self, prompt: str, **kwargs) -> Optional[str]:
        """Call local LLM API"""
        try:
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens)
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
            else:
                self.logger.error(f"Local LLM API error: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Local LLM call error: {e}")
            raise
            
    def get_rate_limit(self) -> Dict[str, int]:
        return RATE_LIMITS["local"]


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI API"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo", **kwargs):
        if not HAS_OPENAI:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
            
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), **kwargs)
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
            
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        self.temperature = kwargs.get("temperature", 0.1)
        self.max_tokens = kwargs.get("max_tokens", 2000)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APITimeoutError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
    )
    def call(self, prompt: str, **kwargs) -> Optional[str]:
        """Call OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
            
    def get_rate_limit(self) -> Dict[str, int]:
        return RATE_LIMITS["openai"]


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic API"""
    
    def __init__(self, api_key: str = None, model: str = "claude-3-sonnet-20240229", **kwargs):
        if not HAS_ANTHROPIC:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
            
        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"), **kwargs)
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
            
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = kwargs.get("max_tokens", 2000)
        self.temperature = kwargs.get("temperature", 0.1)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((anthropic.APIError, anthropic.APITimeoutError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
    )
    def call(self, prompt: str, **kwargs) -> Optional[str]:
        """Call Anthropic API"""
        try:
            response = self.client.messages.create(
                model=kwargs.get("model", self.model),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            
            # Anthropic returns a list of content blocks
            if response.content:
                return response.content[0].text
            return None
            
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise
            
    def get_rate_limit(self) -> Dict[str, int]:
        return RATE_LIMITS["anthropic"]


class GoogleProvider(LLMProvider):
    """Provider for Google Generative AI (Gemini)"""
    
    def __init__(self, api_key: str = None, model: str = "gemini-pro", **kwargs):
        if not HAS_GOOGLE:
            raise ImportError("Google Generative AI package not installed. Run: pip install google-generativeai")
            
        super().__init__(api_key or os.getenv("GOOGLE_API_KEY"), **kwargs)
        if not self.api_key:
            raise ValueError("Google API key not provided")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)
        self.temperature = kwargs.get("temperature", 0.1)
        self.max_tokens = kwargs.get("max_output_tokens", 2000)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
    )
    def call(self, prompt: str, **kwargs) -> Optional[str]:
        """Call Google Generative AI API"""
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=kwargs.get("temperature", self.temperature),
                max_output_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            self.logger.error(f"Google API error: {e}")
            raise
            
    def get_rate_limit(self) -> Dict[str, int]:
        return RATE_LIMITS["google"]


# Factory function to create providers
def create_llm_provider(provider: str = None, **kwargs) -> LLMProvider:
    """
    Create LLM provider instance
    
    Args:
        provider: Provider name ("openai", "anthropic", "google", "local")
        **kwargs: Provider-specific configuration
        
    Returns:
        LLMProvider instance
    """
    provider = provider or os.getenv("LLM_PROVIDER", "local").lower()
    
    if provider == "openai":
        return OpenAIProvider(**kwargs)
    elif provider == "anthropic":
        return AnthropicProvider(**kwargs)
    elif provider == "google":
        return GoogleProvider(**kwargs)
    elif provider == "local":
        return LocalLLMProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


class FixedContentProcessor:
    """
    Rozszerzona klasa do przetwarzania treści z obsługą cloud API.
    Zachowuje kompatybilność wsteczną z lokalnym LLM.
    """
    
    def __init__(self, provider: str = None, api_key: str = None, **kwargs):
        """
        Initialize content processor with specified provider
        
        Args:
            provider: LLM provider ("openai", "anthropic", "google", "local")
            api_key: API key for cloud providers
            **kwargs: Additional provider-specific configuration
        """
        self.logger = logging.getLogger(__name__)
        
        # Get provider from environment if not specified
        self.provider_name = provider or os.getenv("LLM_PROVIDER", "local")
        
        # Create LLM provider instance
        self.llm_provider = create_llm_provider(
            self.provider_name,
            api_key=api_key,
            **kwargs
        )
        
        # Set up rate limiting based on provider
        rate_config = self.llm_provider.get_rate_limit()
        self._rate_limit_decorator = limits(
            calls=rate_config["calls"],
            period=rate_config["period"]
        )
        
        # Enhanced cache with TTL
        self.cache_file = Path(f"cache_llm_{self.provider_name}.json")
        self.llm_cache = self._load_cache()
        self.cache_ttl = timedelta(days=7)  # Cache entries expire after 7 days
        
        # Log configuration
        self.logger.info(f"Initialized with provider: {self.provider_name}")

    def _load_cache(self) -> Dict:
        """Ładuje cache z pliku z obsługą TTL"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                # Clean expired entries
                current_time = datetime.now()
                cleaned_cache = {}
                
                for key, entry in cache_data.items():
                    if isinstance(entry, dict) and "timestamp" in entry:
                        entry_time = datetime.fromisoformat(entry["timestamp"])
                        if current_time - entry_time < self.cache_ttl:
                            cleaned_cache[key] = entry
                    else:
                        # Old cache format - convert to new format
                        cleaned_cache[key] = {
                            "response": entry,
                            "timestamp": current_time.isoformat()
                        }
                        
                return cleaned_cache
        except Exception as e:
            self.logger.warning(f"Nie udało się wczytać cache: {e}")
        return {}
    
    def _save_cache(self):
        """Zapisuje cache do pliku"""
        try:
            # Limit cache size to prevent it from growing too large
            if len(self.llm_cache) > 10000:
                # Keep only the 8000 most recent entries
                sorted_items = sorted(
                    self.llm_cache.items(),
                    key=lambda x: x[1].get("timestamp", ""),
                    reverse=True
                )
                self.llm_cache = dict(sorted_items[:8000])
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.llm_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Nie udało się zapisać cache: {e}")
    
    def _get_cache_key(self, prompt: str) -> str:
        """Tworzy klucz cache dla prompta z uwzględnieniem providera"""
        cache_string = f"{self.provider_name}:{prompt}"
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

    @sleep_and_retry
    def _call_llm(self, prompt: str, **kwargs) -> Optional[str]:
        """
        Wywołuje LLM z obsługą różnych providerów, rate limiting i cachingiem.
        
        Args:
            prompt: The prompt to send to LLM
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLM response or None if failed
        """
        
        # Check cache first
        cache_key = self._get_cache_key(prompt)
        if cache_key in self.llm_cache:
            cache_entry = self.llm_cache[cache_key]
            
            # Check if it's new format with timestamp
            if isinstance(cache_entry, dict) and "response" in cache_entry:
                self.logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return cache_entry["response"]
            else:
                # Old format - return as is
                self.logger.debug(f"Cache hit (old format) for prompt: {prompt[:50]}...")
                return cache_entry
        
        # Apply rate limiting dynamically
        @self._rate_limit_decorator
        def _make_llm_call():
            try:
                self.logger.debug(f"Calling {self.provider_name} with prompt length: {len(prompt)}")
                
                # Call the provider
                response = self.llm_provider.call(prompt, **kwargs)
                
                if response:
                    self.logger.debug(f"LLM response length: {len(response)}")
                    
                    # Save to cache with timestamp
                    self.llm_cache[cache_key] = {
                        "response": response,
                        "timestamp": datetime.now().isoformat()
                    }
                    self._save_cache()
                    
                    return response
                else:
                    self.logger.error(f"{self.provider_name} returned no response")
                    return None
                    
            except Exception as e:
                self.logger.error(f"{self.provider_name} call error: {e}")
                return None
        
        return _make_llm_call()

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
    """Test procesora z różnymi providerami."""
    
    # Przykłady użycia różnych providerów
    print("=== PRZYKŁADY UŻYCIA ===\n")
    
    # 1. Lokalny LLM (domyślnie)
    print("1. Lokalny LLM:")
    print('processor = FixedContentProcessor()')
    print('# lub')
    print('processor = FixedContentProcessor(provider="local")\n')
    
    # 2. OpenAI
    print("2. OpenAI:")
    print('processor = FixedContentProcessor(')
    print('    provider="openai",')
    print('    api_key=os.getenv("OPENAI_API_KEY"),')
    print('    model="gpt-3.5-turbo"  # lub "gpt-4"')
    print(')\n')
    
    # 3. Anthropic
    print("3. Anthropic:")
    print('processor = FixedContentProcessor(')
    print('    provider="anthropic",')
    print('    api_key=os.getenv("ANTHROPIC_API_KEY"),')
    print('    model="claude-3-sonnet-20240229"')
    print(')\n')
    
    # 4. Google
    print("4. Google:")
    print('processor = FixedContentProcessor(')
    print('    provider="google",')
    print('    api_key=os.getenv("GOOGLE_API_KEY"),')
    print('    model="gemini-pro"')
    print(')\n')
    
    # 5. Konfiguracja przez zmienne środowiskowe
    print("5. Konfiguracja przez zmienne środowiskowe:")
    print('# Ustaw zmienne środowiskowe:')
    print('export LLM_PROVIDER="anthropic"')
    print('export ANTHROPIC_API_KEY="your-api-key"')
    print('# Następnie:')
    print('processor = FixedContentProcessor()\n')
    
    # Test z aktualnym providerem
    provider = os.getenv("LLM_PROVIDER", "local")
    print(f"=== TEST Z PROVIDEREM: {provider.upper()} ===")
    
    try:
        # Utwórz processor
        processor = FixedContentProcessor()
        
        # Test z przykładem
        test_url = "https://x.com/aaditsh/status/1931041095317688786"
        test_tweet = "How to build an app from scratch using the latest AI workflows (76 mins)"
        test_content = "Some extracted content from the webpage..."
        
        print(f"URL: {test_url}")
        print(f"Tweet: {test_tweet}")
        print(f"Provider: {processor.provider_name}")
        
        result = processor.process_single_item(test_url, test_tweet, test_content)
        
        if result:
            print("\n✅ WYNIK ANALIZY:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("❌ ANALIZA NIEUDANA")
            
        processor.close()
        
    except Exception as e:
        print(f"❌ BŁĄD: {e}")
        print("\nUpewnij się, że:")
        print("1. Masz zainstalowane wymagane pakiety (pip install -r requirements.txt)")
        print("2. Masz ustawione odpowiednie klucze API w zmiennych środowiskowych")
        print("3. Dla lokalnego LLM - serwer jest uruchomiony")


def test_all_providers():
    """Test wszystkich providerów po kolei."""
    providers = ["local", "openai", "anthropic", "google"]
    
    test_url = "https://x.com/test/status/123"
    test_tweet = "Test tweet for all providers"
    
    for provider in providers:
        print(f"\n=== TESTING {provider.upper()} ===")
        try:
            processor = FixedContentProcessor(provider=provider)
            result = processor.process_single_item(test_url, test_tweet)
            print(f"✅ {provider}: Success")
            if result:
                print(f"   Title: {result.get('title', 'N/A')}")
        except Exception as e:
            print(f"❌ {provider}: {str(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_fixed_processing() 