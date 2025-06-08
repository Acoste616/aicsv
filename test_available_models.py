#!/usr/bin/env python3
"""
Test wszystkich dostępnych modeli w LM Studio
"""

import requests
import json
import time

def test_model(model_name):
    """Test pojedynczego modelu"""
    print(f"\n🤖 Testowanie: {model_name}")
    print("-" * 50)
    
    simple_prompt = """Zwróć JSON z polami title i summary dla tego tekstu:
"Przewodnik po AI jest bardzo przydatny"

Odpowiedz TYLKO JSON."""

    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": simple_prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
                "stream": False
            },
            timeout=45
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"✅ Odpowiedź w {response_time:.1f}s")
            print(f"📝 Treść ({len(content)} znaków): {content[:150]}...")
            
            # Test JSON
            try:
                json_data = json.loads(content)
                print("✅ JSON poprawny!")
                return True, response_time
            except:
                print("⚠️ JSON niepoprawny, ale model odpowiada")
                return True, response_time
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:100]}")
            return False, 0
            
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return False, 0

def main():
    print("TEST WSZYSTKICH DOSTĘPNYCH MODELI")
    print("=" * 60)
    
    # Lista modeli do testowania
    models = [
        "mistralai/mistral-7b-instruct-v0.3",
        "meta-llama-3.1-8b-instruct-hf", 
        "qwen3-8b",
        "deepseek-r1-distill-llama-8b"
    ]
    
    results = {}
    
    for model in models:
        success, response_time = test_model(model)
        results[model] = {
            'success': success,
            'response_time': response_time
        }
        time.sleep(2)  # Przerwa między testami
    
    # Podsumowanie
    print(f"\n{'='*60}")
    print("📊 PODSUMOWANIE WSZYSTKICH MODELI")
    print("="*60)
    
    working_models = []
    for model, result in results.items():
        model_short = model.split('/')[-1] if '/' in model else model
        status = "✅ DZIAŁA" if result['success'] else "❌ NIE DZIAŁA"
        time_info = f"({result['response_time']:.1f}s)" if result['success'] else ""
        
        print(f"{model_short:30} {status} {time_info}")
        
        if result['success']:
            working_models.append(model)
    
    print(f"\n🏆 REKOMENDACJE:")
    print(f"✅ Działające modele: {len(working_models)}/{len(models)}")
    
    if working_models:
        # Znajdź najszybszy
        fastest = min(working_models, key=lambda m: results[m]['response_time'])
        fastest_short = fastest.split('/')[-1] if '/' in fastest else fastest
        print(f"⚡ Najszybszy: {fastest_short} ({results[fastest]['response_time']:.1f}s)")
        
        # Rekomendacje
        if "mistralai/mistral-7b-instruct-v0.3" in working_models:
            print("🥇 POLECAM: Mistral 7B - najlepszy dla RTX 4050")
        elif "qwen3-8b" in working_models:
            print("🥈 POLECAM: Qwen3 8B - dobra alternatywa")
        elif working_models:
            print(f"🥉 POLECAM: {working_models[0].split('/')[-1]} - jedyny działający")
    else:
        print("❌ Żaden model nie działa - sprawdź LM Studio!")

if __name__ == "__main__":
    main() 