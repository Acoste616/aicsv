#!/usr/bin/env python3
"""
ULEPSZONA WERSJA - Content Processor
Fokus na lepszej ekstrakcji i przekazuje kontekst do LLM
"""

import json
import re
import requests
import logging
from typing import Dict, List, Optional
from content_extractor import ContentExtractor

class EnhancedContentProcessor:
    """
    Ulepszona klasa do przetwarzania treści z lepszym kontekstem dla LLM.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.extractor = ContentExtractor()
        self.api_url = "http://localhost:1234/v1/chat/completions"
        
        # Konfiguracja LLM
        self.llm_config = {
            "model_name": "mistralai/mistral-7b-instruct-v0.3",
            "temperature": 0.1,
            "max_tokens": 800,
            "timeout": 60
        }

    def extract_enhanced_content(self, url: str, tweet_text: str = "") -> Dict:
        """
        Ekstraktuje treść z lepszym kontekstem i metadata.
        """
        result = {
            "url": url,
            "original_tweet": tweet_text,
            "extracted_content": "",
            "content_type": "",
            "metadata": {},
            "extraction_quality": "unknown"
        }
        
        try:
            # Pobierz podstawową treść
            raw_content = self.extractor.extract_with_retry(url)
            result["extracted_content"] = raw_content
            
            # Określ typ contentu
            result["content_type"] = self._detect_content_type(url, raw_content)
            
            # Wyciągnij metadata w zależności od typu
            if result["content_type"] == "twitter":
                result["metadata"] = self._extract_twitter_metadata(raw_content)
            elif result["content_type"] == "youtube":
                result["metadata"] = self._extract_youtube_metadata(raw_content)
            elif result["content_type"] == "article":
                result["metadata"] = self._extract_article_metadata(raw_content)
            
            # Oceń jakość ekstrakcji
            result["extraction_quality"] = self._assess_extraction_quality(
                raw_content, tweet_text, result["metadata"]
            )
            
            self.logger.info(f"Extracted {len(raw_content)} chars, quality: {result['extraction_quality']}")
            
        except Exception as e:
            self.logger.error(f"Extraction error for {url}: {e}")
            result["extraction_quality"] = "failed"
            
        return result

    def _detect_content_type(self, url: str, content: str) -> str:
        """Określa typ contentu na podstawie URL i treści."""
        url_lower = url.lower()
        content_lower = content.lower()
        
        if "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif any(indicator in content_lower for indicator in ["article", "blog", "post", "read more"]):
            return "article"
        else:
            return "webpage"

    def _extract_twitter_metadata(self, content: str) -> Dict:
        """Wyciąga metadata z Twitter/X."""
        metadata = {}
        
        # Szukaj czasów video w treści
        time_pattern = r'(\d+):(\d+)'
        time_matches = re.findall(time_pattern, content)
        if time_matches:
            # Znajdź najdłuższy czas (prawdopodobnie długość video)
            max_time = max(time_matches, key=lambda x: int(x[0]) * 60 + int(x[1]))
            metadata["video_duration"] = f"{max_time[0]}:{max_time[1]}"
        
        # Szukaj liczby wyświetleń
        views_pattern = r'(\d+(?:,\d+)*)\s*(?:tys\.?\s*)?wyświetleń'
        views_match = re.search(views_pattern, content)
        if views_match:
            metadata["views"] = views_match.group(1)
        
        # Szukaj liczby odpowiedzi
        replies_pattern = r'(\d+)\s*odpowied'
        replies_match = re.search(replies_pattern, content)
        if replies_match:
            metadata["replies"] = replies_match.group(1)
            
        return metadata

    def _extract_youtube_metadata(self, content: str) -> Dict:
        """Wyciąga metadata z YouTube."""
        metadata = {}
        
        # YouTube ma często więcej szczegółów w opisie
        if "subscribe" in content.lower() or "channel" in content.lower():
            metadata["platform"] = "youtube"
            
        return metadata

    def _extract_article_metadata(self, content: str) -> Dict:
        """Wyciąga metadata z artykułów."""
        metadata = {}
        
        # Szacuj czas czytania na podstawie długości
        word_count = len(content.split())
        if word_count > 0:
            reading_time = max(1, word_count // 200)  # ~200 słów na minutę
            metadata["estimated_reading_time"] = f"{reading_time} min"
            
        return metadata

    def _assess_extraction_quality(self, content: str, tweet_text: str, metadata: Dict) -> str:
        """Ocenia jakość wyciągniętej treści."""
        content_length = len(content.strip())
        
        if content_length < 50:
            return "poor"
        elif content_length < 200:
            return "basic"
        elif content_length > 500 or metadata:
            return "good"
        else:
            return "moderate"

    def create_enhanced_prompt(self, extraction_result: Dict) -> str:
        """
        Tworzy zaawansowany prompt z pełnym kontekstem dla LLM.
        """
        
        content_type = extraction_result["content_type"]
        quality = extraction_result["extraction_quality"] 
        extracted_content = extraction_result["extracted_content"]
        tweet_text = extraction_result["original_tweet"]
        metadata = extraction_result["metadata"]
        
        # Przygotuj kontekst w zależności od jakości danych
        context_parts = []
        
        # Dodaj oryginalny tweet
        if tweet_text:
            context_parts.append(f"ORYGINALNY TWEET: {tweet_text}")
        
        # Dodaj wyciągniętą treść
        if extracted_content:
            # Ogranicz długość żeby zmieścić się w context window
            limited_content = extracted_content[:2000] + "..." if len(extracted_content) > 2000 else extracted_content
            context_parts.append(f"TREŚĆ ZE STRONY: {limited_content}")
        
        # Dodaj metadata
        if metadata:
            metadata_str = ", ".join([f"{k}: {v}" for k, v in metadata.items()])
            context_parts.append(f"METADATA: {metadata_str}")
        
        # Dodaj wskazówki dla LLM w zależności od typu i jakości
        quality_instructions = {
            "poor": "UWAGA: Masz ograniczone informacje. Skup się na tym co jest w tweecie i wyciągnij maksimum z dostępnych danych.",
            "basic": "UWAGA: Masz podstawowe informacje. Zrób realistyczną analizę na podstawie dostępnych danych.",
            "good": "Masz dobre informacje. Stwórz szczegółową analizę.",
            "moderate": "Masz umiarkowane informacje. Zrób zbilansowaną analizę."
        }
        
        type_instructions = {
            "twitter": "To tweet, prawdopodobnie zawiera krótką informację lub link do dłuższej treści.",
            "youtube": "To video z YouTube. Jeśli widzisz czas trwania, uwzględnij to w opisie.",
            "article": "To artykuł lub post blogowy.",
            "webpage": "To strona internetowa, przeanalizuj dostępne informacje."
        }
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Przeanalizuj poniższą treść i stwórz JSON z analizą.

{quality_instructions.get(quality, "")}
{type_instructions.get(content_type, "")}

DANE DO ANALIZY:
{context}

WYMAGANY FORMAT JSON:
{{
    "title": "Krótki, opisowy tytuł (max 100 znaków)",
    "short_description": "Zwięzły opis w 1-2 zdaniach",
    "detailed_description": "Szczegółowy opis do 500 słów",
    "category": "AI/Machine Learning lub Biznes lub Rozwój Osobisty lub Technologia lub Inne",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "estimated_time": "Czas czytania/oglądania jeśli da się określić",
    "content_type": "{content_type}",
    "key_points": ["punkt1", "punkt2", "punkt3"]
}}

TYLKO JSON, bez dodatkowych komentarzy:"""

        return prompt

    def analyze_content(self, extraction_result: Dict) -> Optional[Dict]:
        """
        Analizuje treść używając LLM z ulepszonym promptem.
        """
        try:
            prompt = self.create_enhanced_prompt(extraction_result)
            
            # Wywołanie LLM
            response = self._call_llm(prompt)
            if not response:
                return None
                
            # Parsowanie JSON
            analysis = self._extract_json_from_response(response)
            if not analysis:
                return None
                
            # Dodaj metadata o jakości ekstrakcji
            analysis["extraction_quality"] = extraction_result["extraction_quality"]
            analysis["source_url"] = extraction_result["url"]
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Analysis error: {e}")
            return None

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Wywołuje LLM z ulepszonym promptem."""
        try:
            payload = {
                "model": self.llm_config["model_name"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.llm_config["temperature"],
                "max_tokens": self.llm_config["max_tokens"]
            }
            
            response = requests.post(
                self.api_url, 
                json=payload, 
                timeout=self.llm_config["timeout"]
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                self.logger.error(f"LLM API error: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"LLM call error: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """Wyciąga JSON z odpowiedzi LLM."""
        try:
            # Szukaj JSON w różnych formatach
            patterns = [
                r'\{.*\}',
                r'```json\s*(\{.*\})\s*```',
                r'```\s*(\{.*\})\s*```'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    json_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    return json.loads(json_str)
                    
            return None
            
        except Exception as e:
            self.logger.error(f"JSON extraction error: {e}")
            return None

    def process_single_item(self, url: str, tweet_text: str = "") -> Optional[Dict]:
        """
        Przetwarza pojedynczy element z pełnym pipeline.
        """
        self.logger.info(f"Processing: {url}")
        
        # Krok 1: Wyciągnij treść
        extraction_result = self.extract_enhanced_content(url, tweet_text)
        
        # Krok 2: Analizuj z LLM
        analysis = self.analyze_content(extraction_result)
        
        return analysis

    def close(self):
        """Zamyka zasoby."""
        if hasattr(self, 'extractor'):
            self.extractor.close()


# Test function
def test_enhanced_processing():
    """Test nowego procesora."""
    processor = EnhancedContentProcessor()
    
    # Test z przykładem z CSV
    test_url = "https://x.com/aaditsh/status/1931041095317688786"
    test_tweet = "How to build an app from scratch using the latest AI workflows (76 mins)"
    
    print("=== TEST ENHANCED PROCESSING ===")
    print(f"URL: {test_url}")
    print(f"Tweet: {test_tweet}")
    
    result = processor.process_single_item(test_url, test_tweet)
    
    if result:
        print("\n✅ WYNIK ANALIZY:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("❌ ANALIZA NIEUDANA")
    
    processor.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_enhanced_processing() 