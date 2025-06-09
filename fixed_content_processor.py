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
from typing import Dict, List, Optional
from config import LLM_CONFIG, EXTRACTION_CONFIG

class FixedContentProcessor:
    """
    Naprawiona klasa do przetwarzania treści z lepszym error handling.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_config = LLM_CONFIG.copy()
        self.api_url = self.llm_config["api_url"]

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

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Wywołuje LLM z lepszym error handling."""
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
        """Uproszczone wyciąganie JSON z odpowiedzi LLM."""
        if not response:
            self.logger.error("Empty response from LLM")
            return None
            
        try:
            # Strategia 1: Całość to JSON
            try:
                return json.loads(response.strip())
            except:
                pass
                
            # Strategia 2: Szukaj między { i }
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end+1]
                try:
                    return json.loads(json_str)
                except:
                    pass
                    
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
        Przetwarza pojedynczy element z pełnym error handling.
        """
        self.logger.info(f"Fixed processing: {url[:50]}...")
        
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