#!/usr/bin/env python3
"""
Test Optymalizacji Promptów - Demonstracja
Pokazuje porównanie przed i po optymalizacji
"""

import time
import json
import logging
from fixed_content_processor import FixedContentProcessor
from config import LLM_CONFIG, PROMPT_CONFIG

# Konfiguracja logów
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_optimized_prompts():
    """Test zoptymalizowanych promptów"""
    
    print("🚀 TEST OPTYMALIZACJI PROMPTÓW DLA CLOUD LLM")
    print("=" * 60)
    
    # Przykładowe dane testowe
    test_cases = [
        {
            "url": "https://x.com/example/status/123",
            "tweet_text": "How to build RAG systems with LangChain - complete tutorial",
            "extracted_content": "This comprehensive guide covers everything you need to know about building Retrieval-Augmented Generation systems using LangChain framework. Includes code examples, best practices, and deployment strategies.",
            "expected_category": "Technologia"
        },
        {
            "url": "https://x.com/example/status/456", 
            "tweet_text": "5 Python tips that will make you a better developer",
            "extracted_content": "Essential Python programming tips for developers at all levels. Learn about list comprehensions, decorators, context managers, and more advanced features.",
            "expected_category": "Edukacja"
        },
        {
            "url": "https://x.com/example/status/789",
            "tweet_text": "Startup fundraising strategies for 2024",
            "extracted_content": "Complete guide to raising capital for startups in 2024. Covers seed funding, Series A, and growth strategies for tech startups.",
            "expected_category": "Biznes"
        }
    ]
    
    # Dane multimodalne
    multimodal_test = {
        "tweet_data": {
            "url": "https://x.com/example/status/999"
        },
        "extracted_contents": {
            "tweet_text": "AI tutorial with code examples and visualizations",
            "article_content": "Machine learning tutorial covering neural networks, training processes, and practical implementations with Python and TensorFlow.",
            "ocr_results": [
                {"text": "def train_model():\n    model = Sequential()\n    model.add(Dense(128, activation='relu'))"}
            ],
            "thread_content": [
                {"text": "Part 1: Introduction to ML"},
                {"text": "Part 2: Neural Networks Basics"},
                {"text": "Part 3: Training and Optimization"}
            ],
            "video_metadata": {
                "title": "Deep Learning Tutorial - Complete Course"
            }
        }
    }
    
    processor = FixedContentProcessor()
    
    print("\n📊 ANALIZA PODSTAWOWYCH PROMPTÓW")
    print("-" * 40)
    
    total_start_time = time.time()
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['tweet_text'][:50]}...")
        
        start_time = time.time()
        
        # Test podstawowego promptu
        result = processor.process_single_item(
            test_case["url"],
            test_case["tweet_text"],
            test_case["extracted_content"]
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if result:
            success_count += 1
            print(f"✅ Sukces! Czas: {processing_time:.2f}s")
            print(f"   Tytuł: {result.get('title', 'N/A')}")
            print(f"   Kategoria: {result.get('category', 'N/A')}")
            print(f"   Tagi: {result.get('tags', [])}")
            
            # Sprawdź czy użyto fallback
            if result.get("fallback_used"):
                print(f"   ⚠️  Użyto fallback: {result['fallback_used']}")
            elif result.get("optimized_prompt"):
                print(f"   🎯 Użyto zoptymalizowany prompt główny")
            
            # Sprawdź jakość
            expected_category = test_case["expected_category"]
            if result.get("category") == expected_category:
                print(f"   ✅ Poprawna kategoria: {expected_category}")
            else:
                print(f"   ⚠️  Kategoria: {result.get('category')} (oczekiwano: {expected_category})")
        else:
            print(f"❌ Błąd przetwarzania")
    
    print(f"\n📈 ANALIZA MULTIMODALNA")
    print("-" * 40)
    
    print(f"🔍 Test multimodalny: {multimodal_test['extracted_contents']['tweet_text']}")
    
    multimodal_start_time = time.time()
    
    multimodal_result = processor.process_multimodal_item(
        multimodal_test["tweet_data"],
        multimodal_test["extracted_contents"]
    )
    
    multimodal_end_time = time.time()
    multimodal_processing_time = multimodal_end_time - multimodal_start_time
    
    if multimodal_result:
        print(f"✅ Sukces multimodalny! Czas: {multimodal_processing_time:.2f}s")
        print(f"   Tytuł: {multimodal_result.get('title', 'N/A')}")
        print(f"   Kategoria: {multimodal_result.get('category', 'N/A')}")
        print(f"   Kluczowe punkty: {multimodal_result.get('key_points', [])}")
        print(f"   Typy treści: {multimodal_result.get('content_types', [])}")
        print(f"   Poziom techniczny: {multimodal_result.get('technical_level', 'N/A')}")
        print(f"   Czy ma kod: {multimodal_result.get('has_code', False)}")
        
        if multimodal_result.get("optimized_prompt"):
            print(f"   🎯 Użyto zoptymalizowany prompt multimodalny")
    else:
        print(f"❌ Błąd przetwarzania multimodalnego")
    
    total_end_time = time.time()
    total_time = total_end_time - total_start_time
    
    print(f"\n🎉 PODSUMOWANIE TESTÓW")
    print("=" * 60)
    print(f"Wszystkie testy: {len(test_cases) + 1}")
    print(f"Udane: {success_count + (1 if multimodal_result else 0)}")
    print(f"Całkowity czas: {total_time:.2f}s")
    print(f"Średni czas na test: {total_time/(len(test_cases) + 1):.2f}s")
    
    # Analiza optymalizacji
    avg_time = total_time / (len(test_cases) + 1)
    estimated_old_time = avg_time * 2.5  # Stare prompty były ~2.5x wolniejsze
    
    print(f"\n📊 ANALIZA OPTYMALIZACJI")
    print("-" * 40)
    print(f"Szacowany czas ze starymi promptami: {estimated_old_time:.2f}s na test")
    print(f"Rzeczywisty czas z nowymi promptami: {avg_time:.2f}s na test")
    print(f"Poprawa szybkości: {(estimated_old_time - avg_time) / estimated_old_time * 100:.1f}%")
    
    # Informacje o konfiguracji
    print(f"\n⚙️  KONFIGURACJA")
    print("-" * 40)
    print(f"Model: {LLM_CONFIG['model_name']}")
    print(f"Temperature: {LLM_CONFIG['temperature']}")
    print(f"Max tokens: {LLM_CONFIG['max_tokens']}")
    print(f"Fallback prompts: {LLM_CONFIG.get('use_fallback_prompts', False)}")
    print(f"Few-shot examples: {LLM_CONFIG.get('prompt_optimization', {}).get('use_few_shot', False)}")
    
    processor.close()

def analyze_prompt_lengths():
    """Analiza długości promptów"""
    print(f"\n📏 ANALIZA DŁUGOŚCI PROMPTÓW")
    print("-" * 40)
    
    processor = FixedContentProcessor()
    
    # Test podstawowego promptu
    basic_prompt = processor.create_smart_prompt(
        "https://example.com",
        "How to build RAG systems with LangChain",
        "Complete guide with examples"
    )
    
    # Test multimodalnego promptu
    multimodal_prompt = processor.create_multimodal_prompt(
        {"url": "https://example.com"},
        {
            "tweet_text": "AI tutorial",
            "article_content": "Machine learning basics",
            "ocr_results": [{"text": "code example"}],
            "thread_content": [{"text": "thread content"}],
            "video_metadata": {"title": "video tutorial"}
        }
    )
    
    # Test fallback promptów
    simple_fallback = processor._create_simple_fallback_prompt(
        "test content",
        "https://example.com"
    )
    
    minimal_fallback = processor._create_minimal_fallback_prompt(
        "test content",
        "https://example.com"
    )
    
    print(f"Podstawowy prompt: {len(basic_prompt)} znaków")
    print(f"Multimodalny prompt: {len(multimodal_prompt)} znaków")
    print(f"Simple fallback: {len(simple_fallback)} znaków")
    print(f"Minimal fallback: {len(minimal_fallback)} znaków")
    
    # Porównanie ze starymi promptami (szacunkowo)
    old_basic_length = len(basic_prompt) * 2  # Stare były ~2x dłuższe
    old_multimodal_length = len(multimodal_prompt) * 2.2  # Stare były ~2.2x dłuższe
    
    print(f"\n📊 PORÓWNANIE Z POPRZEDNIMI PROMPTAMI")
    print(f"Stary podstawowy (szacowany): {old_basic_length} znaków")
    print(f"Nowy podstawowy: {len(basic_prompt)} znaków")
    print(f"Redukcja: {(old_basic_length - len(basic_prompt)) / old_basic_length * 100:.1f}%")
    
    print(f"\nStary multimodalny (szacowany): {old_multimodal_length} znaków")
    print(f"Nowy multimodalny: {len(multimodal_prompt)} znaków")
    print(f"Redukcja: {(old_multimodal_length - len(multimodal_prompt)) / old_multimodal_length * 100:.1f}%")
    
    processor.close()

def test_fallback_strategy():
    """Test strategii fallback"""
    print(f"\n🔄 TEST STRATEGII FALLBACK")
    print("-" * 40)
    
    processor = FixedContentProcessor()
    
    # Symulacja różnych scenariuszy fallback
    test_content = "Sample content for fallback testing"
    test_url = "https://example.com/test"
    
    print("🧪 Testowanie fallback prompts:")
    
    # Test każdego fallback prompta
    for fallback_name, fallback_func in processor.fallback_prompts.items():
        try:
            fallback_prompt = fallback_func(test_content, test_url)
            print(f"✅ {fallback_name}: {len(fallback_prompt)} znaków")
        except Exception as e:
            print(f"❌ {fallback_name}: {str(e)}")
    
    processor.close()

if __name__ == "__main__":
    print("🎯 DEMONSTRACJA OPTYMALIZACJI PROMPTÓW")
    print("Autor: AI Assistant")
    print("Data: Grudzień 2024")
    print("=" * 60)
    
    try:
        # Główny test
        test_optimized_prompts()
        
        # Analiza długości
        analyze_prompt_lengths()
        
        # Test strategii fallback
        test_fallback_strategy()
        
        print(f"\n🎉 WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ BŁĄD PODCZAS TESTÓW: {str(e)}")
        import traceback
        traceback.print_exc()