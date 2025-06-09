#!/usr/bin/env python3
"""
Szybki test komponentów run_multimodal_analysis.py
"""

import sys
import os

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from run_multimodal_analysis import LibraryChecker, ModeSelector, MultimodalAnalysisRunner
    print("✅ Import komponentów udany")
except ImportError as e:
    print(f"❌ Błąd importu: {e}")
    sys.exit(1)

def test_library_checker():
    """Test sprawdzania bibliotek"""
    print("\n🔍 TEST: LibraryChecker")
    checker = LibraryChecker()
    
    # Sprawdź dostępność bibliotek
    status = checker.check_all_libraries()
    print(f"Dostępne kategorie: {list(status['available'].keys())}")
    print(f"Brakujące kategorie: {list(status['missing'].keys())}")
    
    # Sprawdź komendy instalacji
    commands = checker.get_installation_commands()
    if commands:
        print(f"Komendy instalacji: {commands}")
    else:
        print("Wszystkie biblioteki dostępne!")
    
    return checker

def test_mode_selector(checker):
    """Test wyboru trybów"""
    print("\n🎯 TEST: ModeSelector")
    selector = ModeSelector(checker)
    
    # Sprawdź dostępne tryby
    available_modes = selector.get_available_modes()
    print("Dostępne tryby:")
    for mode, available in available_modes.items():
        status = "✅" if available else "❌"
        mode_info = selector.ANALYSIS_MODES[mode]
        print(f"  {status} {mode}: {mode_info['name']}")
    
    # Test szybkiego wyboru
    selected = selector.get_quick_selection()
    active_modes = [mode for mode, active in selected.items() if active]
    print(f"Wybrane tryby: {active_modes}")
    
    return selector

def test_runner_setup():
    """Test setupu runnera"""
    print("\n🚀 TEST: MultimodalAnalysisRunner setup")
    runner = MultimodalAnalysisRunner()
    
    # Test sprawdzania dostępności bibliotek
    library_status = runner.library_checker.check_all_libraries()
    
    # Test mode selector
    runner.mode_selector = ModeSelector(runner.library_checker)
    selected_modes = runner.mode_selector.get_quick_selection()
    
    # Test inicjalizacji pipeline (jeśli moduły dostępne)
    try:
        from multimodal_pipeline import MultimodalKnowledgePipeline
        pipeline = MultimodalKnowledgePipeline()
        print("✅ Pipeline multimodalny zainicjalizowany")
    except Exception as e:
        print(f"❌ Błąd inicjalizacji pipeline: {e}")
    
    return runner

def test_data_preparation():
    """Test przygotowania danych"""
    print("\n📊 TEST: Przygotowanie danych")
    runner = MultimodalAnalysisRunner()
    
    # Test różnych formatów danych
    test_data = [
        {'url': 'https://twitter.com/user/status/123', 'content': 'Test tweet 1'},
        {'link': 'https://twitter.com/user/status/456', 'text': 'Test tweet 2'},
        {'full_text': 'Test tweet 3 https://example.com', 'id': '789'},
        {'invalid': 'data'}  # Nieprawidłowe dane
    ]
    
    prepared_count = 0
    for i, item in enumerate(test_data):
        prepared = runner._prepare_tweet_data(item)
        if prepared:
            prepared_count += 1
            print(f"  ✅ Item {i}: {prepared['url'][:50]}...")
        else:
            print(f"  ❌ Item {i}: Nie udało się przygotować")
    
    print(f"Przygotowano {prepared_count}/{len(test_data)} elementów")

def main():
    """Główna funkcja testowa"""
    print("🧪 TEST KOMPONENTÓW MULTIMODAL ANALYSIS RUNNER")
    print("=" * 50)
    
    try:
        # Test 1: LibraryChecker
        checker = test_library_checker()
        
        # Test 2: ModeSelector
        selector = test_mode_selector(checker)
        
        # Test 3: Runner setup
        runner = test_runner_setup()
        
        # Test 4: Data preparation
        test_data_preparation()
        
        print("\n✅ WSZYSTKIE TESTY ZAKOŃCZONE")
        print("📋 PODSUMOWANIE:")
        
        # Podsumowanie dostępności
        available_categories = []
        missing_categories = []
        
        for category, libs in checker.available.items():
            if libs:
                available_categories.append(category)
            else:
                missing_categories.append(category)
        
        print(f"  🟢 Dostępne: {available_categories}")
        print(f"  🔴 Brakujące: {missing_categories}")
        
        # Rekomendacje
        print("\n💡 REKOMENDACJE:")
        commands = checker.get_installation_commands()
        if commands:
            print("  Zainstaluj brakujące biblioteki:")
            for cmd in commands:
                print(f"    {cmd}")
        else:
            print("  ✅ Wszystkie biblioteki są dostępne!")
        
        print("\n🚀 Gotowy do uruchomienia pełnej analizy!")
        
    except Exception as e:
        print(f"\n❌ Błąd podczas testów: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 