#!/usr/bin/env python3
"""
PRZYKŁADY ZOPTYMALIZOWANYCH PROMPTÓW DLA CLOUD LLM

Optymalizacje:
1. Prompty skrócone o 50-70% - używamy few-shot zamiast długich instrukcji
2. JSON mode dla GPT-4 z response_format
3. Temperature=0.1 dla konsystencji
4. Fallback prompts dla error recovery
5. Kompaktowe dane wejściowe
"""

import json

# PRZYKŁAD 1: Podstawowy prompt (z ~250 słów do ~80 słów)
BASIC_PROMPT_OLD = """
Przeanalizuj poniższe dane i zwróć TYLKO poprawny JSON (bez żadnego dodatkowego tekstu):

Tweet: {tweet_text}
Dodatkowa treść: {extracted_content}

Zwróć dokładnie taki format JSON:
{
    "title": "Krótki tytuł do 10 słów",
    "short_description": "Opis w 1-2 zdaniach",
    "category": "Technologia",
    "tags": ["tag1", "tag2", "tag3"],
    "url": "{url}"
}

Zasady:
- title: maksymalnie 10 słów, czytelny i treściwy
- short_description: 1-2 zdania podsumowujące główną ideę
- category: wybierz jedną z: Technologia, Biznes, Edukacja, Nauka, Inne
- tags: 3-5 tagów związanych z treścią
- url: zachowaj oryginalny URL

Przykład poprawnej odpowiedzi:
{
    "title": "Budowanie systemów RAG z LangChain",
    "short_description": "Przewodnik pokazuje jak tworzyć systemy RAG używając LangChain z fokusem na strategie podziału tekstu.",
    "category": "Technologia",
    "tags": ["RAG", "LangChain", "AI"],
    "url": "https://example.com"
}
"""

BASIC_PROMPT_OPTIMIZED = '''Analizuj treść i zwróć JSON. Przykłady:

Input: {"tweet": "Nowy framework do budowania RAG w Pythonie", "content": "LangChain 0.1 wprowadza nowe API..."}
Output: {"title": "LangChain 0.1 - framework RAG", "short_description": "Nowe API do budowania systemów RAG w Pythonie z LangChain 0.1", "category": "Technologia", "tags": ["RAG", "LangChain", "Python"], "url": "https://example.com"}

Input: {"tweet": "Analiza rynku krypto 2024", "content": "Bitcoin osiągnął nowe ATH..."}
Output: {"title": "Bitcoin ATH - analiza rynku 2024", "short_description": "Analiza wzrostu Bitcoina i prognozy na 2024 rok", "category": "Biznes", "tags": ["Bitcoin", "krypto", "inwestycje"], "url": "https://example.com"}

Teraz przeanalizuj:
{input_data}
Output:'''

# PRZYKŁAD 2: Multimodal prompt (z ~400 słów do ~120 słów)
MULTIMODAL_PROMPT_OPTIMIZED = '''Analizuj dane multimodalne. Przykłady:

Input: {"tweet": "Thread o ML pipelines", "article": "Budowanie produkcyjnych pipeline'ów ML...", "images": 3, "thread": 5, "video": false}
Output: {"tweet_url": "https://x.com/123", "title": "Pipeline ML w produkcji - kompletny przewodnik", "summary": "Thread opisuje budowanie produkcyjnych pipeline'ów ML z przykładami kodu i diagramami. Zawiera 5 części pokrywających architekturę, monitoring i deployment.", "category": "Technologia", "key_points": ["Architektura pipeline ML", "Monitoring modeli", "Deployment strategii"], "content_types": ["thread", "image", "article"], "technical_level": "advanced", "has_code": true, "estimated_time": "15 min"}

Input: {"tweet": "Nowa strategia inwestycyjna 2024", "article": null, "images": 1, "thread": 0, "video": true}
Output: {"tweet_url": "https://x.com/456", "title": "Strategia inwestycyjna na 2024", "summary": "Wideo prezentuje analizę rynku i strategię inwestycyjną na 2024. Omawia trendy makroekonomiczne i konkretne sektory.", "category": "Biznes", "key_points": ["Analiza makro", "Sektory wzrostowe", "Risk management"], "content_types": ["video", "image"], "technical_level": "intermediate", "has_code": false, "estimated_time": "20 min"}

Analizuj:
{input_data}
Output:'''

