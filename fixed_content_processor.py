#!/usr/bin/env python3
"""
FIXED CONTENT PROCESSOR
Naprawiona wersja z poprawionym parsowaniem LLM i error handling

NAPRAWIONE PROBLEMY:
1. LLM Response parsing - lepsze wykrywanie i parsowanie JSON
2. None handling - sprawdzanie czy LLM zwróciło cokolwiek
3. Error handling - lepsza obsługa błędów
4. Fallback strategies - działanie nawet przy problemach z ekstrcją
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
    Naprawiona klasa do przetwarzania treści z lepszym error handling i cachingiem.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_config = LLM_CONFIG.copy()
        self.api_url = self.llm_config["api_url"]
        
        # Cache dla LLM
        self.cache_file = Path("cache_llm.json")
        self.llm_cache = self._load_cache()

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
            payload = {
                "model": self.llm_config["model_name"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.llm_config["temperature"],
                "max_tokens": self.llm_config["max_tokens"]
            }
            
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