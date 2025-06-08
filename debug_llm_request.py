#!/usr/bin/env python3
"""
Debug LLM request - sprawdzenie co wysyłamy do API
"""

import requests
import json

def debug_llm_request():
    """Debuguje żądanie LLM"""
    print("🔍 DEBUG LLM REQUEST")
    print("=" * 50)
    
    # Recreate the exact payload from bookmark_processor_fixed
    payload = {
        "model": "mistralai/mistral-7b-instruct-v0.3",
        "messages": [
            {
                "role": "system", 
                "content": "Jesteś ekspertem analizy treści. Zawsze zwracasz WYŁĄCZNIE poprawny JSON bez dodatkowego tekstu, komentarzy czy formatowania markdown."
            },
            {
                "role": "user",
                "content": "Test prompt: zwróć JSON z title i summary dla tekstu 'test content'"
            }
        ],
        "temperature": 0.2,
        "max_tokens": 750,
        "stream": False
    }
    
    print("📤 Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        print("\n🚀 Wysyłam żądanie...")
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json=payload,
            timeout=30
        )
        
        print(f"📊 Status: {response.status_code}")
        print(f"📝 Headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"❌ Error response: {response.text}")
        else:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"📄 Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")

if __name__ == "__main__":
    debug_llm_request() 