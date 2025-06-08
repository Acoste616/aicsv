#!/usr/bin/env python3
"""
Skrypt diagnostyczny do testowania jakości analiz LLM
Pomaga zidentyfikować problemy z generowaniem JSON
"""

import requests
import json
import time
from content_extractor import ContentExtractor

def test_single_tweet_analysis():
    """Testuje analizę pojedynczego tweeta z pełnym debugowaniem."""
    
    # Przykładowy tweet do testowania
    test_tweet = {
        'id': 'test_123',
        'full_text': 'Just discovered this amazing guide on building RAG systems with @LangChain! '
                     'The step-by-step approach to chunking strategies is gold 🔥 '
                     'https://t.co/example123 #AI #RAG #LangChain',
        'created_at': '2024-11-15 10:00:00'
    }
    
    print("TEST ANALIZY POJEDYNCZEGO TWEETA")
    print("=" * 50)
    print(f"Tweet: {test_tweet['full_text'][:100]}...")
    
    # Test 1: Ekstrakcja treści
    print("\n📄 TEST 1: Ekstrakcja treści ze strony...")
    extractor = ContentExtractor()
    
    # Lista URL do testowania - prawdziwe linki z tweetów (różne typy treści)
    test_urls = [
        "https://t.co/0lLjxGSCue",  # Nowy link testowy 1
        "https://t.co/d0wPyTGnDh",  # Nowy link testowy 2
        "https://t.co/FCUsmol5XR",  # Poprzedni działający
        "https://github.com/langchain-ai/langchain",  # GitHub - referencyjny
        "https://openai.com/blog/chatgpt",  # OpenAI - trudny przypadek
    ]
    
    content = ""
    success_count = 0
    total_chars = 0
    
    for i, test_url in enumerate(test_urls, 1):
        print(f"\n🔗 URL {i}/{len(test_urls)}: {test_url}")
        content = extractor.extract_with_retry(test_url, max_retries=2)
    
        
        if content and len(content) > 100:  # Obniżony próg
            char_count = len(content)
            total_chars += char_count
            print(f"✅ Pobrano {char_count} znaków")
            print(f"📝 Fragment: {content[:200]}...")
            
            # Sprawdź jakość treści
            if char_count < 200:
                print("⚠️  Treść krótka - może być niepełna")
            elif "javascript" in content.lower()[:200]:
                print("⚠️  Możliwy komunikat o błędzie JavaScript!")
            elif "treść niedostępna" in content.lower():
                print("⚠️  Treść niedostępna - strona blokuje boty")
            elif char_count > 500:
                print("✅ Treść wygląda bardzo dobrze!")
                success_count += 1
            else:
                print("✅ Treść wygląda dobrze!")
                success_count += 1
                
            # Użyj pierwszej dobrej treści do dalszej analizy
            if char_count > 300:
                break
        else:
            print(f"❌ Niewystarczająca treść ({len(content) if content else 0} znaków)")
    
    # Jeśli żaden URL nie zadziałał, użyj dummy content
    if not content or len(content) < 300:
        print("\n⚠️  Używam przykładowej treści do testów...")
        content = """
        LangChain is a framework for developing applications powered by language models. 
        It enables applications that are context-aware and can reason. The framework provides 
        modular components for working with LLMs, including prompt templates, chains, agents, 
        and memory systems. This guide covers RAG (Retrieval Augmented Generation) implementation 
        with best practices for chunking strategies, vector stores, and retrieval optimization.
        """
    
    # Test 2: Prompt Generation
    print("\n🎯 TEST 2: Generowanie prompta...")
    prompt = create_test_prompt(test_tweet['full_text'], content)
    print(f"📏 Długość prompta: {len(prompt)} znaków")
    
    # Test 3: LLM Query
    print("\n🤖 TEST 3: Zapytanie do LLM...")
    
    for temperature in [0.3, 0.5, 0.7]:
        print(f"\n--- Testowanie z temperature={temperature} ---")
        response = query_llm_test(prompt, temperature)
        
        if response:
            print(f"✅ Otrzymano odpowiedź ({len(response)} znaków)")
            
            # Próba parsowania JSON
            json_data = extract_json(response)
            if json_data:
                print("✅ JSON parsed successfully!")
                print(json.dumps(json_data, indent=2, ensure_ascii=False)[:500])
                
                # Walidacja jakości
                quality_score = validate_quality(json_data)
                print(f"\n📊 Ocena jakości: {quality_score}/10")
                
                if quality_score < 7:
                    print("⚠️ Niska jakość - sprawdź:")
                    print("  - Czy treść artykułu jest poprawnie pobrana?")
                    print("  - Czy prompt zawiera dość kontekstu?")
                    print("  - Czy model nie jest przeciążony?")
            else:
                print("❌ Nie udało się sparsować JSON!")
                print(f"Odpowiedź: {response[:300]}...")
        else:
            print("❌ Brak odpowiedzi od LLM")
        
        time.sleep(2)
    
    # Podsumowanie testów ekstrakcji treści
    print(f"\n{'='*60}")
    print("📊 PODSUMOWANIE EKSTRAKCJI TREŚCI")
    print(f"{'='*60}")
    print(f"✅ Sukces: {success_count}/{len(test_urls)} ({(success_count/len(test_urls))*100:.0f}%)")
    print(f"📏 Średnia długość: {total_chars//len(test_urls) if total_chars > 0 else 0} znaków")
    print(f"📈 Łączna treść: {total_chars} znaków")
    
    if success_count >= 4:
        print("🎉 DOSKONAŁY WYNIK! Ekstrakcja treści działa świetnie!")
    elif success_count >= 3:
        print("✅ DOBRY WYNIK! Większość stron działa poprawnie")
    elif success_count >= 2:
        print("⚠️  ŚREDNI WYNIK - wymaga dalszych optymalizacji")
    else:
        print("❌ SŁABY WYNIK - potrzebne poważne poprawki ekstraktora")
    
    extractor.close()

