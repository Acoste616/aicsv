#!/usr/bin/env python3
"""
Test połączenia z LM Studio API
"""

import requests
import json

def test_lm_studio():
    """Test połączenia z LM Studio"""
    api_base = "http://localhost:1234/v1"
    
    print("[TEST] Testowanie połączenia z LM Studio...")
    
    try:
        # Test połączenia
        response = requests.get(f"{api_base}/models", timeout=10)
        
        if response.status_code == 200:
            models = response.json()
            print("[OK] Połączenie z LM Studio OK!")
            
            if models.get('data'):
                model_name = models['data'][0]['id']
                print(f"[MODEL] Aktywny model: {model_name}")
                
                # Test prostego zapytania
                print("\n[TEST] Testowanie prostego zapytania...")
                
                test_response = requests.post(
                    f"{api_base}/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": model_name,
                        "messages": [
                            {"role": "user", "content": "Odpowiedz tylko: TEST OK"}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 10
                    },
                    timeout=30
                )
                
                if test_response.status_code == 200:
                    result = test_response.json()
                    answer = result['choices'][0]['message']['content'].strip()
                    print(f"[OK] Odpowiedź modelu: {answer}")
                    print("\n[READY] System gotowy do przetwarzania!")
                    return True
                else:
                    print(f"[ERROR] Błąd zapytania: {test_response.status_code}")
                    try:
                        error_details = test_response.json()
                        print(f"[INFO] Szczegóły błędu: {error_details}")
                    except:
                        print(f"[INFO] Raw response: {test_response.text}")
            else:
                print("[ERROR] Brak załadowanego modelu")
        else:
            print(f"[ERROR] Błąd połączenia: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Nie można połączyć z LM Studio")
        print("[INFO] Sprawdź czy:")
        print("   - LM Studio jest uruchomione")
        print("   - Serwer API jest włączony (Local Server -> Start Server)")
        print("   - Model jest załadowany")
        
    except Exception as e:
        print(f"[ERROR] Błąd: {e}")
    
    return False

if __name__ == "__main__":
    test_lm_studio() 