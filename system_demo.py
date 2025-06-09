# system_demo.py
"""
Demo ulepszonego systemu analizy treści
"""

import logging
import json
import time
from enhanced_content_strategy import EnhancedContentStrategy
from adaptive_prompts import AdaptivePromptGenerator
from smart_queue import SmartProcessingQueue

logging.basicConfig(level=logging.INFO)

def demo_enhanced_system():
    """Demonstracja nowego systemu"""
    
    print("🚀 Demo Enhanced Content Analysis System")
    print("=" * 50)
    
    # Inicjalizacja komponentów
    content_strategy = EnhancedContentStrategy()
    prompt_generator = AdaptivePromptGenerator()
    processing_queue = SmartProcessingQueue()
    
    # Przykładowe tweety
    sample_tweets = [
        {
            'url': 'https://github.com/microsoft/vscode',
            'text': 'Amazing code editor! #programming',
            'likes': 150
        },
        {
            'url': 'https://arxiv.org/abs/2023.12345', 
            'text': 'AI research paper 1/5 🧵',
            'likes': 89
        },
        {
            'url': 'https://nytimes.com/paywall-article',
            'text': 'Breaking tech news',
            'likes': 45
        }
    ]
    
    print(f"\n📝 Analizuję {len(sample_tweets)} tweetów...")
    
    results = []
    
    for i, tweet in enumerate(sample_tweets, 1):
        print(f"\n--- Tweet {i}: {tweet['url'][:40]}... ---")
        
        try:
            # 1. Dodaj do kolejki z priorytetem
            item_id = processing_queue.add_item(
                tweet['url'], 
                tweet['text'],
                tweet
            )
            
            # 2. Pobierz treść z Enhanced Strategy
            start_time = time.time()
            content_data = content_strategy.get_content(
                tweet['url'], 
                tweet['text']
            )
            process_time = time.time() - start_time
            
            print(f"  📊 Jakość: {content_data['quality']}")
            print(f"  📍 Źródło: {content_data['source']}")
            print(f"  🎯 Pewność: {content_data.get('confidence', 0):.2f}")
            print(f"  ⏱️ Czas: {process_time:.2f}s")
            
            # 3. Wygeneruj adaptacyjny prompt
            prompt = prompt_generator.generate_prompt(content_data)
            
            print(f"  🤖 Prompt: {len(prompt)} znaków")
            print(f"     Typ: {content_data['quality']} quality prompt")
            
            # 4. Symuluj analizę LLM
            analysis = {
                'title': f"Analiza {content_data['source']}",
                'quality_score': {'high': 8, 'medium': 6, 'low': 4}[content_data['quality']],
                'confidence': content_data.get('confidence', 0)
            }
            
            result = {
                'url': tweet['url'],
                'content_quality': content_data['quality'],
                'source': content_data['source'],
                'processing_time': process_time,
                'analysis': analysis
            }
            
            results.append(result)
            processing_queue.mark_completed(item_id, True)
            print("  ✅ Sukces!")
            
        except Exception as e:
            print(f"  ❌ Błąd: {e}")
            processing_queue.mark_completed(item_id, False, str(e))
    
    # Podsumowanie
    print("\n" + "=" * 50)
    print("📊 PODSUMOWANIE:")
    
    successful = len(results)
    total = len(sample_tweets)
    
    print(f"✅ Przetworzone: {successful}/{total}")
    print(f"⚡ Success rate: {successful/total:.1%}")
    
    if results:
        avg_time = sum(r['processing_time'] for r in results) / len(results)
        print(f"⏱️ Średni czas: {avg_time:.2f}s")
        
        # Rozkład jakości
        quality_dist = {}
        for r in results:
            q = r['content_quality']
            quality_dist[q] = quality_dist.get(q, 0) + 1
        
        print(f"🎯 Jakość treści: {quality_dist}")
        
        # Źródła
        sources = {}
        for r in results:
            s = r['source']
            sources[s] = sources.get(s, 0) + 1
        
        print(f"📍 Źródła: {sources}")
    
    # Status kolejki
    queue_status = processing_queue.get_status()
    print(f"📋 Kolejka: {queue_status}")
    
    print("\n💡 ZALETY NOWEGO SYSTEMU:")
    print("  • Inteligentna priorytetyzacja treści")
    print("  • Wielopoziomowa strategia pozyskiwania")
    print("  • Adaptacyjne prompty dla LLM")
    print("  • Lepsze radzenie sobie z niedostępnymi artykułami")
    print("  • Szczegółowa analiza błędów")
    
    return results

if __name__ == "__main__":
    demo_enhanced_system() 