def create_test_prompt(tweet_text, article_content):
    """Tworzy prompt testowy."""
    return f"""Jesteś ekspertem w analizie treści. Przeanalizuj tweet i artykuł.

Tweet: {tweet_text}

Artykuł: {article_content[:1500] if article_content else "Brak treści"}

Stwórz analizę w formacie JSON z polami:
- title: konkretny tytuł (max 10 słów)
- summary: opis 2-3 zdania
- keywords: lista 5-7 słów kluczowych
- category: jedna z ["Technologia", "Nauka", "Biznes", "Społeczne", "Inne"]
- sentiment: ["Pozytywny", "Neutralny", "Negatywny"]
- estimated_reading_time_minutes: liczba
- difficulty: ["Łatwy", "Średni", "Trudny"]
- key_takeaways: lista 3-5 wniosków

Odpowiedz TYLKO poprawnym JSON, bez dodatkowego tekstu."""

def query_llm_test(prompt, temperature):
    """Testowe zapytanie do LLM."""
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": "mistralai/mistral-7b-instruct-v0.3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": 800,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Błąd: {e}")
    
    return None

def extract_json(text):
    """Wyciąga JSON z tekstu."""
    import re
    
    if not text:
        return None

    # Metoda 1: markdown block
    match = re.search(r'```(?:json)?\s*(\\{.*?\\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # Metoda 2: znajdź JSON
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except:
            pass
    
    return None

def validate_quality(data):
    """Ocenia jakość analizy (0-10)."""
    score = 0
    
    if not data:
        return 0

    # Sprawdź obecność pól
    required_fields = ['title', 'summary', 'keywords', 'category', 'key_takeaways']
    for field in required_fields:
        if field in data and data[field]:
            score += 1
    
    # Sprawdź jakość
    if len(data.get('title', '')) > 10:
        score += 1
    if len(data.get('summary', '')) > 50:
        score += 1
    if len(data.get('keywords', [])) >= 5:
        score += 1
    if len(data.get('key_takeaways', [])) >= 3:
        score += 1
    
    # Sprawdź czy nie jest generyczne
    generic_terms = ['javascript', 'błąd', 'nie dostępny', 'brak treści']
    summary_lower = str(data.get('summary', '')).lower()
    title_lower = str(data.get('title', '')).lower()

    if not any(term in title_lower for term in generic_terms) and \
       not any(term in summary_lower for term in generic_terms):
        score += 1
    
    return score

def test_llm_variations():
    """Testuje różne warianty promptów."""
    print("\n🔬 TEST RÓŻNYCH PROMPTÓW")
    print("=" * 50)
    
    test_content = """
    OpenAI announced Canvas, a new interface for working with ChatGPT that enables 
    real-time collaboration on coding projects. Users can now edit code directly 
    within the interface, receive inline suggestions, and iterate on projects 
    without constantly copying and pasting. The feature supports multiple 
    programming languages and includes automatic formatting.
    """
    
    prompts = [
        # Prosty prompt
        "Analyze this: " + test_content + "\nReturn JSON with title, summary, keywords.",
        
        # Szczegółowy prompt
        f"""You are analyzing tech content. Create a JSON analysis:
{test_content}

Required JSON structure:
{{"title": "...", "summary": "...", "keywords": [...], "category": "..."}}""",
        
        # Z przykładem
        f"""Example output: {{"title": "AI Breakthrough", "summary": "New model", "keywords": ["AI"]}}

Now analyze: {test_content}

Output JSON:"""
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n--- Prompt {i} ---")
        response = query_llm_test(prompt, 0.5)
        if response:
            print(f"Response: {response[:200]}...")
            if extract_json(response):
                print("✅ Valid JSON generated")
            else:
                print("❌ Invalid JSON")
        time.sleep(2)

def diagnose_content_extraction():
    """Diagnozuje problemy z ekstrakcją treści."""
    print("\n🔍 DIAGNOZA EKSTRAKCJI TREŚCI")
    print("=" * 50)
    
    test_urls = [
        "https://t.co/0lLjxGSCue",  # Nowy link testowy 1
        "https://t.co/d0wPyTGnDh",  # Nowy link testowy 2
        "https://t.co/FCUsmol5XR",  # Poprzedni działający
        "https://github.com/langchain-ai/langchain",  # GitHub - referencyjny
        "https://openai.com/blog/chatgpt",  # OpenAI - trudny
    ]
    
    extractor = ContentExtractor()
    
    for url in test_urls:
        print(f"\n📎 Testowanie: {url}")
        content = extractor.extract_with_retry(url)
        
        if content:
            print(f"✅ Sukces: {len(content)} znaków")
            # Sprawdź jakość
            if "javascript" in content.lower() and len(content) < 200:
                print("⚠️ Możliwy błąd JS - treść zbyt krótka")
            if "<" in content and ">" in content:
                print("⚠️ Możliwe tagi HTML w treści")
        else:
            print("❌ Brak treści")
    
    extractor.close()

def compare_extraction_methods():
    """Porównuje starą i nową metodę ekstrakcji."""
    print("\n🔬 PORÓWNANIE METOD EKSTRAKCJI")
    print("=" * 50)
    
    test_urls = [
        ("Twitter Link 1", "https://t.co/0lLjxGSCue"),
        ("Twitter Link 2", "https://t.co/d0wPyTGnDh"), 
        ("Twitter Link 3", "https://t.co/FCUsmol5XR"),
        ("GitHub LangChain", "https://github.com/langchain-ai/langchain"),
        ("OpenAI ChatGPT", "https://openai.com/blog/chatgpt"),
    ]
    
    extractor = ContentExtractor()
    
    for name, url in test_urls:
        print(f"\n📎 {name} ({url})")
        print("-" * 40)
        
        # Test 1: Podstawowa metoda (jeden raz)
        start_time = time.time()
        basic_content = extractor.get_webpage_content(url)
        basic_time = time.time() - start_time
        
        print(f"Podstawowa metoda (1 próba):")
        print(f"  ⏱️  Czas: {basic_time:.2f}s")
        print(f"  📏 Długość: {len(basic_content)} znaków")
        
        if len(basic_content) < 300:
            print(f"  ⚠️  PROBLEM: Za mało treści!")
        
        # Test 2: Metoda z retry
        start_time = time.time()
        retry_content = extractor.extract_with_retry(url, max_retries=2)
        retry_time = time.time() - start_time
        
        print(f"\nMetoda z retry:")
        print(f"  ⏱️  Czas: {retry_time:.2f}s")
        print(f"  📏 Długość: {len(retry_content)} znaków")
        
        if len(retry_content) > len(basic_content):
            if len(basic_content) > 0:
                improvement = ((len(retry_content) - len(basic_content)) / len(basic_content)) * 100
                print(f"  ✅ LEPSZE o {improvement:.0f}%!")
            else:
                print(f"  ✅ LEPSZE (z 0 do {len(retry_content)} znaków)!")

        # Analiza treści
        if retry_content:
            error_phrases = ['javascript', 'enable', 'browser', 'not supported']
            is_error = any(phrase in retry_content.lower()[:200] for phrase in error_phrases)
            
            if is_error:
                print(f"  ⚠️  Wykryto możliwy komunikat błędu")
            else:
                print(f"  ✅ Treść wygląda poprawnie")
        
        time.sleep(1)  # Nie przeciążaj serwerów
    
    extractor.close()

if __name__ == "__main__":
    print("DIAGNOSTYKA BOOKMARK PROCESSOR")
    print("=" * 70)
    
    # Test 1: Pojedynczy tweet
    test_single_tweet_analysis()
    
    # Test 2: Porównanie metod ekstrakcji
    compare_extraction_methods()
    
    # Test 3: Różne prompty
    # test_llm_variations()
    
    print("\n✅ Diagnostyka zakończona!") 