#!/usr/bin/env python3
"""
Prosty test porównawczy Mistral vs poprzedni model
"""

import requests
import json
import time

def test_llm_response(model_name, prompt, temperature=0.3):
    """Test pojedynczej odpowiedzi LLM"""
    print(f"\n=== TEST: {model_name} (temp={temperature}) ===")
    
    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "Jesteś ekspertem analizy treści. Zawsze zwracasz WYŁĄCZNIE poprawny JSON bez dodatkowego tekstu."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": 500,
                "stream": False
            },
            timeout=30
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"✅ Odpowiedź w {response_time:.1f}s ({len(content)} znaków)")
            
            # Próba parsowania JSON
            try:
                json_data = json.loads(content)
                print("✅ JSON poprawny!")
                print(f"📋 Pola: {list(json_data.keys())}")
                return True, json_data, response_time
            except json.JSONDecodeError as e:
                print(f"❌ Błąd JSON: {e}")
                print(f"📝 Fragment odpowiedzi: {content[:200]}...")
                return False, content, response_time
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False, None, 0
            
    except Exception as e:
        print(f"❌ Błąd połączenia: {e}")
        return False, None, 0

def main():
    print("PORÓWNANIE MISTRAL vs LLAMA")
    print("=" * 50)
    
    # Prosty prompt testowy
    test_prompt = """Przeanalizuj ten tweet i zwróć JSON:

Tweet: "Właśnie odkryłem niesamowity przewodnik po systemach RAG z @LangChain! Podejście krok po kroku do strategii chunking to złoto 🔥 https://example.com #AI #RAG"

Zwróć JSON z polami:
- title: krótki tytuł (max 8 słów)
- summary: opis w 2 zdaniach  
- keywords: lista 5 słów kluczowych
- category: jedna z ["Technologia", "Biznes", "Nauka", "Inne"]
- sentiment: ["Pozytywny", "Neutralny", "Negatywny"]

Odpowiedz TYLKO JSON, bez dodatkowego tekstu."""

    models_to_test = [
        "mistralai/mistral-7b-instruct-v0.3",
        "meta-llama-3.1-8b-instruct-hf"  # dla porównania jeśli jest dostępny
    ]
    
    results = {}
    
    for model in models_to_test:
        print(f"\n🤖 Testowanie modelu: {model}")
        
        # Test z różnymi temperaturami
        for temp in [0.2, 0.3, 0.5]:
            success, data, response_time = test_llm_response(model, test_prompt, temp)
            
            if model not in results:
                results[model] = []
            
            results[model].append({
                'temperature': temp,
                'success': success,
                'response_time': response_time,
                'data': data if success else None
            })
            
            time.sleep(1)  # Krótka przerwa
    
    # Podsumowanie
    print("\n" + "=" * 60)
    print("📊 PODSUMOWANIE WYNIKÓW")
    print("=" * 60)
    
    for model, tests in results.items():
        model_name = model.split('/')[-1] if '/' in model else model
        successful_tests = sum(1 for t in tests if t['success'])
        avg_time = sum(t['response_time'] for t in tests if t['success']) / max(successful_tests, 1)
        
        print(f"\n🤖 {model_name}:")
        print(f"   ✅ Sukces: {successful_tests}/{len(tests)} ({successful_tests/len(tests)*100:.0f}%)")
        print(f"   ⏱️  Średni czas: {avg_time:.1f}s")
        
        if successful_tests > 0:
            # Pokaż przykład najlepszej odpowiedzi
            best_test = min([t for t in tests if t['success']], key=lambda x: x['temperature'])
            if best_test['data']:
                print(f"   📋 Przykład (temp={best_test['temperature']}):")
                for key, value in best_test['data'].items():
                    print(f"      {key}: {value}")
    
    # Rekomendacja
    print(f"\n{'='*60}")
    print("🏆 REKOMENDACJA")
    print("="*60)
    
    mistral_success = sum(1 for t in results.get("mistralai/mistral-7b-instruct-v0.3", []) if t['success'])
    llama_success = sum(1 for t in results.get("meta-llama-3.1-8b-instruct-hf", []) if t['success'])
    
    if mistral_success > llama_success:
        print("🥇 MISTRAL 7B wygrywa! Lepsze generowanie JSON.")
    elif llama_success > mistral_success:
        print("🥇 LLAMA 3.1 8B wygrywa! Lepsze generowanie JSON.")
    else:
        print("🤝 Remis - oba modele podobnie skuteczne.")
    
    print(f"\nMistral: {mistral_success}/3 testów")
    print(f"Llama: {llama_success}/3 testów")

if __name__ == "__main__":
    main() 