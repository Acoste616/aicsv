#!/usr/bin/env python3
"""
Automatyczne uruchomienie analizy multimodalnej na pliku bookmarks1_cleaned.csv
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
    sys.exit(1)

def main():
    """Automatyczne uruchomienie analizy na bookmarks1_cleaned.csv"""
    print("🚀 AUTOMATYCZNA ANALIZA MULTIMODALNA")
    print("=" * 45)
    print("Plik: bookmarks1_cleaned.csv")
    print("Tryb: Wszystkie dostępne funkcje")
    print("=" * 45)
    
    start_time = time.time()
    
    try:
        # 1. Sprawdź biblioteki
        print("\n🔍 SPRAWDZANIE BIBLIOTEK...")
        checker = LibraryChecker()
        library_status = checker.check_all_libraries()
        
        total_available = sum(len(libs) for libs in library_status['available'].values())
        total_missing = sum(len(libs) for libs in library_status['missing'].values())
        total_libs = total_available + total_missing
        
        print(f"✅ Dostępne: {total_available}/{total_libs}")
        if total_missing > 0:
            print(f"⚠️ Brakujące: {total_missing}")
            
        # 2. Automatyczny wybór trybów
        print("\n🎯 KONFIGURACJA TRYBÓW...")
        mode_selector = ModeSelector(checker)
        selected_modes = mode_selector.get_quick_selection()
        
        active_modes = [mode for mode, active in selected_modes.items() if active]
        print(f"✅ Aktywne tryby: {', '.join(active_modes)}")
        
        # 3. Sprawdź plik
        if not os.path.exists('bookmarks_cleaned.csv'):
            print("❌ Plik bookmarks_cleaned.csv nie istnieje!")
            return
        
        # 4. Wczytaj dane CSV (tylko pierwsze 5 jako test)
        print("📊 Wczytywanie danych...")
        try:
            # ZMIANA: Użyj bookmarks_cleaned.csv zamiast bookmarks1_cleaned.csv
            df = pd.read_csv('bookmarks_cleaned.csv', encoding='utf-8')
            print(f"✅ Wczytano {len(df)} wpisów z CSV")
            
            # ZMIANA: Ogranicz do pierwszych 5 wpisów jako test
            df_test = df.head(5)  
            print(f"🧪 Test na pierwszych {len(df_test)} wpisach")
            
            data = df_test.to_dict('records')
            print(f"📋 Przygotowano {len(data)} rekordów do analizy")
        except Exception as e:
            print(f"❌ Błąd wczytywania CSV: {e}")
            return
        
        # 5. Inicjalizuj runner
        print("\n🔧 INICJALIZACJA SYSTEMU...")
        runner = MultimodalAnalysisRunner()
        runner.library_checker = checker
        runner.mode_selector = mode_selector
        
        # Inicjalizuj pipeline
        from multimodal_pipeline import MultimodalKnowledgePipeline
        runner.pipeline = MultimodalKnowledgePipeline()
        print("✅ Pipeline multimodalny gotowy")
        
        # 6. Uruchom analizę
        print(f"\n🚀 ROZPOCZĘCIE ANALIZY...")
        print(f"⚡ Przetwarzanie {len(data)} wpisów...")
        
        runner.results['start_time'] = datetime.now()
        
        # Przetwarzanie z progress tracking
        try:
            from tqdm import tqdm
            progress_bar = tqdm(data, desc="Analizowanie", unit="wpis")
        except ImportError:
            progress_bar = data
            print("📊 Progress: ", end="", flush=True)
        
        for i, item in enumerate(progress_bar):
            try:
                # Przygotuj dane tweeta
                tweet_data = runner._prepare_tweet_data(item)
                
                if tweet_data:
                    # Uruchom przetwarzanie multimodalne
                    result = runner.pipeline.process_tweet_complete(tweet_data)
                    
                    if result and not result.get('error'):
                        runner.results['success_count'] += 1
                        runner._update_content_type_stats(result)
                        
                        # Pokaż przykład wyniku dla pierwszego wpisu
                        if i == 0:
                            print(f"\n📝 PRZYKŁAD WYNIKU (wpis 1):")
                            print(f"  URL: {result.get('tweet_url', 'brak')}")
                            print(f"  Typ treści: {result.get('content_type', 'brak')}")
                            print(f"  Kategoria: {result.get('category', 'brak')}")
                            if result.get('extracted_from'):
                                extracted = result['extracted_from']
                                print(f"  Artykuły: {len(extracted.get('articles', []))}")
                                print(f"  Obrazy: {len(extracted.get('images', []))}")
                                print(f"  Wideo: {len(extracted.get('videos', []))}")
                                print(f"  Długość nitki: {extracted.get('thread_length', 0)}")
                    else:
                        runner.results['failure_count'] += 1
                        if result and result.get('error'):
                            print(f"\n⚠️ Błąd wpisu {i+1}: {result['error'][:50]}...")
                else:
                    runner.results['failure_count'] += 1
                
                runner.results['processed_count'] += 1
                
                # Progress bez tqdm
                if not hasattr(progress_bar, 'update'):
                    if i % 5 == 0:
                        print(f"{i+1}", end=" ", flush=True)
                
            except Exception as e:
                runner.results['failure_count'] += 1
                runner.results['errors'].append(f"Wpis {i}: {str(e)}")
                print(f"\n❌ Błąd wpisu {i+1}: {str(e)[:30]}...")
        
        if not hasattr(progress_bar, 'update'):
            print()  # Nowa linia
        
        runner.results['end_time'] = datetime.now()
        
        # 7. Generuj raport
        print(f"\n📊 RAPORT KOŃCOWY:")
        report = runner.generate_report()
        print(report)
        
        # 8. Zapisz raport
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"bookmarks_analysis_report_{timestamp}.txt"
        
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write("RAPORT ANALIZY MULTIMODALNEJ - BOOKMARKS_CLEANED.CSV\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Data analizy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Plik źródłowy: bookmarks_cleaned.csv\n")
                f.write(f"Analizowane wpisy: {len(df_test)} z {len(df)}\n\n")
                f.write(report)
                
                # Dodaj szczegółowe statystyki
                f.write(f"\n\nSZCZEGÓŁOWE STATYSTYKI:\n")
                f.write("=" * 30 + "\n")
                f.write(f"Aktywne tryby: {', '.join(active_modes)}\n")
                f.write(f"Dostępne biblioteki: {total_available}/{total_libs}\n")
                
                if runner.results['errors']:
                    f.write(f"\nBŁĘDY ({len(runner.results['errors'])}):\n")
                    for error in runner.results['errors'][:10]:
                        f.write(f"  • {error}\n")
            
            print(f"\n📄 Raport zapisany: {report_filename}")
        except Exception as e:
            print(f"⚠️ Nie udało się zapisać raportu: {e}")
        
        # Podsumowanie końcowe
        end_time = time.time()
        total_duration = end_time - start_time
        
        print(f"\n🎉 ANALIZA ZAKOŃCZONA!")
        print("=" * 25)
        print(f"⏱️ Całkowity czas: {total_duration:.1f}s")
        
        if runner.results['processed_count'] > 0:
            success_rate = (runner.results['success_count'] / runner.results['processed_count']) * 100
            print(f"📈 Wskaźnik sukcesu: {success_rate:.1f}%")
            print(f"⚡ Średni czas na wpis: {total_duration/runner.results['processed_count']:.2f}s")
        
        total_content = sum(runner.results['content_types'].values())
        print(f"📊 Wykryte treści multimodalne: {total_content}")
        
        print(f"\n💡 Aby przeanalizować więcej wpisów, zmień wartość 'limit' w skrypcie")
        print(f"💾 Pełny raport: {report_filename}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Analiza przerwana przez użytkownika")
    except Exception as e:
        print(f"\n❌ Błąd krytyczny: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 