# PRZYKŁAD 3: Fallback prompt (ultra-prosty)
FALLBACK_PROMPT = '''Stwórz prosty JSON dla tego tweeta:

Tweet: "{tweet_text}"

Format: {"title": "tytuł", "category": "kategoria"}
Przykład: {"title": "Analiza rynku AI", "category": "Technologia"}

JSON dla tweeta:'''

# PRZYKŁAD UŻYCIA Z GPT-4 JSON MODE
def call_gpt4_with_json_mode(prompt: str):
    """Przykład wywołania GPT-4 z JSON mode."""
    import requests
    
    payload = {
        "model": "gpt-4-1106-preview",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant designed to output JSON. Always respond with valid JSON only, no additional text."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,  # Niska temperatura dla konsystencji
        "max_tokens": 500,
        "response_format": {"type": "json_object"}  # JSON mode
    }
    
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        json=payload,
        headers={
            "Authorization": "Bearer YOUR_API_KEY",
            "Content-Type": "application/json"
        }
    )
    
    return response.json()

def enrich_fallback_result(fallback_result: dict) -> dict:
    """Wzbogaca minimalny wynik z fallback prompt."""
    return {
        "title": fallback_result.get("title", "Brak tytułu"),
        "short_description": f"Analiza: {fallback_result.get('title', '')}",
        "category": fallback_result.get("category", "Inne"),
        "tags": [fallback_result.get("category", "inne").lower()],
        "from_fallback": True
    }

# PRZYKŁAD ERROR HANDLING Z FALLBACK
def process_with_fallback(main_prompt: str, fallback_prompt: str) -> dict:
    """Przykład przetwarzania z fallback."""
    try:
        # Próba 1: Główny prompt
        response = call_gpt4_with_json_mode(main_prompt)
        result = parse_json_response(response)
        
        if result:
            return result
        
        # Próba 2: Fallback prompt
        print("Main parsing failed, trying fallback...")
        fallback_response = call_gpt4_with_json_mode(fallback_prompt)
        fallback_result = parse_json_response(fallback_response)
        
        if fallback_result:
            return enrich_fallback_result(fallback_result)
        
        # Próba 3: Hardcoded fallback
        return {
            "title": "Analiza automatyczna",
            "category": "Inne",
            "fallback": True
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            "title": "Błąd przetwarzania",
            "category": "Inne",
            "error": str(e)
        }

def parse_json_response(response: dict) -> dict:
    """Bezpieczne parsowanie odpowiedzi."""
    try:
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except:
        return {}

# PORÓWNANIE DŁUGOŚCI PROMPTÓW
print("OPTYMALIZACJA PROMPTÓW - STATYSTYKI:")
print(f"Podstawowy prompt - przed: {len(BASIC_PROMPT_OLD.split())} słów")
print(f"Podstawowy prompt - po: {len(BASIC_PROMPT_OPTIMIZED.split())} słów")
print(f"Redukcja: {(1 - len(BASIC_PROMPT_OPTIMIZED.split())/len(BASIC_PROMPT_OLD.split()))*100:.0f}%")
print(f"\nMultimodal prompt - zoptymalizowany: {len(MULTIMODAL_PROMPT_OPTIMIZED.split())} słów")
print(f"Fallback prompt: {len(FALLBACK_PROMPT.split())} słów")

# KLUCZOWE OPTYMALIZACJE:
"""
1. FEW-SHOT EXAMPLES: Zamiast opisywać format, pokazujemy 2-3 przykłady
2. KOMPAKTOWE DANE: Input jako JSON, nie długi tekst
3. BRAK REDUNDANCJI: Usunięte powtórzenia i oczywiste instrukcje
4. JSON MODE: response_format dla GPT-4 gwarantuje poprawny JSON
5. TEMPERATURE 0.1: Maksymalna konsystencja wyników
6. FALLBACK CHAIN: Główny -> Fallback -> Hardcoded
"""