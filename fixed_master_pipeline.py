#!/usr/bin/env python3
"""
FIXED MASTER PROCESSING PIPELINE
Kompletny system przetwarzania CSV z naprawionymi wszystkimi problemami

NAPRAWIONE PROBLEMY:
1. Mapowanie kolumn CSV: url/tweet_text zamiast tweet_url/full_text
2. LLM Response parsing - poprawiona obsługa None
3. Quality validation - mniej restrykcyjna 
4. Error handling - lepsza obsługa błędów
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
from fixed_content_processor import FixedContentProcessor
from content_extractor import ContentExtractor

class FixedMasterPipeline:
    """
    Naprawiony pipeline przetwarzający CSV z wszystkimi fixami.
    """
    
    def __init__(self):
        self.setup_logging()
        
        # Inicjalizacja komponentów
        self.csv_cleaner = CSVCleanerAndPrep()
        self.content_processor = FixedContentProcessor()
        self.content_extractor = ContentExtractor()
        
        # Konfiguracja
        self.config = {
            "batch_size": 5,            # Zmniejszone dla stabilności
            "checkpoint_frequency": 10,  # Częstsze checkpointy
            "max_retries": 2,           # Mniej prób
            "quality_threshold": 0.4,   # Niższy próg jakości
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
            "url_hashes": set(),
        }
        
        # Przygotuj folder outputu
        self.output_dir = Path("fixed_output")
        self.output_dir.mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Konfiguracja logowania."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('fixed_pipeline.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def detect_duplicates(self, url: str, title: str) -> bool:
        """
        Wykrywa duplikaty na podstawie URL.
        """
        if not self.config["enable_duplicates_check"]:
            return False
            
        # Prosty hash dla URL
        url_hash = hashlib.md5(url.lower().encode()).hexdigest()
        
        if url_hash in self.state["url_hashes"]:
            self.logger.info(f"DUPLIKAT URL wykryty: {url}")
            return True
            
        self.state["url_hashes"].add(url_hash)
        return False
        
    def validate_content_quality(self, content: str, url: str) -> Dict:
        """
        Łagodniejsza walidacja jakości pobranej treści.
        """
        if not self.config["enable_quality_validation"]:
            return {"valid": True, "score": 1.0, "issues": []}
            
        issues = []
        score = 1.0
        
        # Test 1: Długość treści - bardziej tolerancyjny
        if len(content.strip()) < 20:
            issues.append("Treść bardzo krótka (< 20 znaków)")
            score -= 0.4
        elif len(content.strip()) < 50:
            issues.append("Treść krótka (< 50 znaków)")
            score -= 0.2
            
        # Test 2: Czy to nie error page - ŁAGODNIEJSZY
        serious_error_indicators = [
            "404 not found", "page not found", "access denied", 
            "forbidden 403", "internal server error"
        ]
        content_lower = content.lower()
        for indicator in serious_error_indicators:
            if indicator in content_lower:
                issues.append(f"Prawdopodobna strona błędu: {indicator}")
                score -= 0.3
                break
                
        # USUWA - słowo "error" samo w sobie nie jest problemem
        
        # Test 3: Bardzo powtarzalna treść - łagodniejszy
        words = content.split()
        if len(set(words)) < len(words) * 0.2 and len(words) > 100:
            issues.append("Bardzo powtarzalna treść")
            score -= 0.2
            
        valid = score >= self.config["quality_threshold"]
        
        if not valid:
            self.logger.warning(f"JAKOŚĆ: {url} - Score: {score:.2f}, Issues: {issues}")
        else:
            self.logger.debug(f"JAKOŚĆ OK: {url} - Score: {score:.2f}")
            
        return {
            "valid": valid,
            "score": max(0, score),
            "issues": issues
        }
        
    def enhance_content_extraction(self, url: str, original_text: str) -> Dict:
        """
        Ulepszona ekstrakcja treści.
        """
        try:
            # Strategia 1: Standardowy content extractor
            extracted_content = self.content_extractor.extract_with_retry(url)
            
            # Strategia 2: Walidacja jakości
            quality = self.validate_content_quality(extracted_content, url)
            
            # Kombinuj oryginalna treść tweeta + extracted content
            combined_content = f"""
ORYGINAŁ TWEETA: {original_text}

