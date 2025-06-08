#!/usr/bin/env python3
"""
Test różnych modeli LLM dla RTX 4050 + 16GB RAM
Testuje Mistral 7B, Llama 3.2 7B, Phi-3 Medium z optymalnymi ustawieniami
"""

import json
import time
import requests
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelTester:
    def __init__(self):
        self.api_url = "http://localhost:1234/v1/chat/completions"
        self.session = requests.Session()
        
        # Modele do testowania (w kolejności preferencji dla RTX 4050)
        self.models_to_test = [
            {
                "name": "mistral-7b-instruct-v0.3-q4-k-m", 
                "id": "mistral-7b-instruct-v0.3-q4-k-m.gguf",
                "description": "Mistral 7B Q4_K_M - najlepsza opcja dla RTX 4050"
            },
            {
                "name": "llama-3.2-7b-instruct-q5-k-m",
                "id": "llama-3.2-7b-instruct-q5-k-m.gguf", 
                "description": "Llama 3.2 7B Q5_K_M - dobry balans"
            },
            {
                "name": "phi-3-medium-4k-instruct-q4-k-m",
                "id": "phi-3-medium-4k-instruct-q4-k-m.gguf",
                "description": "Phi-3 Medium Q4_K_M - szybka opcja"
            }
        ]

    def get_available_models(self) -> List[str]:
        """Sprawdza dostępne modele w LM Studio"""
        try:
            response = requests.get(f"http://localhost:1234/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                available = [model['id'] for model in models.get('data', [])]
                logger.info(f"Dostępne modele: {available}")
                return available
            return []
        except Exception as e:
            logger.error(f"Błąd sprawdzania modeli: {e}")
            return []

    def create_optimized_prompt(self, tweet_text: str, article_content: str = "") -> str:
        """Tworzy zoptymalizowany prompt dla analizy tweeta"""
        
        context = f"Tweet: {tweet_text[:300]}"
        if article_content and len(article_content) > 50:
            context += f"\n\nTreść artykułu: {article_content[:1500]}"
        
        prompt = f"""Przeanalizuj poniższy tweet i zwróć TYLKO poprawny JSON.

{context}

Zwróć analizę w formacie:
{{
    "title": "Konkretny tytuł opisujący główny temat",
    "summary": "Krótkie podsumowanie głównych punktów (50-150 słów)",
    "keywords": ["słowo1", "słowo2", "słowo3", "słowo4", "słowo5"],
    "category": "Technologia/Biznes/Nauka/Rozrywka/Inne",
    "sentiment": "Pozytywny/Neutralny/Negatywny",
    "estimated_reading_time_minutes": 5,
    "difficulty": "Łatwy/Średni/Trudny",
    "key_takeaways": [
        "Praktyczny wniosek 1",
        "Praktyczny wniosek 2"
    ]
}}

UWAGA: Zwróć TYLKO JSON, bez dodatkowego tekstu."""

        return prompt

    def test_model_with_optimal_settings(self, model_id: str, prompt: str) -> Optional[Dict]:
        """Testuje model z optymalnymi ustawieniami"""
        
        # Optymalne ustawienia dla każdego typu modelu
        if "mistral" in model_id.lower():
            temperature = 0.3  # Mistral lubi niską temperaturę
            max_tokens = 800
        elif "llama" in model_id.lower():
            temperature = 0.4  # Llama trochę wyższą
            max_tokens = 900
        elif "phi" in model_id.lower():
            temperature = 0.2  # Phi bardzo niską
            max_tokens = 700
        else:
            temperature = 0.3
            max_tokens = 800

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": "Jesteś ekspertem w analizie treści. Zawsze zwracasz poprawny JSON bez dodatkowego tekstu."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "stop": ["```", "\n\n---", "Podsumowanie:"]
        }

        try:
            start_time = time.time()
            response = self.session.post(
                self.api_url,
                json=payload,
                timeout=60
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                logger.info(f"✅ Model {model_id} odpowiedział w {response_time:.1f}s")
                logger.info(f"📄 Długość odpowiedzi: {len(content)} znaków")
                
                return {
                    'model': model_id,
                    'response': content,
                    'response_time': response_time,
                    'temperature': temperature,
                    'success': True
                }
            else:
                logger.error(f"❌ Model {model_id} - błąd HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Model {model_id} - błąd: {e}")
            return None

    def extract_and_validate_json(self, text: str) -> Optional[Dict]:
        """Wyciąga i waliduje JSON z odpowiedzi"""
        if not text:
            return None
            
        # Znajdź JSON
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end + 1]
            try:
                data = json.loads(json_str)
                
                # Walidacja podstawowa
                required_fields = ['title', 'summary', 'keywords', 'category']
                if all(field in data for field in required_fields):
                    if len(data.get('keywords', [])) >= 3:
                        return data
                        
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                
        return None

    def run_comprehensive_test(self):
        """Uruchamia kompleksowy test modeli"""
        
        logger.info("🚀 ROZPOCZYNAM TEST LEPSZYCH MODELI LLM")
        logger.info("=" * 60)
        
        # Sprawdź dostępne modele
        available_models = self.get_available_models()
        if not available_models:
            logger.error("❌ Brak dostępnych modeli w LM Studio!")
            return
            
        # Test cases
        test_cases = [
            {
                "tweet": "Odkryłem niesamowity przewodnik do budowania systemów RAG z @LangChain! Krok po kroku podejście do strategii chunking to złoto. https://t.co/example123",
                "article": "LangChain RAG Guide: Building effective retrieval systems requires careful consideration of chunking strategies. Best practices include semantic chunking, overlap management, and vector store optimization.",
                "description": "Test techniczny - RAG systems"
            },
            {
                "tweet": "Nowa wersja VS Code z AI Copilot integration jest niesamowita! Productivity boost x10 💻 https://t.co/vscode456", 
                "article": "VS Code AI features include intelligent code completion, automated refactoring, and context-aware suggestions that significantly improve developer productivity.",
                "description": "Test programistyczny - VS Code AI"
            },
            {
                "tweet": "Climate change data shows alarming trends. New study reveals 2024 hottest year on record. We need immediate action! 🌍 https://t.co/climate789",
                "article": "Climate research indicates unprecedented global temperature increases. The study analyzed data from 1880-2024, showing accelerating warming trends with significant implications for policy.",
                "description": "Test naukowy - zmiana klimatu"
            }
        ]

        results = {}
        
        for model_info in self.models_to_test:
            model_id = model_info["id"]
            model_name = model_info["name"]
            
            # Sprawdź czy model jest dostępny
            if not any(model_id in available for available in available_models):
                logger.warning(f"⚠️ Model {model_name} nie jest dostępny")
                logger.info(f"💡 Aby go pobrać, wejdź w LM Studio i pobierz: {model_id}")
                continue
                
            logger.info(f"\n🧪 TESTOWANIE: {model_info['description']}")
            logger.info("-" * 50)
            
            model_results = []
            
            for i, test_case in enumerate(test_cases):
                logger.info(f"\n📝 Test {i+1}/3: {test_case['description']}")
                
                prompt = self.create_optimized_prompt(
                    test_case['tweet'], 
                    test_case['article']
                )
                
                result = self.test_model_with_optimal_settings(model_id, prompt)
                
                if result:
                    # Sprawdź jakość JSON
                    parsed_json = self.extract_and_validate_json(result['response'])
                    
                    if parsed_json:
                        logger.info(f"✅ JSON poprawny!")
                        logger.info(f"📋 Tytuł: {parsed_json.get('title', 'Brak')[:50]}...")
                        logger.info(f"🏷️ Kategoria: {parsed_json.get('category', 'Brak')}")
                        logger.info(f"⏱️ Czas: {result['response_time']:.1f}s")
                        
                        result['json_valid'] = True
                        result['parsed_json'] = parsed_json
                    else:
                        logger.warning(f"⚠️ JSON niepoprawny lub niekompletny")
                        logger.info(f"📄 Fragment odpowiedzi: {result['response'][:100]}...")
                        result['json_valid'] = False
                        
                    model_results.append(result)
                else:
                    logger.error(f"❌ Model nie odpowiedział")
                    
                time.sleep(1)  # Krótka przerwa między testami
            
            results[model_name] = model_results

        # Podsumowanie wyników
        self.print_summary(results)

    def print_summary(self, results: Dict):
        """Drukuje podsumowanie wyników testów"""
        
        logger.info(f"\n🏆 PODSUMOWANIE TESTÓW")
        logger.info("=" * 60)
        
        for model_name, model_results in results.items():
            if not model_results:
                continue
                
            valid_json_count = sum(1 for r in model_results if r.get('json_valid', False))
            avg_response_time = sum(r['response_time'] for r in model_results) / len(model_results)
            
            logger.info(f"\n📊 {model_name}:")
            logger.info(f"   ✅ Poprawne JSON: {valid_json_count}/3")
            logger.info(f"   ⏱️ Średni czas: {avg_response_time:.1f}s")
            logger.info(f"   📈 Sukces: {(valid_json_count/3)*100:.0f}%")
            
            if valid_json_count == 3:
                logger.info(f"   🌟 IDEALNY WYNIK!")
            elif valid_json_count >= 2:
                logger.info(f"   👍 DOBRY WYNIK!")
            else:
                logger.info(f"   👎 SŁABY WYNIK")

        # Rekomendacje
        logger.info(f"\n💡 REKOMENDACJE:")
        logger.info("- Jeśli żaden model nie działa dobrze, spróbuj:")
        logger.info("  1. Obniżyć temperature do 0.1-0.2")
        logger.info("  2. Dodać więcej przykładów do prompta")
        logger.info("  3. Uprościć zadanie analizy")
        logger.info("  4. Sprawdzić czy LM Studio używa GPU")

def main():
    """Główna funkcja"""
    tester = ModelTester()
    
    print("🔧 TESTER LEPSZYCH MODELI LLM dla RTX 4050")
    print("=" * 50)
    print("Ten skrypt przetestuje najlepsze modele dla Twojego sprzętu:")
    print("• Mistral 7B Instruct (Q4_K_M) - ~4GB VRAM")
    print("• Llama 3.2 7B (Q5_K_M) - ~5GB VRAM") 
    print("• Phi-3 Medium (Q4_K_M) - ~7GB VRAM")
    print()
    print("💡 Jeśli model nie jest dostępny, pobierz go w LM Studio")
    print()
    
    input("Naciśnij Enter aby rozpocząć testy...")
    
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main() 