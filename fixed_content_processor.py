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

class FixedContentProcessor:
    """
    Naprawiona klasa do przetwarzania treści z lepszym error handling.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_url = "http://localhost:1234/v1/chat/completions"
        
        # Konfiguracja LLM
        self.llm_config = {
            "model_name": "mistralai/mistral-7b-instruct-v0.3",
            "temperature": 0.1,
            "max_tokens": 1000,
            "timeout": 120  # Więcej czasu
        }

    def create_smart_prompt(self, url: str, tweet_text: str, extracted_content: str = "") -> str:
        """
        Tworzy inteligentny prompt z fallback strategies.
        """
        
        # Określ długość wyciągniętej treści
        content_length = len(extracted_content.strip())
        
        # Przygotuj kontekst w zależności od dostępnych danych
        if content_length > 200:
            # Mamy dużo danych
            context = f"""
ORYGINALNY TWEET: {tweet_text}

SZCZEGÓŁOWA TREŚĆ ZE STRONY:
{extracted_content[:1500]}...
"""
            instruction = "Masz bogate informacje. Stwórz szczegółową analizę."
            
        elif content_length > 50:
            # Mamy średnio danych
            context = f"""
ORYGINALNY TWEET: {tweet_text}

TREŚĆ ZE STRONY:
{extracted_content}
"""
            instruction = "Masz podstawowe informacje. Zrób realistyczną analizę."
            
        else:
            # Mamy tylko tweet
            context = f"""
ORYGINALNY TWEET: {tweet_text}

DODATKOWE INFO: Nie udało się pobrać szczegółowej treści ze strony.
"""
            instruction = "Masz tylko tweet. Przeanalizuj go i wywnioskuj co możesz na podstawie dostępnych informacji."

        prompt = f"""Przeanalizuj poniższą treść i stwórz JSON z kategoryzacją.

{instruction}

DANE DO ANALIZY:
{context}

WYMAGANY FORMAT JSON (WAŻNE: tylko czysty JSON, bez komentarzy):
{{
    "title": "Krótki, opisowy tytuł (max 100 znaków)",
    "short_description": "Zwięzły opis w 1-2 zdaniach",
    "detailed_description": "Szczegółowy opis do 300 słów",
    "category": "AI/Machine Learning lub Biznes lub Rozwój Osobisty lub Technologia lub Inne",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "estimated_time": "Czas czytania/oglądania jeśli da się określić",
    "content_type": "tweet/article/video/webpage",
    "key_points": ["punkt1", "punkt2", "punkt3"]
}}

TYLKO JSON:"""

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
        """Ulepszone wyciąganie JSON z odpowiedzi LLM."""
        if not response:
            self.logger.error("Empty response from LLM")
            return None
            
        try:
            # Strategia 1: Całość to JSON
            try:
                return json.loads(response.strip())
            except:
                pass
                
            # Strategia 2: JSON w bloku ```json```
            json_pattern = r'```json\s*(\{.*?\})\s*```'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                return json.loads(match.group(1))
                
            # Strategia 3: JSON w bloku ```
            json_pattern = r'```\s*(\{.*?\})\s*```'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                return json.loads(match.group(1))
                
            # Strategia 4: Znajdź największy blok JSON
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, response, re.DOTALL)
            
            for match in sorted(matches, key=len, reverse=True):
                try:
                    return json.loads(match)
                except:
                    continue
                    
            # Strategia 5: Fallback - spróbuj znaleźć choćby fragment
            self.logger.warning(f"Could not parse JSON from response: {response[:200]}...")
            return None
            
        except Exception as e:
            self.logger.error(f"JSON extraction error: {e}")
            return None

    def _create_fallback_result(self, url: str, tweet_text: str) -> Dict:
        """Tworzy fallback result gdy LLM zawiedzie."""
        return {
            "title": tweet_text[:80] + "..." if len(tweet_text) > 80 else tweet_text,
            "short_description": "Analiza automatyczna na podstawie tweeta",
            "detailed_description": f"Tweet: {tweet_text}. Nie udało się przeprowadzić pełnej analizy.",
            "category": "Inne",
            "tags": ["tweet", "automatyczna"],
            "estimated_time": "1 min",
            "content_type": "tweet",
            "key_points": [tweet_text[:100]],
            "fallback": True,
            "source_url": url
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
            required_fields = ["title", "short_description", "category"]
            for field in required_fields:
                if field not in analysis:
                    self.logger.warning(f"Missing field {field} in LLM response for {url}")
                    analysis[field] = f"Brak {field}"
                    
            # Dodaj metadata
            analysis["source_url"] = url
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