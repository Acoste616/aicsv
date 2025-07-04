#!/usr/bin/env python3
"""
FIXED CONTENT PROCESSOR - Optimized for Cloud LLM
Zoptymalizowana wersja z ulepszonymi promptami dla cloud LLM

OPTYMALIZACJE:
1. Skrócone prompty o 50% zachowując jakość
2. Few-shot examples zamiast długich instrukcji
3. Structured output z JSON mode (dla GPT-4)
4. Temperature=0.1 dla konsystencji
5. Fallback prompts gdy JSON parsing fails
"""

import json
import re
import requests
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from config import LLM_CONFIG, EXTRACTION_CONFIG

class FixedContentProcessor:
    """
    Zoptymalizowana klasa do przetwarzania treści z ulepszonymi promptami cloud LLM.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_config = LLM_CONFIG.copy()
        
        # Optymalizacja dla cloud LLM
        self.llm_config["temperature"] = 0.1  # Konsystencja
        self.llm_config["response_format"] = {"type": "json_object"}  # JSON mode dla GPT-4
        
        self.api_url = self.llm_config["api_url"]
        
        # Cache dla LLM
        self.cache_file = Path("cache_llm.json")
        self.llm_cache = self._load_cache()
        
        # Fallback prompts
        self.fallback_prompts = {
            "simple": self._create_simple_fallback_prompt,
            "minimal": self._create_minimal_fallback_prompt
        }

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
        """Tworzy klucz cache dla prompta"""
        return hashlib.md5(prompt.encode('utf-8')).hexdigest()
    
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
        """Zoptymalizowany prompt z few-shot examples - skrócony o 50%."""
        
        # Przygotuj dane wejściowe
        content = tweet_text
        if extracted_content and len(extracted_content) > 50:
            content += f" | {extracted_content[:300]}"
        
        # Skrócony prompt z few-shot examples
        prompt = f'''Analyze content and return JSON:

INPUT: {content}

Examples:
1. Input: "Building RAG systems with LangChain - complete guide"
   Output: {{"title": "RAG Systems with LangChain Guide", "description": "Complete guide to building RAG systems using LangChain framework.", "category": "Technologia", "tags": ["RAG", "LangChain", "AI"], "url": "{url}"}}

2. Input: "5 Python tips for beginners"
   Output: {{"title": "5 Python Tips for Beginners", "description": "Essential Python programming tips for new developers.", "category": "Edukacja", "tags": ["Python", "programming", "tips"], "url": "{url}"}}

Format:
{{"title": "max 10 words", "description": "1-2 sentences", "category": "Technologia|Biznes|Edukacja|Nauka|Inne", "tags": ["3-5 tags"], "url": "{url}"}}'''
        
        return prompt

    def create_multimodal_prompt(self, tweet_data: Dict, extracted_contents: Dict) -> str:
        """Zoptymalizowany prompt multimodalny - skrócony o 50% z few-shot examples."""
        
        # Przygotuj dane wejściowe (skrócone)
        url = tweet_data.get('url', '')
        tweet_text = extracted_contents.get('tweet_text', '')
        article_content = extracted_contents.get('article_content', '')[:400]  # Skrócone
        ocr_text = " ".join([r.get('text', '')[:100] for r in extracted_contents.get('ocr_results', [])])[:200]
        thread_text = " ".join([t.get('text', '')[:50] for t in extracted_contents.get('thread_content', [])])[:200]
        video_title = extracted_contents.get('video_metadata', {}).get('title', '')[:50]
        
        # Określ typy treści
        content_types = []
        if tweet_text: content_types.append("tweet")
        if article_content: content_types.append("article")
        if ocr_text: content_types.append("image")
        if thread_text: content_types.append("thread")
        if video_title: content_types.append("video")
        
        # Skrócony prompt z few-shot examples
        prompt = f'''Analyze multimodal content and return JSON:

DATA:
Tweet: {tweet_text}
Article: {article_content}
Images: {ocr_text}
Thread: {thread_text}
Video: {video_title}

Examples:
1. Input: Tweet about "AI tutorial", Article: "Machine learning basics", Images: "code screenshots"
   Output: {{"title": "AI Tutorial with ML Basics", "summary": "Tutorial covering AI and machine learning fundamentals with code examples.", "category": "Technologia", "key_points": ["AI basics", "ML fundamentals", "code examples"], "content_types": ["tweet", "article", "image"], "technical_level": "beginner", "has_code": true, "estimated_time": "15 min"}}

2. Input: Tweet about "business strategy", Thread: "startup advice", no images
   Output: {{"title": "Business Strategy for Startups", "summary": "Strategic advice for startup businesses and entrepreneurs.", "category": "Biznes", "key_points": ["business strategy", "startup advice", "entrepreneurship"], "content_types": ["tweet", "thread"], "technical_level": "beginner", "has_code": false, "estimated_time": "10 min"}}

Format:
{{"title": "max 15 words", "summary": "2-3 sentences", "category": "Technologia|Biznes|Edukacja|Nauka|Inne", "key_points": ["3-5 points"], "content_types": {json.dumps(content_types)}, "technical_level": "beginner|intermediate|advanced", "has_code": true|false, "estimated_time": "X min"}}'''
        
        return prompt

    def _create_simple_fallback_prompt(self, content: str, url: str) -> str:
        """Prosty fallback prompt gdy główny zawodzi."""
        return f'''Analyze: {content[:200]}

Return JSON:
{{"title": "short title", "category": "Inne", "tags": ["general"], "url": "{url}"}}'''

    def _create_minimal_fallback_prompt(self, content: str, url: str) -> str:
        """Minimalny fallback prompt gdy pozostałe zawiodą."""
        return f'''Content: {content[:100]}
JSON: {{"title": "Content Analysis", "category": "Inne", "url": "{url}"}}'''

    def _call_llm(self, prompt: str, use_json_mode: bool = True) -> Optional[str]:
        """Wywołuje LLM z optymalizacją dla cloud LLM."""
        
        # Sprawdź cache
        cache_key = self._get_cache_key(prompt)
        if cache_key in self.llm_cache:
            self.logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
            return self.llm_cache[cache_key]
        
        try:
            payload = {
                "model": self.llm_config["model_name"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,  # Wymuszona konsystencja
                "max_tokens": self.llm_config["max_tokens"]
            }
            
            # Dodaj JSON mode dla GPT-4
            if use_json_mode and "gpt-4" in self.llm_config["model_name"].lower():
                payload["response_format"] = {"type": "json_object"}
            
            self.logger.debug(f"Calling LLM with prompt length: {len(prompt)}")
            
            response = requests.post(
                self.api_url, 
                json=payload, 
                timeout=self.llm_config["timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    self.logger.debug(f"LLM response length: {len(content) if content else 0}")
                    
                    # Zapisz do cache
                    if content:
                        self.llm_cache[cache_key] = content
                        self._save_cache()
                    
                    return content
                else:
                    self.logger.error("LLM response missing choices")
                    return None
            else:
                self.logger.error(f"LLM API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("LLM timeout")
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

    def _try_fallback_prompts(self, url: str, tweet_text: str, extracted_content: str) -> Optional[Dict]:
        """Próbuje fallback prompts gdy główny prompt zawodzi."""
        content = f"{tweet_text} {extracted_content}"[:500]
        
        for fallback_name, fallback_func in self.fallback_prompts.items():
            try:
                self.logger.info(f"Trying fallback prompt: {fallback_name}")
                
                fallback_prompt = fallback_func(content, url)
                response = self._call_llm(fallback_prompt, use_json_mode=False)
                
                if response:
                    analysis = self._extract_json_from_response(response)
                    if analysis:
                        analysis["fallback_used"] = fallback_name
                        return analysis
                        
            except Exception as e:
                self.logger.warning(f"Fallback prompt {fallback_name} failed: {e}")
                continue
                
        return None

    def process_single_item(self, url: str, tweet_text: str = "", extracted_content: str = "") -> Optional[Dict]:
        """
        Przetwarza pojedynczy element z optymalizowanymi promptami i fallback strategiami.
        """
        self.logger.info(f"Optimized processing: {url[:50]}...")
        
        # Sprawdź czy można pominąć przetwarzanie
        if self._should_skip_processing(tweet_text, url):
            return self._create_quick_fallback_result(url, tweet_text)
        
        try:
            # Krok 1: Główny zoptymalizowany prompt
            prompt = self.create_smart_prompt(url, tweet_text, extracted_content)
            response = self._call_llm(prompt)
            
            if response:
                analysis = self._extract_json_from_response(response)
                if analysis:
                    # Waliduj wynik
                    required_fields = ["title", "description", "category", "tags", "url"]
                    for field in required_fields:
                        if field not in analysis:
                            analysis[field] = f"Brak {field}" if field != "tags" else []
                    
                    analysis["processing_success"] = True
                    analysis["optimized_prompt"] = True
                    
                    self.logger.info(f"Successfully processed with main prompt: {url[:50]}...")
                    return analysis
            
            # Krok 2: Spróbuj fallback prompts
            self.logger.warning(f"Main prompt failed, trying fallback prompts for {url}")
            analysis = self._try_fallback_prompts(url, tweet_text, extracted_content)
            
            if analysis:
                analysis["processing_success"] = True
                self.logger.info(f"Successfully processed with fallback: {url[:50]}...")
                return analysis
                
            # Krok 3: Ostateczny fallback
            self.logger.warning(f"All prompts failed, using final fallback for {url}")
            return self._create_fallback_result(url, tweet_text)
            
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
        Przetwarza element z zoptymalizowanym promptem multimodalnym.
        """
        url = tweet_data.get('url', '')
        tweet_text = extracted_contents.get('tweet_text', '')
        
        self.logger.info(f"Optimized multimodal processing: {url[:50]}...")
        
        try:
            # Krok 1: Główny zoptymalizowany prompt multimodalny
            prompt = self.create_multimodal_prompt(tweet_data, extracted_contents)
            response = self._call_llm(prompt)
            
            if response:
                analysis = self._extract_json_from_response(response)
                if analysis:
                    # Waliduj wynik
                    required_fields = ["title", "summary", "category", "key_points", "content_types"]
                    for field in required_fields:
                        if field not in analysis:
                            if field == "key_points" or field == "content_types":
                                analysis[field] = []
                            else:
                                analysis[field] = f"Brak {field}"
                    
                    # Dodaj standardowe pola
                    analysis["tweet_url"] = url
                    analysis["processing_success"] = True
                    analysis["multimodal_processing"] = True
                    analysis["optimized_prompt"] = True
                    
                    self.logger.info(f"Successfully processed multimodal with main prompt: {url[:50]}...")
                    return analysis
            
            # Krok 2: Fallback dla multimodal
            self.logger.warning(f"Multimodal prompt failed, using fallback for {url}")
            return self._create_multimodal_fallback(url, tweet_text, extracted_contents)
            
        except Exception as e:
            self.logger.error(f"Multimodal processing error for {url}: {e}")
            return self._create_multimodal_fallback(url, tweet_text, extracted_contents)

    def _create_multimodal_fallback(self, url: str, tweet_text: str, extracted_contents: Dict) -> Dict:
        """Tworzy fallback result dla przetwarzania multimodalnego."""
        
        # Zbierz dostępne treści
        all_texts = [tweet_text] if tweet_text else []
        if extracted_contents.get("article_content"):
            all_texts.append(extracted_contents["article_content"][:100])
        if extracted_contents.get("thread_content"):
            all_texts.append(str(extracted_contents["thread_content"])[:100])
        
        combined_text = " ".join(all_texts)[:200]
        
        # Wykryj typy treści
        content_types = ["tweet"]
        if extracted_contents.get("thread_content"):
            content_types.append("thread")
        if extracted_contents.get("ocr_results"):
            content_types.append("image")
        if extracted_contents.get("video_metadata"):
            content_types.append("video")
        if extracted_contents.get("article_content"):
            content_types.append("article")
        
        return {
            "tweet_url": url,
            "title": combined_text[:50] + "..." if len(combined_text) > 50 else combined_text,
            "summary": "Analiza automatyczna treści multimodalnych",
            "category": "Inne",
            "key_points": ["automatyczna analiza", "treści multimodalne"],
            "content_types": content_types,
            "technical_level": "unknown",
            "has_code": False,
            "estimated_time": "5 min",
            "fallback": True,
            "multimodal_processing": True,
            "processing_success": True
        }

    def close(self):
        """Zamyka zasoby."""
        pass


# Test function
def test_fixed_processing():
    """Test naprawionego procesora."""
    processor = FixedContentProcessor()
    
    # Test z przykładem z CSV
    test_url = "https://x.com/aaditsh/status/1931041095317688786"
    test_tweet = "How to build an app from scratch using the latest AI workflows (76 mins)"
    test_content = "Some extracted content from the webpage..."
    
    print("=== TEST FIXED PROCESSING ===")
    print(f"URL: {test_url}")
    print(f"Tweet: {test_tweet}")
    
    result = processor.process_single_item(test_url, test_tweet, test_content)
    
    if result:
        print("\n✅ WYNIK ANALIZY:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\nTyp wyniku: {type(result)}")
        print(f"Czy ma 'title': {'title' in result}")
    else:
        print("❌ ANALIZA NIEUDANA")
    
    processor.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_fixed_processing() 