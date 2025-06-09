#!/usr/bin/env python3
"""
Demo skrypt pokazujący działanie systemu analizy multimodalnej
Automatycznie uruchamia analizę na przykładowych danych
"""

import sys
import os
import time
from datetime import datetime

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from run_multimodal_analysis import LibraryChecker, ModeSelector, MultimodalAnalysisRunner
    import pandas as pd
except ImportError as e:
    print(f"❌ Błąd importu: {e}")
    print("Uruchom: pip install pandas")
    sys.exit(1)

def demo_library_status():
    """Pokazuje status bibliotek"""
    print("🔍 SPRAWDZANIE BIBLIOTEK")
    print("=" * 30)
    
    checker = LibraryChecker()
    status = checker.check_all_libraries()
    
    print(f"\n📊 PODSUMOWANIE:")
    total_available = sum(len(libs) for libs in status['available'].values())
    total_missing = sum(len(libs) for libs in status['missing'].values())
    total_libs = total_available + total_missing
    
    print(f"  ✅ Dostępne: {total_available}/{total_libs}")
    print(f"  ❌ Brakujące: {total_missing}/{total_libs}")
    
    if total_missing > 0:
        commands = checker.get_installation_commands()
        print(f"\n💡 Do zainstalowania:")
        for cmd in commands:
            print(f"  {cmd}")
    
    return checker

def demo_mode_selection(checker):
    """Pokazuje dostępne tryby"""
    print("\n🎯 DOSTĘPNE TRYBY ANALIZY")
    print("=" * 30)
    
    selector = ModeSelector(checker)
    available_modes = selector.get_available_modes()
    
    for mode_id, mode_info in selector.ANALYSIS_MODES.items():
        is_available = available_modes[mode_id]
        status = "✅" if is_available else "❌"
        print(f"{status} {mode_info['name']}")
        print(f"   {mode_info['description']}")
    
    # Automatyczny wybór wszystkich dostępnych
    selected = selector.get_quick_selection()
    active_modes = [mode for mode, active in selected.items() if active]
    
    print(f"\n🚀 AKTYWNE TRYBY: {', '.join(active_modes)}")
    
    return selector, selected

def demo_sample_analysis():
    """Uruchamia analizę na przykładowych danych"""
    print("\n📊 ANALIZA PRZYKŁADOWYCH DANYCH")
    print("=" * 35)
    
    # Sprawdź czy plik istnieje
    if not os.path.exists('sample_tweets.csv'):
        print("❌ Plik sample_tweets.csv nie istnieje")
        return
    
    # Załaduj dane
    try:
        df = pd.read_csv('sample_tweets.csv')
        print(f"📁 Załadowano {len(df)} przykładowych tweetów")
        
        # Pokaż przykłady
        print("\n📝 PRZYKŁADOWE TWEETY:")
        for i, row in df.head(3).iterrows():
            content = row['content'][:60] + "..." if len(row['content']) > 60 else row['content']
            print(f"  {i+1}. {content}")
        
        if len(df) > 3:
            print(f"  ... i {len(df)-3} więcej")
        
    except Exception as e:
        print(f"❌ Błąd ładowania danych: {e}")
        return
    
    # Inicjalizuj runner
    try:
        runner = MultimodalAnalysisRunner()
        
        # Automatyczna konfiguracja
        checker = LibraryChecker()
        checker.check_all_libraries()
        
        runner.mode_selector = ModeSelector(checker)
        selected_modes = runner.mode_selector.get_quick_selection()
        
        # Inicjalizuj pipeline
        from multimodal_pipeline import MultimodalKnowledgePipeline
        runner.pipeline = MultimodalKnowledgePipeline()
        
        print("\n🚀 ROZPOCZĘCIE ANALIZY...")
        
        # Uruchom analizę na ograniczonych danych (pierwsze 5)
        data = df.head(5).to_dict('records')
        runner.results['start_time'] = datetime.now()
        
        print(f"⚡ Przetwarzanie {len(data)} tweetów...")
        
        for i, item in enumerate(data):
            print(f"  📝 Tweet {i+1}/{len(data)}: ", end="", flush=True)
            
            try:
                tweet_data = runner._prepare_tweet_data(item)
                
                if tweet_data:
                    result = runner.pipeline.process_tweet_complete(tweet_data)
                    
                    if result and not result.get('error'):
                        runner.results['success_count'] += 1
                        runner._update_content_type_stats(result)
                        print("✅")
                    else:
                        runner.results['failure_count'] += 1
                        print("⚠️")
                else:
                    runner.results['failure_count'] += 1
                    print("❌")
                
                runner.results['processed_count'] += 1
                
            except Exception as e:
                runner.results['failure_count'] += 1
                print(f"❌ ({str(e)[:30]}...)")
        
        runner.results['end_time'] = datetime.now()
        
        # Wygeneruj raport
        print("\n📊 WYNIKI ANALIZY:")
        report = runner.generate_report()
        print(report)
        
        return runner
        
    except Exception as e:
        print(f"❌ Błąd podczas analizy: {e}")
        import traceback
        traceback.print_exc()
        return None