SZCZEGÓŁOWA TREŚĆ ZE STRONY:
{extracted_content}
            """.strip()
            
            return {
                "content": combined_content,
                "extracted_length": len(extracted_content),
                "quality": quality,
                "url": url
            }
            
        except Exception as e:
            self.logger.error(f"Błąd ekstrakcji {url}: {e}")
            return {
                "content": f"ORYGINAŁ TWEETA: {original_text}",  # Fallback
                "extracted_length": 0,
                "quality": {"valid": True, "score": 0.5, "issues": ["Fallback na tweet"]},
                "url": url
            }
            
    def process_single_entry(self, entry: Dict) -> Dict:
        """
        Przetwarza pojedynczy wpis z CSV - NAPRAWIONE MAPOWANIE KOLUMN.
        """
        # NAPRAWKA: Poprawne mapowanie kolumn CSV
        url = entry.get('url', '')  # Kolumna 'url' zamiast 'tweet_url'
        original_text = entry.get('tweet_text', '')  # Kolumna 'tweet_text' zamiast 'full_text'
        
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
        
        # Debug log
        self.logger.info(f"Processing: {url[:50]}... | Text: {original_text[:50]}...")
        
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
                # NIE RETURN - spróbuj z LLM mimo to, może się uda
                self.logger.warning(f"Quality fail but continuing: {url}")
                
            # 4. LLM Processing - NAPRAWKA: Lepsze error handlinge
            try:
                llm_result = self.content_processor.process_single_item(
                    url=url,
                    tweet_text=original_text,
                    extracted_content=content_data["content"]
                )
                
                # NAPRAWKA: Sprawdź czy llm_result nie jest None
                if llm_result is None:
                    result["errors"].append("LLM zwróciło None")
                elif isinstance(llm_result, dict) and "error" in llm_result:
                    result["errors"].append(f"LLM błąd: {llm_result['error']}")
                elif isinstance(llm_result, dict):
                    result["llm_result"] = llm_result
                    result["success"] = True
                    self.state["success_count"] += 1
                    self.logger.info(f"SUCCESS: {url[:50]}...")
                else:
                    result["errors"].append(f"LLM zwróciło nieprawidłowy format: {type(llm_result)}")
                    
            except Exception as llm_error:
                result["errors"].append(f"LLM exception: {str(llm_error)}")
                self.logger.error(f"LLM ERROR {url}: {llm_error}")
                
        except Exception as e:
            result["errors"].append(f"Wyjątek główny: {str(e)}")
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
        estimated_total = (elapsed_time / total * 98) if total > 0 else 0  # 98 wierszy w CSV
        remaining = estimated_total - elapsed_time
        
        return f"""
📊 NAPRAWIONY PIPELINE - RAPORT POSTĘPU:
• Przetworzono: {total}/98 ({total/98*100:.1f}%)
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
        self.logger.info(f"🔧 NAPRAWIONY PIPELINE - ROZPOCZYNAM: {csv_file}")
        self.state["start_time"] = time.time()
        
        # 1. Wczytaj CSV
        self.logger.info("📋 Wczytywanie CSV...")
        df = pd.read_csv(csv_file)
        
        # Debug - sprawdź kolumny
        self.logger.info(f"Kolumny CSV: {list(df.columns)}")
        self.logger.info(f"Pierwszy wiersz URL: {df['url'].iloc[0] if 'url' in df.columns else 'BRAK'}")
        self.logger.info(f"Pierwszy wiersz tweet_text: {df['tweet_text'].iloc[0] if 'tweet_text' in df.columns else 'BRAK'}")
        
        # 2. Konwertuj do słowników
        entries = df.to_dict('records')
        total_entries = len(entries)
        
        self.logger.info(f"Do przetworzenia: {total_entries} wpisów")
        
        all_results = []
        
        # 3. Przetwarzanie w batchach - zmniejszone batch size
        for i in range(0, total_entries, self.config["batch_size"]):
            batch = entries[i:i + self.config["batch_size"]]
            batch_results = []
            
            # Przetwarzanie pojedyncze (nie równoległe na początku dla debugowania)
            for entry in batch:
                result = self.process_single_entry(entry)
                batch_results.append(result)
                
                self.state["processed_count"] += 1
                
                # Progress report
                if self.state["processed_count"] % 5 == 0:
                    print(self.generate_progress_report())
                    
            all_results.extend(batch_results)
            
            # Checkpoint częściej
            if self.state["processed_count"] % self.config["checkpoint_frequency"] == 0:
                checkpoint_id = self.state["processed_count"] // self.config["checkpoint_frequency"]
                self.save_checkpoint(all_results, checkpoint_id)
                
            # Rate limiting - mniej spam'u
            time.sleep(0.5)
            
        # 4. Końcowy checkpoint
        final_checkpoint = len(self.state["checkpoints"]) + 1
        self.save_checkpoint(all_results, final_checkpoint)
        
        # 5. Generuj final output
        final_output = self.generate_final_output(all_results)
        
        # 6. Raport końcowy
        total_time = time.time() - self.state["start_time"]
        self.logger.info(f"""
🎉 NAPRAWIONY PIPELINE - UKOŃCZONO!
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
        successful_results = []
        for r in results:
            if r["success"] and r["llm_result"]:
                entry = {
                    "url": r["url"],
                    "original_text": r["original_text"],
                    "processing_timestamp": datetime.fromtimestamp(r["processing_time"]).isoformat(),
                }
                # Dodaj dane z LLM
                entry.update(r["llm_result"])
                successful_results.append(entry)
        
        output_file = self.output_dir / f"fixed_knowledge_base_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
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
            
        return str(output_file)


def main():
    """Główny punkt wejścia."""
    pipeline = FixedMasterPipeline()
    
    csv_file = "bookmarks_cleaned.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ Plik {csv_file} nie istnieje!")
        return
        
    print("🔧 NAPRAWIONY PIPELINE - START")
    result = pipeline.process_csv(csv_file)
    
    if result["success"]:
        print(f"✅ SUKCES! Przetworzono {result['successful']}/{result['total_processed']} wpisów")
        print(f"📁 Wynik: {result['output_file']}")
    else:
        print("❌ BŁĄD podczas przetwarzania")


if __name__ == "__main__":
    main() 