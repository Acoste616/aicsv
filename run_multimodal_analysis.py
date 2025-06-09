#!/usr/bin/env python3
"""
Interaktywny skrypt do uruchamiania analizy multimodalnej
- Sprawdza dostępność bibliotek
- Pozwala wybrać tryby analizy
- Pokazuje progress bar
- Generuje raport statystyk
"""

import os
import sys
import subprocess
import importlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import time

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import dla progress bar
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Importy naszych modułów
try:
    from multimodal_pipeline import MultimodalKnowledgePipeline
    from tweet_content_analyzer import TweetContentAnalyzer
    from thread_collector import ThreadCollector
    from fixed_master_pipeline import FixedMasterPipeline
    from config import MULTIMODAL_CONFIG, OCR_CONFIG
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"❌ Błąd importu modułów: {e}")
    MODULES_AVAILABLE = False


class LibraryChecker:
    """Sprawdza dostępność wymaganych bibliotek"""
    
    REQUIRED_LIBRARIES = {
        'core': [
            ('requests', 'requests'),
            ('pandas', 'pandas'),
            ('beautifulsoup4', 'bs4'),
        ],
        'ocr': [
            ('pytesseract', 'pytesseract'),
            ('pillow', 'PIL'),
            ('easyocr', 'easyocr'),
            ('opencv-python', 'cv2'),
        ],
        'video': [
            ('yt-dlp', 'yt_dlp'),
        ],
        'progress': [
            ('tqdm', 'tqdm'),
        ]
    }
    
    def __init__(self):
        self.available = {}
        self.missing = {}
        
    def check_all_libraries(self) -> Dict[str, Dict]:
        """Sprawdza wszystkie biblioteki"""
        print("🔍 Sprawdzam dostępność bibliotek...")
        
        for category, libraries in self.REQUIRED_LIBRARIES.items():
            print(f"\n📚 Kategoria: {category.upper()}")
            
            self.available[category] = []
            self.missing[category] = []
            
            for pip_name, import_name in libraries:
                if self._check_library(import_name, pip_name):
                    self.available[category].append(pip_name)
                    print(f"  ✅ {pip_name}")
                else:
                    self.missing[category].append(pip_name)
                    print(f"  ❌ {pip_name}")
        
        return {
            'available': self.available,
            'missing': self.missing
        }
    
    def _check_library(self, import_name: str, pip_name: str) -> bool:
        """Sprawdza pojedynczą bibliotekę"""
        try:
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False
    
    def get_installation_commands(self) -> List[str]:
        """Generuje komendy instalacji dla brakujących bibliotek"""
        commands = []
        
        all_missing = []
        for category, libraries in self.missing.items():
            all_missing.extend(libraries)
        
        if all_missing:
            # Grupuj w logiczne komendy
            core_libs = [lib for lib in all_missing if lib in ['requests', 'pandas', 'beautifulsoup4', 'tqdm']]
            ocr_libs = [lib for lib in all_missing if lib in ['pytesseract', 'pillow', 'easyocr', 'opencv-python']]
            video_libs = [lib for lib in all_missing if lib in ['yt-dlp']]
            
            if core_libs:
                commands.append(f"pip install {' '.join(core_libs)}")
            if ocr_libs:
                commands.append(f"pip install {' '.join(ocr_libs)}")
            if video_libs:
                commands.append(f"pip install {' '.join(video_libs)}")
        
        return commands
    
    def install_missing_libraries(self) -> bool:
        """Próbuje zainstalować brakujące biblioteki"""
        commands = self.get_installation_commands()
        
        if not commands:
            print("✅ Wszystkie biblioteki są dostępne!")
            return True
        
        print("\n📦 Instaluję brakujące biblioteki...")
        
        for command in commands:
            print(f"\n🔧 Wykonuję: {command}")
            try:
                result = subprocess.run(
                    command.split(), 
                    capture_output=True, 
                    text=True, 
                    timeout=300  # 5 minut timeout
                )
                
                if result.returncode == 0:
                    print("✅ Instalacja zakończona sukcesem")
                else:
                    print(f"❌ Błąd instalacji: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                print("❌ Timeout podczas instalacji")
                return False
            except Exception as e:
                print(f"❌ Błąd podczas instalacji: {e}")
                return False
        
        return True


class ModeSelector:
    """Pozwala wybrać tryby analizy"""
    
    ANALYSIS_MODES = {
        'articles': {
            'name': 'Artykuły z linków',
            'description': 'Pobiera i analizuje treść artykułów z linków w tweetach',
            'requires': ['core'],
            'default': True
        },
        'ocr': {
            'name': 'OCR z obrazów',
            'description': 'Wyciąga tekst z obrazów używając OCR',
            'requires': ['core', 'ocr'],
            'default': True
        },
        'threads': {
            'name': 'Analiza nitek',
            'description': 'Zbiera i analizuje nitki tweetów',
            'requires': ['core'],
            'default': True
        },
        'video': {
            'name': 'Metadane wideo',
            'description': 'Pobiera metadane z filmów (YouTube, itp.)',
            'requires': ['core', 'video'],
            'default': True
        }
    }
    
    def __init__(self, library_checker: LibraryChecker):
        self.checker = library_checker
        self.selected_modes = {}
        
    def get_available_modes(self) -> Dict[str, bool]:
        """Sprawdza które tryby są dostępne"""
        available_modes = {}
        
        for mode_id, mode_info in self.ANALYSIS_MODES.items():
            is_available = True
            
            # Sprawdź czy wszystkie wymagane kategorie bibliotek są dostępne
            for required_category in mode_info['requires']:
                if not self.checker.available.get(required_category):
                    is_available = False
                    break
            
            available_modes[mode_id] = is_available
        
        return available_modes
    
    def display_mode_selection(self) -> Dict[str, bool]:
        """Wyświetla interaktywny wybór trybów"""
        print("\n🎯 Wybierz tryby analizy:")
        print("=" * 50)
        
        available_modes = self.get_available_modes()
        
        for mode_id, mode_info in self.ANALYSIS_MODES.items():
            is_available = available_modes[mode_id]
            status = "✅ Dostępny" if is_available else "❌ Niedostępny"
            default = mode_info['default'] and is_available
            
            print(f"\n{mode_id.upper()}: {mode_info['name']}")
            print(f"  {mode_info['description']}")
            print(f"  Status: {status}")
            
            if is_available:
                while True:
                    choice = input(f"  Włączyć? [{'Y' if default else 'N'}/y/n]: ").strip().lower()
                    
                    if choice == '':
                        choice = 'y' if default else 'n'
                    
                    if choice in ['y', 'yes', 'tak']:
                        self.selected_modes[mode_id] = True
                        break
                    elif choice in ['n', 'no', 'nie']:
                        self.selected_modes[mode_id] = False
                        break
                    else:
                        print("  Proszę odpowiedzieć 'y' lub 'n'")
            else:
                self.selected_modes[mode_id] = False
        
        return self.selected_modes
    
    def get_quick_selection(self) -> Dict[str, bool]:
        """Szybki wybór - wszystkie dostępne tryby"""
        available_modes = self.get_available_modes()
        
        for mode_id, is_available in available_modes.items():
            self.selected_modes[mode_id] = is_available
        
        return self.selected_modes


class MultimodalAnalysisRunner:
    """Główna klasa do uruchamiania analizy"""
    
    def __init__(self):
        self.library_checker = LibraryChecker()
        self.mode_selector = None
        self.pipeline = None
        self.results = {
            'processed_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'content_types': {
                'articles': 0,
                'images': 0,
                'threads': 0,
                'videos': 0
            },
            'start_time': None,
            'end_time': None,
            'errors': []
        }
        
    def setup(self) -> bool:
        """Konfiguracja początkowa"""
        print("🚀 MULTIMODAL ANALYSIS RUNNER")
        print("=" * 40)
        
        # 1. Sprawdź moduły
        if not MODULES_AVAILABLE:
            print("❌ Nie można zaimportować wymaganych modułów")
            return False
        
        # 2. Sprawdź biblioteki
        library_status = self.library_checker.check_all_libraries()
        
        # 3. Zaproponuj instalację
        missing_commands = self.library_checker.get_installation_commands()
        if missing_commands:
            print("\n💡 Brakujące biblioteki można zainstalować:")
            for cmd in missing_commands:
                print(f"   {cmd}")
            
            choice = input("\nCzy zainstalować teraz? [y/N]: ").strip().lower()
            if choice in ['y', 'yes', 'tak']:
                if not self.library_checker.install_missing_libraries():
                    print("❌ Instalacja nie powiodła się")
                    return False
                
                # Ponownie sprawdź biblioteki
                self.library_checker.check_all_libraries()
        
        # 4. Wybór trybów
        self.mode_selector = ModeSelector(self.library_checker)
        
        print("\nWybierz tryb konfiguracji:")
        print("1. Interaktywny wybór trybów")
        print("2. Szybki start (wszystkie dostępne)")
        
        while True:
            choice = input("Wybór [1/2]: ").strip()
            if choice == '1':
                selected_modes = self.mode_selector.display_mode_selection()
                break
            elif choice == '2':
                selected_modes = self.mode_selector.get_quick_selection()
                break
            else:
                print("Proszę wybrać 1 lub 2")
        
        # 5. Podsumowanie
        print("\n📋 Podsumowanie konfiguracji:")
        active_modes = [mode for mode, active in selected_modes.items() if active]
        
        if not active_modes:
            print("❌ Nie wybrano żadnych trybów analizy")
            return False
        
        for mode in active_modes:
            mode_info = self.mode_selector.ANALYSIS_MODES[mode]
            print(f"  ✅ {mode_info['name']}")
        
        # 6. Inicjalizuj pipeline
        try:
            self.pipeline = MultimodalKnowledgePipeline()
            print("\n✅ Pipeline multimodalny zainicjalizowany")
        except Exception as e:
            print(f"❌ Błąd inicjalizacji pipeline: {e}")
            return False
        
        return True
    
    def load_data(self) -> List[Dict]:
        """Ładuje dane do przetworzenia"""
        print("\n📁 Ładowanie danych...")
        
        # Sprawdź dostępne pliki CSV
        csv_files = list(Path('.').glob('*.csv'))
        
        if not csv_files:
            print("❌ Nie znaleziono plików CSV w bieżącym katalogu")
            return []
        
        print("Dostępne pliki:")
        for i, file in enumerate(csv_files, 1):
            print(f"  {i}. {file.name}")
        
        # Wybór pliku
        while True:
            try:
                choice = input(f"Wybierz plik [1-{len(csv_files)}]: ").strip()
                if choice == '':
                    choice = '1'  # Default
                
                file_index = int(choice) - 1
                if 0 <= file_index < len(csv_files):
                    selected_file = csv_files[file_index]
                    break
                else:
                    print(f"Proszę wybrać numer od 1 do {len(csv_files)}")
            except ValueError:
                print("Proszę podać prawidłowy numer")
        
        # Załaduj dane
        try:
            import pandas as pd
            df = pd.read_csv(selected_file)
            
            print(f"✅ Załadowano {len(df)} wpisów z {selected_file}")
            
            # Konwertuj do listy słowników
            data = df.to_dict('records')
            
            # Limit dla testów
            limit = input(f"Ile wpisów przetworzyć? [domyślnie wszystkie {len(data)}]: ").strip()
            if limit:
                try:
                    limit = int(limit)
                    data = data[:limit]
                    print(f"📊 Ograniczono do {len(data)} wpisów")
                except ValueError:
                    print("Nieprawidłowy limit, przetwarzam wszystkie")
            
            return data
            
        except Exception as e:
            print(f"❌ Błąd ładowania pliku: {e}")
            return []
    
    def run_analysis(self, data: List[Dict]) -> bool:
        """Uruchamia analizę multimodalną z monitoringiem postępu"""
        if not data:
            print("❌ Brak danych do przetworzenia")
            return False
        
        print(f"\n🔬 Rozpoczynam analizę {len(data)} wpisów...")
        self.results['start_time'] = datetime.now()
        
        # Liczniki sukcesu vs fallbacków
        success_count = 0
        fallback_count = 0 
        processing_times = []
        
        # Progress bar
        if TQDM_AVAILABLE:
            pbar = tqdm(data, desc="Przetwarzanie", unit="tweet")
        else:
            pbar = data
            print("Progress: ", end="", flush=True)
        
        for i, item in enumerate(pbar):
            item_start_time = time.time()
            
            try:
                # Przekształć dane do formatu oczekiwanego przez pipeline
                tweet_data = self._prepare_tweet_data(item)
                
                if tweet_data:
                    # Uruchom przetwarzanie
                    result = self.pipeline.process_tweet_complete(tweet_data)
                    
                    if result and not result.get('error'):
                        # Sprawdź czy to była pełna analiza czy fallback
                        if result.get('fallback', False):
                            fallback_count += 1
                        else:
                            success_count += 1
                            
                        self.results['success_count'] += 1
                        self._update_content_type_stats(result)
                    else:
                        self.results['failure_count'] += 1
                        fallback_count += 1
                        if result and result.get('error'):
                            self.results['errors'].append(f"Item {i}: {result['error']}")
                else:
                    self.results['failure_count'] += 1
                    fallback_count += 1
                
                self.results['processed_count'] += 1
                
                # Zapisz czas przetwarzania
                item_time = time.time() - item_start_time
                processing_times.append(item_time)
                
                # Co 10 tweetów pokazuj statystyki
                processed = self.results['processed_count']
                if processed % 10 == 0 and processed > 0:
                    avg_time = sum(processing_times) / len(processing_times)
                    print(f"\n📊 Statystyki po {processed} tweetach:")
                    print(f"✅ Pełny sukces: {success_count} ({success_count/processed*100:.1f}%)")
                    print(f"⚠️ Fallback: {fallback_count} ({fallback_count/processed*100:.1f}%)")
                    print(f"❌ Błędy: {self.results['failure_count']} ({self.results['failure_count']/processed*100:.1f}%)")
                    print(f"⏱️ Śr. czas: {avg_time:.1f}s/tweet")
                    print(f"🔄 ETA: {(len(data) - processed) * avg_time / 60:.1f} min")
                
                # Progress bez tqdm
                if not TQDM_AVAILABLE:
                    if i % 10 == 0:
                        print(f"{i+1}", end=" ", flush=True)
                
            except Exception as e:
                self.results['failure_count'] += 1
                fallback_count += 1
                self.results['errors'].append(f"Item {i}: {str(e)}")
                
                # Zapisz czas nawet dla błędów
                item_time = time.time() - item_start_time
                processing_times.append(item_time)
                
                if not TQDM_AVAILABLE:
                    print("E", end="", flush=True)
        
        if not TQDM_AVAILABLE:
            print()  # Nowa linia
        
        self.results['end_time'] = datetime.now()
        
        print(f"\n✅ Analiza zakończona!")
        return True
    
    def _prepare_tweet_data(self, item: Dict) -> Optional[Dict]:
        """Przygotowuje dane tweeta do przetworzenia"""
        try:
            # Różne możliwe nazwy kolumn
            url_fields = ['url', 'link', 'tweet_url', 'full_text', 'content']
            content_fields = ['content', 'text', 'full_text', 'rawContent']
            
            url = None
            content = None
            
            # Znajdź URL
            for field in url_fields:
                if field in item and item[field]:
                    url = str(item[field])
                    if 'http' in url:
                        break
            
            # Znajdź treść
            for field in content_fields:
                if field in item and item[field]:
                    content = str(item[field])
                    break
            
            if not url and not content:
                return None
            
            return {
                'url': url or 'unknown',
                'content': content or '',
                'rawContent': content or '',
                'id': item.get('id', f"item_{hash(str(item))}")
            }
            
        except Exception as e:
            print(f"Błąd przygotowania danych: {e}")
            return None
    
    def _update_content_type_stats(self, result: Dict):
        """Aktualizuje statystyki typów treści"""
        try:
            # Sprawdź extracted_from
            extracted_from = result.get('extracted_from', {})
            
            if extracted_from.get('articles'):
                self.results['content_types']['articles'] += len(extracted_from['articles'])
            
            if extracted_from.get('images'):
                self.results['content_types']['images'] += len(extracted_from['images'])
            
            if extracted_from.get('videos'):
                self.results['content_types']['videos'] += len(extracted_from['videos'])
            
            if extracted_from.get('thread_length', 0) > 0:
                self.results['content_types']['threads'] += 1
                
        except Exception as e:
            pass  # Ignoruj błędy statystyk
    
    def generate_report(self) -> str:
        """Generuje raport z wynikami"""
        if not self.results['start_time']:
            return "❌ Brak danych do raportu"
        
        duration = self.results['end_time'] - self.results['start_time']
        duration_seconds = duration.total_seconds()
        
        report = []
        report.append("📊 RAPORT ANALIZY MULTIMODALNEJ")
        report.append("=" * 50)
        
        # Statystyki ogólne
        report.append(f"\n⏱️  Czas wykonania: {duration_seconds:.1f}s")
        report.append(f"📝 Przetworzonych wpisów: {self.results['processed_count']}")
        report.append(f"✅ Sukces: {self.results['success_count']}")
        report.append(f"❌ Błędy: {self.results['failure_count']}")
        
        if self.results['processed_count'] > 0:
            success_rate = (self.results['success_count'] / self.results['processed_count']) * 100
            report.append(f"📈 Wskaźnik sukcesu: {success_rate:.1f}%")
            
            if duration_seconds > 0:
                throughput = self.results['processed_count'] / duration_seconds
                report.append(f"⚡ Przepustowość: {throughput:.1f} wpisów/s")
        
        # Statystyki typów treści
        report.append(f"\n📋 TYPY TREŚCI:")
        content_stats = self.results['content_types']
        report.append(f"  📄 Artykuły: {content_stats['articles']}")
        report.append(f"  🖼️  Obrazy: {content_stats['images']}")
        report.append(f"  🎬 Wideo: {content_stats['videos']}")
        report.append(f"  🧵 Nitki: {content_stats['threads']}")
        
        total_content = sum(content_stats.values())
        report.append(f"  📊 Łącznie treści: {total_content}")
        
        # Błędy
        if self.results['errors']:
            report.append(f"\n❌ BŁĘDY ({len(self.results['errors'])}):")
            for error in self.results['errors'][:5]:  # Pokaż tylko pierwsze 5
                report.append(f"  • {error}")
            
            if len(self.results['errors']) > 5:
                report.append(f"  ... i {len(self.results['errors']) - 5} więcej")
        
        return "\n".join(report)
    
    def save_report(self, report: str) -> str:
        """Zapisuje raport do pliku"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"multimodal_analysis_report_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            return filename
        except Exception as e:
            print(f"❌ Błąd zapisu raportu: {e}")
            return ""


def main():
    """Główna funkcja skryptu"""
    runner = MultimodalAnalysisRunner()
    
    try:
        # 1. Setup
        if not runner.setup():
            print("❌ Setup nie powiódł się")
            return
        
        # 2. Ładowanie danych
        data = runner.load_data()
        if not data:
            print("❌ Nie udało się załadować danych")
            return
        
        # 3. Analiza
        if not runner.run_analysis(data):
            print("❌ Analiza nie powiodła się")
            return
        
        # 4. Raport
        report = runner.generate_report()
        print(f"\n{report}")
        
        # 5. Zapis raportu
        save_choice = input("\nZapisać raport do pliku? [Y/n]: ").strip().lower()
        if save_choice != 'n':
            filename = runner.save_report(report)
            if filename:
                print(f"📄 Raport zapisany: {filename}")
        
        print("\n🎉 Analiza zakończona pomyślnie!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Analiza przerwana przez użytkownika")
    except Exception as e:
        print(f"\n❌ Błąd krytyczny: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 