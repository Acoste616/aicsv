#!/usr/bin/env python3
"""
MASTER PROCESSING PIPELINE
Kompletny system przetwarzania CSV z zakładkami do wysokiej jakości bazy danych

ARCHITEKTURA:
1. CSV Cleaning & Prep
2. Enhanced Content Extraction (bez API - tylko web scraping) 
3. Duplicate Detection
4. Quality Validation
5. LLM Processing 
6. Progress Tracking & Checkpoints
7. JSON Output
"""

import json
import pandas as pd
import time
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Importy lokalnych komponentów
from csv_cleaner_and_prep import CSVCleanerAndPrep
from enhanced_content_processor import EnhancedContentProcessor
from content_extractor import ContentExtractor

class MasterProcessingPipeline:
    """
    Główny pipeline przetwarzający CSV z inteligentnym podejściem do jakości danych.
    """
    
    def __init__(self):
        self.setup_logging()
        
        # Inicjalizacja komponentów
        self.csv_cleaner = CSVCleanerAndPrep()
        self.content_processor = EnhancedContentProcessor()
        self.content_extractor = ContentExtractor()
        
        # Konfiguracja
        self.config = {
            "batch_size": 10,           # Ile równolegle
            "checkpoint_frequency": 20,  # Co ile zapisywać checkpoint
            "max_retries": 3,           # Maksimum prób dla failed URLs
            "quality_threshold": 0.7,   # Próg jakości (0-1)
            "enable_duplicates_check": True,
            "enable_quality_validation": True,
            "output_format": "json",
            "progress_tracking": True,
        }
        
        # Stan przetwarzania
        self.state = {
            "processed_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "duplicates_count": 0,
            "quality_fails": 0,
            "start_time": None,
            "checkpoints": [],
            "processed_urls": set(),
            "url_hashes": set(),  # Dla duplikatów
        }
        
        # Przygotuj folder outputu
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Konfiguracja logowania."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('master_pipeline.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def detect_duplicates(self, url: str, title: str) -> bool:
        """
        Wykrywa duplikaty na podstawie URL i similarity tytułów.
        """
        if not self.config["enable_duplicates_check"]:
            return False
            
        # Prosty hash dla URL
        url_hash = hashlib.md5(url.lower().encode()).hexdigest()
        
        if url_hash in self.state["url_hashes"]:
            self.logger.info(f"DUPLIKAT URL wykryty: {url}")
            return True
            
        # TODO: Dodać similarity check dla tytułów (fuzzywuzzy)
        # Na razie tylko URL
        
        self.state["url_hashes"].add(url_hash)
        return False
        
    def validate_content_quality(self, content: str, url: str) -> Dict:
        """
        Waliduje jakość pobranej treści.
        """
        if not self.config["enable_quality_validation"]:
            return {"valid": True, "score": 1.0, "issues": []}
            
        issues = []
        score = 1.0
        
        # Test 1: Długość treści
        if len(content.strip()) < 50:
            issues.append("Treść za krótka (< 50 znaków)")
            score -= 0.3
            
        # Test 2: Czy to nie error page
        error_indicators = [
            "404", "not found", "error", "forbidden", 
            "access denied", "page not available"
        ]
        content_lower = content.lower()
        for indicator in error_indicators:
            if indicator in content_lower:
                issues.append(f"Prawdopodobna strona błędu: {indicator}")
                score -= 0.4
                break
                
        # Test 3: Czy treść zawiera przydatne informacje
        useful_indicators = [
            "tutorial", "guide", "how to", "tips", "learn",
            "development", "code", "programming", "AI", "machine learning"
        ]
        has_useful_content = any(indicator in content_lower for indicator in useful_indicators)
        if not has_useful_content and len(content.strip()) < 200:
            issues.append("Brak przydatnej treści")
            score -= 0.2
            
        # Test 4: Bardzo powtarzalna treść (spam/boilerplate)
        words = content.split()
        if len(set(words)) < len(words) * 0.3 and len(words) > 50:
            issues.append("Bardzo powtarzalna treść (możliwy spam)")
            score -= 0.3
            
        valid = score >= self.config["quality_threshold"]
        
        if not valid:
            self.logger.warning(f"JAKOŚĆ: {url} - Score: {score:.2f}, Issues: {issues}")
            
        return {
            "valid": valid,
            "score": max(0, score),
            "issues": issues
        }
        
    def enhance_content_extraction(self, url: str, original_text: str) -> Dict:
        """
        Ulepszona ekstrakcja treści z wieloma strategiami.
        """
        try:
            # Strategia 1: Standardowy content extractor
            extracted_content = self.content_extractor.extract_with_retry(url)
            
            # Strategia 2: Jeśli treść za słaba, spróbuj inne podejście
            quality = self.validate_content_quality(extracted_content, url)
            
            if not quality["valid"] and len(extracted_content.strip()) < 200:
                self.logger.info(f"Próba ulepszonej ekstrakcji dla: {url}")
                
                # Różne selektory dla różnych typów stron
                enhanced_content = self._try_enhanced_extraction(url)
                if enhanced_content and len(enhanced_content) > len(extracted_content):
                    extracted_content = enhanced_content
                    quality = self.validate_content_quality(extracted_content, url)
                    
            # Kombinuj oryginalna treść tweeta + extracted content
            combined_content = f"""
            ORYGINAŁ: {original_text}
            
            SZCZEGÓŁOWA TREŚĆ:
            {extracted_content}
            """
            
            return {
                "content": combined_content,
                "extracted_length": len(extracted_content),
                "quality": quality,
                "url": url
            }
            
        except Exception as e:
            self.logger.error(f"Błąd ekstrakcji {url}: {e}")
            return {
                "content": original_text,  # Fallback do oryginalnej treści
                "extracted_length": 0,
                "quality": {"valid": False, "score": 0, "issues": [str(e)]},
                "url": url
            }
            
    def _try_enhanced_extraction(self, url: str) -> Optional[str]:
        """
        Próby ulepszonej ekstrakcji dla różnych typów stron.
        """
        # TO-DO: Implement enhanced extraction strategies
        # - YouTube: meta descriptions, comments snippets
        # - Twitter: thread extraction via nitter.net
        # - Articles: better content selectors
        return None
        
    def process_single_entry(self, entry: Dict) -> Dict:
        """
        Przetwarza pojedynczy wpis z CSV.
        """
        url = entry.get('tweet_url', entry.get('url', ''))
        original_text = entry.get('full_text', entry.get('text', ''))
        
        result = {
            "url": url,
            "original_text": original_text,
            "processing_time": time.time(),
            "success": False,
            "duplicate": False,
            "quality_check": None,
            "llm_result": None,
            "errors": []
        }
        
        try:
            # 1. Check duplicates
            if self.detect_duplicates(url, original_text):
                result["duplicate"] = True
                self.state["duplicates_count"] += 1
                return result
                
            # 2. Enhanced content extraction
            content_data = self.enhance_content_extraction(url, original_text)
            result["quality_check"] = content_data["quality"]
            
            # 3. Quality validation
            if not content_data["quality"]["valid"]:
                result["errors"].append("Nie przeszło walidacji jakości")
                self.state["quality_fails"] += 1
                return result
                
            # 4. LLM Processing
            llm_result = self.content_processor.process_single_item(
                url=url,
                tweet_text=original_text
            )
            
            if llm_result and "error" not in llm_result:
                result["llm_result"] = llm_result
                result["success"] = True
                self.state["success_count"] += 1
                self.logger.info(f"SUCCESS: {url[:50]}...")
            else:
                result["errors"].append(f"LLM błąd: {llm_result.get('error', 'Nieznany')}")
                
        except Exception as e:
            result["errors"].append(f"Wyjątek: {str(e)}")
            self.logger.error(f"ERROR {url}: {e}")
            
        finally:
            result["processing_time"] = time.time() - result["processing_time"]
            if not result["success"]:
                self.state["failed_count"] += 1
                
        return result
        
    def save_checkpoint(self, results: List[Dict], checkpoint_id: int):
        """Zapisuje checkpoint z rezultatami."""
        checkpoint_file = self.output_dir / f"checkpoint_{checkpoint_id}.json"
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "state": self.state.copy(),
            "results": results
        }
        
        # Convert sets to lists for JSON serialization
        checkpoint_data["state"]["url_hashes"] = list(self.state["url_hashes"])
        checkpoint_data["state"]["processed_urls"] = list(self.state["processed_urls"])
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
        self.state["checkpoints"].append(checkpoint_id)
        self.logger.info(f"CHECKPOINT {checkpoint_id} saved ({len(results)} results)")
        
    def generate_progress_report(self) -> str:
        """Generuje raport postępu."""
        total = self.state["processed_count"]
        success_rate = (self.state["success_count"] / total * 100) if total > 0 else 0
        
        elapsed_time = time.time() - self.state["start_time"] if self.state["start_time"] else 0
        estimated_total = (elapsed_time / total * 907) if total > 0 else 0
        remaining = estimated_total - elapsed_time
        
        return f"""
📊 RAPORT POSTĘPU:
• Przetworzono: {total}/907 ({total/907*100:.1f}%)
• Sukces: {self.state['success_count']} ({success_rate:.1f}%)
• Błędy: {self.state['failed_count']}
• Duplikaty: {self.state['duplicates_count']}  
• Problemy jakości: {self.state['quality_fails']}
• Czas: {elapsed_time/60:.1f}min / ~{estimated_total/60:.1f}min total
• Pozostało: ~{remaining/60:.1f}min
        """
        
    def process_csv(self, csv_file: str) -> Dict:
        """
        Główna metoda przetwarzająca cały CSV.
        """
        self.logger.info(f"ROZPOCZYNAM PRZETWARZANIE: {csv_file}")
        self.state["start_time"] = time.time()
        
        # 1. Wczytaj i oczyść CSV
        self.logger.info("📋 Czyszczenie CSV...")
        df = pd.read_csv(csv_file)
        
        # 2. Konwertuj do słowników
        entries = df.to_dict('records')
        total_entries = len(entries)
        
        self.logger.info(f"Do przetworzenia: {total_entries} wpisów")
        
        all_results = []
        
        # 3. Przetwarzanie w batchach
        for i in range(0, total_entries, self.config["batch_size"]):
            batch = entries[i:i + self.config["batch_size"]]
            batch_results = []
            
            # Równoległe przetwarzanie batcha
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_entry = {
                    executor.submit(self.process_single_entry, entry): entry 
                    for entry in batch
                }
                
                for future in as_completed(future_to_entry):
                    result = future.result()
                    batch_results.append(result)
                    
                    self.state["processed_count"] += 1
                    
                    # Progress report
                    if self.state["processed_count"] % 10 == 0:
                        print(self.generate_progress_report())
                        
            all_results.extend(batch_results)
            
            # Checkpoint
            if self.state["processed_count"] % self.config["checkpoint_frequency"] == 0:
                checkpoint_id = self.state["processed_count"] // self.config["checkpoint_frequency"]
                self.save_checkpoint(all_results, checkpoint_id)
                
            # Rate limiting - żeby nie spam'ować
            time.sleep(1)
            
        # 4. Końcowy checkpoint
        final_checkpoint = len(self.state["checkpoints"]) + 1
        self.save_checkpoint(all_results, final_checkpoint)
        
        # 5. Generuj final output
        final_output = self.generate_final_output(all_results)
        
        # 6. Raport końcowy
        total_time = time.time() - self.state["start_time"]
        self.logger.info(f"""
🎉 UKOŃCZONO PRZETWARZANIE!
📊 Czas total: {total_time/60:.1f} minut
✅ Sukces: {self.state['success_count']}/{total_entries} ({self.state['success_count']/total_entries*100:.1f}%)
❌ Błędy: {self.state['failed_count']}
🔄 Duplikaty: {self.state['duplicates_count']}
📉 Jakość fails: {self.state['quality_fails']}
📁 Output: {final_output}
        """)
        
        return {
            "success": True,
            "total_processed": total_entries,
            "successful": self.state["success_count"],
            "failed": self.state["failed_count"],
            "duplicates": self.state["duplicates_count"],
            "quality_fails": self.state["quality_fails"],
            "output_file": final_output,
            "processing_time": total_time
        }
        
    def generate_final_output(self, results: List[Dict]) -> str:
        """Generuje końcowy plik output."""
        # Filtruj tylko udane rezultaty
        successful_results = [
            {
                "url": r["url"],
                "original_text": r["original_text"],
                "processing_timestamp": datetime.fromtimestamp(r["processing_time"]).isoformat(),
                **r["llm_result"]
            }
            for r in results 
            if r["success"] and r["llm_result"]
        ]
        
        output_file = self.output_dir / f"processed_knowledge_base_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        final_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_entries": len(results),
                "successful_entries": len(successful_results),
                "processing_config": self.config,
                "statistics": {
                    "success_rate": len(successful_results) / len(results) if results else 0,
                    "duplicates_removed": self.state["duplicates_count"],
                    "quality_failures": self.state["quality_fails"]
                }
            },
            "entries": successful_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Final output saved: {output_file}")
        return str(output_file)


def main():
    """Główna funkcja uruchamiająca pipeline."""
    pipeline = MasterProcessingPipeline()
    
    # Sprawdź które pliki CSV mamy dostępne
    csv_files = [
        "bookmarks_cleaned.csv",
        "bookmarks1_cleaned.csv"
    ]
    
    available_files = [f for f in csv_files if Path(f).exists()]
    
    if not available_files:
        print("❌ Brak oczyszczonych plików CSV! Uruchom najpierw csv_cleaner_and_prep.py")
        return
        
    print("📋 Dostępne pliki CSV:")
    for i, file in enumerate(available_files):
        size = Path(file).stat().st_size / 1024  # KB
        print(f"{i+1}. {file} ({size:.1f} KB)")
        
    # Dla testu używamy pierwszego dostępnego
    chosen_file = available_files[0]
    print(f"\n🎯 Przetwarzam: {chosen_file}")
    
    # Uruchom pipeline
    result = pipeline.process_csv(chosen_file)
    
    if result["success"]:
        print(f"\n🎉 GOTOWE! Sprawdź: {result['output_file']}")
    else:
        print(f"\n❌ BŁĄD w przetwarzaniu")


if __name__ == "__main__":
    main() 