def demo_advanced_features():
    """Pokazuje zaawansowane funkcje"""
    print("\n🔬 ZAAWANSOWANE FUNKCJE")
    print("=" * 25)
    
    try:
        from tweet_content_analyzer import TweetContentAnalyzer
        from thread_collector import ThreadCollector
        
        # Test analizatora tweetów
        analyzer = TweetContentAnalyzer()
        
        test_tweets = [
            {
                'content': '🧵 THREAD: AI tools 1/3',
                'rawContent': '🧵 THREAD: AI tools 1/3',
                'media': []
            },
            {
                'content': 'Amazing visualization pic.twitter.com/abc123',
                'rawContent': 'Amazing visualization pic.twitter.com/abc123',
                'media': [{'type': 'photo', 'fullUrl': 'test.jpg'}]
            },
            {
                'content': 'Check out this video: https://youtube.com/watch?v=test',
                'rawContent': 'Check out this video: https://youtube.com/watch?v=test',
                'media': []
            }
        ]
        
        print("🔍 ANALIZA TYPÓW TREŚCI:")
        for i, tweet in enumerate(test_tweets, 1):
            result = analyzer.analyze_tweet_type(tweet)
            print(f"\nTweet {i}: {tweet['content'][:40]}...")
            print(f"  🧵 Jest nitką: {result['is_thread']}")
            print(f"  🖼️  Ma obrazy: {result['has_images']}")
            print(f"  🎬 Ma wideo: {result['has_video']}")
            print(f"  🔗 Ma linki: {result['has_links']}")
        
        # Test kolektora nitek
        collector = ThreadCollector()
        
        # Przykładowa treść nitki
        thread_content = """
        1/3 Oto moja nitka o najlepszych narzędziach AI w 2024.
        
        2/3 Pierwsze narzędzie: ChatGPT - rewolucyjny asystent AI do kodowania i pisania.
        
        3/3 Drugie narzędzie: GitHub Copilot - AI pair programming na najwyższym poziomie.
        """
        
        knowledge = collector.extract_thread_knowledge(thread_content)
        
        print(f"\n🧵 ANALIZA NITKI:")
        print(f"  📚 Kluczowe tematy: {knowledge.get('key_topics', [])[:3]}")
        print(f"  🔧 Narzędzia: {knowledge.get('mentioned_tools', [])}")
        print(f"  📊 Dane: {knowledge.get('data_points', [])}")
        print(f"  📖 Czas czytania: {knowledge.get('reading_time_minutes', 0):.1f} min")
        print(f"  🎯 Poziom: {knowledge.get('technical_level', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Błąd funkcji zaawansowanych: {e}")

def main():
    """Główna funkcja demo"""
    print("🎭 DEMO SYSTEMU ANALIZY MULTIMODALNEJ")
    print("=" * 40)
    print("Ten skrypt pokazuje możliwości systemu")
    print("bez konieczności interakcji użytkownika\n")
    
    start_time = time.time()
    
    try:
        # 1. Status bibliotek
        checker = demo_library_status()
        
        # 2. Tryby analizy
        selector, selected_modes = demo_mode_selection(checker)
        
        # 3. Analiza przykładowych danych
        runner = demo_sample_analysis()
        
        # 4. Zaawansowane funkcje
        demo_advanced_features()
        
        # Podsumowanie
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n🎉 DEMO ZAKOŃCZONE")
        print("=" * 20)
        print(f"⏱️  Czas wykonania: {duration:.1f}s")
        
        if runner:
            success_rate = (runner.results['success_count'] / max(1, runner.results['processed_count'])) * 100
            print(f"📈 Wskaźnik sukcesu: {success_rate:.1f}%")
            print(f"📊 Przetworzone typy treści: {sum(runner.results['content_types'].values())}")
        
        print("\n💡 Aby uruchomić pełną analizę:")
        print("   py run_multimodal_analysis.py")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo przerwane przez użytkownika")
    except Exception as e:
        print(f"\n❌ Błąd demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 