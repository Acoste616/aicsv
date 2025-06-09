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
from multimodal_pipeline import MultimodalKnowledgePipeline
from tweet_content_analyzer import TweetContentAnalyzer
from config import PIPELINE_CONFIG, OUTPUT_CONFIG

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
        
        # Nowe komponenty multimodalne
        self.multimodal_pipeline = MultimodalKnowledgePipeline()
        self.tweet_analyzer = TweetContentAnalyzer()
        
        # Konfiguracja z config.py
        self.config = PIPELINE_CONFIG.copy()
        
        # Stan przetwarzania
        self.state = {
            "processed_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "duplicates_count": 0,
            "quality_fails": 0,
            "images_processed": 0,
            "threads_collected": 0,
            "videos_analyzed": 0,
            "multimodal_success": 0,
            "start_time": None,
            "checkpoints": [],
            "processed_urls": set(),
            "url_hashes": set(),
        }
        
        # Przygotuj folder outputu z config.py
        self.output_dir = Path(OUTPUT_CONFIG["output_dir"])
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
        
    # Usunięte: detect_duplicates - nie używane
        
    # Usunięte: validate_content_quality - nie używane
        
    def enhance_content_extraction(self, url: str, original_text: str) -> Dict:
        """
        Uproszczona ekstrakcja treści.
        """
        try:
            # Prosta ekstrakcja
            extracted_content = self.content_extractor.extract_with_retry(url)
            
            return {
                "content": extracted_content if extracted_content else original_text,
                "extracted_length": len(extracted_content) if extracted_content else 0,
                "url": url
            }
            
        except Exception as e:
            self.logger.error(f"Błąd ekstrakcji {url}: {e}")
            return {
                "content": original_text,  # Fallback na tweet
                "extracted_length": 0,
                "url": url
            }
            
    def process_single_entry(self, entry: Dict) -> Dict:
        """
        Przetwarza pojedynczy wpis z CSV używając MultimodalKnowledgePipeline.
        """
        # Mapowanie kolumn CSV
        url = entry.get('url', '')
        original_text = entry.get('tweet_text', '')
        
        result = {
            "url": url,
            "original_text": original_text,
            "processing_time": time.time(),
            "success": False,
            "multimodal_processing": False,
            "content_statistics": {},
            "llm_result": None,
            "errors": []
        }
        
        # Debug log
        self.logger.info(f"Processing: {url[:50]}... | Text: {original_text[:50]}...")
        
        try:
            # Przygotuj dane tweeta do przetwarzania multimodalnego
            tweet_data = {
                'url': url,
                'content': original_text,
                'rawContent': '',
                # Dodaj więcej pól jeśli dostępne w CSV
                'id': entry.get('id', ''),
                'author': entry.get('author', ''),
                'timestamp': entry.get('timestamp', ''),
                'media': entry.get('media', []) if entry.get('media') else []
            }
            
            # Użyj MultimodalKnowledgePipeline do kompletnego przetwarzania
            try:
                multimodal_result = self.multimodal_pipeline.process_tweet_complete(tweet_data)
                
                # Sprawdź czy przetwarzanie się udało
                processing_success = multimodal_result.get('processing_metadata', {}).get('processing_success', False)
                
                if processing_success and multimodal_result.get('tweet_url'):
                    # Sukces multimodalny
                    result["llm_result"] = multimodal_result
                    result["success"] = True
                    result["multimodal_processing"] = True
                    self.state["success_count"] += 1
                    self.state["multimodal_success"] += 1
                    
                    # Aktualizuj statystyki na podstawie przetworzonych treści
                    content_stats = multimodal_result.get('content_statistics', {})
                    extracted_from = multimodal_result.get('extracted_from', {})
                    
                    if content_stats.get('total_images', 0) > 0:
                        self.state["images_processed"] += content_stats['total_images']
                    
                    if content_stats.get('total_videos', 0) > 0:
                        self.state["videos_analyzed"] += content_stats['total_videos']
                    
                    if extracted_from.get('thread_length', 0) > 1:
                        self.state["threads_collected"] += 1
                    
                    result["content_statistics"] = content_stats
                    
                    self.logger.info(f"MULTIMODAL SUCCESS: {url[:50]}... - Title: {multimodal_result.get('title', 'N/A')[:30]}...")
                    
                else:
                    # Fallback na standardowe przetwarzanie
                    self.logger.warning(f"Multimodal processing failed for {url}, falling back to standard processing")
                    
                    content_data = self.enhance_content_extraction(url, original_text)
                    
                    llm_result = self.content_processor.process_single_item(
                        url=url,
                        tweet_text=original_text,
                        extracted_content=content_data["content"]
                    )
                    
                    if llm_result and isinstance(llm_result, dict) and "title" in llm_result:
                        result["llm_result"] = llm_result
                        result["success"] = True
                        self.state["success_count"] += 1
                        self.logger.info(f"FALLBACK SUCCESS: {url[:50]}... - Title: {llm_result.get('title', 'N/A')[:30]}...")
                    else:
                        result["errors"].append("Both multimodal and fallback processing failed")
                        
            except Exception as multimodal_error:
                result["errors"].append(f"Multimodal processing exception: {str(multimodal_error)}")
                self.logger.error(f"MULTIMODAL ERROR {url}: {multimodal_error}")
                
                # Fallback na standardowe przetwarzanie
                try:
                    content_data = self.enhance_content_extraction(url, original_text)
                    
                    llm_result = self.content_processor.process_single_item(
                        url=url,
                        tweet_text=original_text,
                        extracted_content=content_data["content"]
                    )
                    
                    if llm_result and isinstance(llm_result, dict) and "title" in llm_result:
                        result["llm_result"] = llm_result
                        result["success"] = True
                        self.state["success_count"] += 1
                        self.logger.info(f"FALLBACK SUCCESS: {url[:50]}...")
                    else:
                        result["errors"].append("Fallback processing also failed")
                        
                except Exception as fallback_error:
                    result["errors"].append(f"Fallback processing exception: {str(fallback_error)}")
                    self.logger.error(f"FALLBACK ERROR {url}: {fallback_error}")
                
        except Exception as e:
            result["errors"].append(f"Main processing exception: {str(e)}")
            self.logger.error(f"MAIN ERROR {url}: {e}")
            
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
        """Generuje raport postępu z nowymi statystykami multimodalnymi."""
        total = self.state["processed_count"]
        success_rate = (self.state["success_count"] / total * 100) if total > 0 else 0
        multimodal_rate = (self.state["multimodal_success"] / total * 100) if total > 0 else 0
        
        elapsed_time = time.time() - self.state["start_time"] if self.state["start_time"] else 0
        estimated_total = (elapsed_time / total * 98) if total > 0 else 0  # 98 wierszy w CSV
        remaining = estimated_total - elapsed_time
        
        return f"""
📊 MULTIMODAL PIPELINE - RAPORT POSTĘPU:
• Przetworzono: {total}/98 ({total/98*100:.1f}%)
• Sukces: {self.state['success_count']} ({success_rate:.1f}%)
• Multimodal sukces: {self.state['multimodal_success']} ({multimodal_rate:.1f}%)
• Błędy: {self.state['failed_count']}
• Duplikaty: {self.state['duplicates_count']}  
• Problemy jakości: {self.state['quality_fails']}

🎯 TREŚCI MULTIMODALNE:
• Obrazy przetworzone: {self.state['images_processed']}
• Nitki zebrane: {self.state['threads_collected']}
• Wideo przeanalizowane: {self.state['videos_analyzed']}

⏰ CZAS:
• Elapsed: {elapsed_time/60:.1f}min / ~{estimated_total/60:.1f}min total
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
        multimodal_rate = (self.state['multimodal_success'] / total_entries * 100) if total_entries > 0 else 0
        
        self.logger.info(f"""
🎉 MULTIMODAL PIPELINE - UKOŃCZONO!
📊 Czas total: {total_time/60:.1f} minut
✅ Sukces: {self.state['success_count']}/{total_entries} ({self.state['success_count']/total_entries*100:.1f}%)
🎯 Multimodal sukces: {self.state['multimodal_success']}/{total_entries} ({multimodal_rate:.1f}%)
❌ Błędy: {self.state['failed_count']}
🔄 Duplikaty: {self.state['duplicates_count']}
📉 Jakość fails: {self.state['quality_fails']}

📸 TREŚCI MULTIMODALNE:
• Obrazy przetworzone: {self.state['images_processed']}
• Nitki zebrane: {self.state['threads_collected']}
• Wideo przeanalizowane: {self.state['videos_analyzed']}

📁 Output: {final_output}
        """)
        
        return {
            "success": True,
            "total_processed": total_entries,
            "successful": self.state["success_count"],
            "multimodal_successful": self.state["multimodal_success"],
            "failed": self.state["failed_count"],
            "duplicates": self.state["duplicates_count"],
            "quality_fails": self.state["quality_fails"],
            "images_processed": self.state["images_processed"],
            "threads_collected": self.state["threads_collected"],
            "videos_analyzed": self.state["videos_analyzed"],
            "output_file": final_output,
            "processing_time": total_time
        }
        
    def generate_final_output(self, results: List[Dict]) -> str:
        """Generuje końcowy plik output z obsługą nowego formatu multimodalnego."""
        # Filtruj tylko udane rezultaty
        successful_results = []
        multimodal_results = []
        standard_results = []
        
        # Statystyki treści multimodalnych
        total_images = 0
        total_videos = 0
        total_articles = 0
        total_threads = 0
        content_type_stats = {"article": 0, "thread": 0, "multimedia": 0, "mixed": 0}
        
        for r in results:
            if r["success"] and r["llm_result"]:
                entry = {
                    "url": r["url"],
                    "original_text": r["original_text"],
                    "processing_timestamp": datetime.fromtimestamp(r["processing_time"]).isoformat(),
                    "multimodal_processing": r.get("multimodal_processing", False),
                    "content_statistics": r.get("content_statistics", {}),
                }
                
                # Dodaj dane z LLM (już w nowym formacie jeśli multimodal)
                llm_data = r["llm_result"].copy()
                entry.update(llm_data)
                
                successful_results.append(entry)
                
                # Kategoryzuj wyniki
                if r.get("multimodal_processing", False):
                    multimodal_results.append(entry)
                    
                    # Zbieraj statystyki
                    content_stats = r.get("content_statistics", {})
                    total_images += content_stats.get("total_images", 0)
                    total_videos += content_stats.get("total_videos", 0)
                    total_articles += content_stats.get("total_articles", 0)
                    total_threads += content_stats.get("total_threads", 0)
                    
                    # Statystyki typu treści
                    content_type = llm_data.get("content_type", "unknown")
                    if content_type in content_type_stats:
                        content_type_stats[content_type] += 1
                else:
                    standard_results.append(entry)
        
        output_file = self.output_dir / f"multimodal_knowledge_base_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        final_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "pipeline_version": "multimodal_v1.0",
                "total_entries": len(results),
                "successful_entries": len(successful_results),
                "multimodal_entries": len(multimodal_results),
                "standard_entries": len(standard_results),
                "processing_config": self.config,
                "statistics": {
                    "success_rate": len(successful_results) / len(results) if results else 0,
                    "multimodal_rate": len(multimodal_results) / len(results) if results else 0,
                    "duplicates_removed": self.state["duplicates_count"],
                    "quality_failures": self.state["quality_fails"],
                    "images_processed": self.state["images_processed"],
                    "threads_collected": self.state["threads_collected"],
                    "videos_analyzed": self.state["videos_analyzed"]
                },
                "content_analysis": {
                    "total_images_found": total_images,
                    "total_videos_found": total_videos,
                    "total_articles_found": total_articles,
                    "total_threads_found": total_threads,
                    "content_type_distribution": content_type_stats
                }
            },
            "entries": successful_results
        }
        
        # Zapisz główny plik
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
            
        # Zapisz oddzielne pliki dla różnych typów
        if multimodal_results:
            multimodal_file = self.output_dir / f"multimodal_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(multimodal_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": final_data["metadata"],
                    "entries": multimodal_results
                }, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Multimodal results saved to: {multimodal_file}")
        
        return str(output_file)


def main():
    """Główny punkt wejścia."""
    pipeline = FixedMasterPipeline()
    
    csv_file = "bookmarks_cleaned.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ Plik {csv_file} nie istnieje!")
        return
        
    print("🎯 MULTIMODAL PIPELINE - START")
    result = pipeline.process_csv(csv_file)
    
    if result["success"]:
        print(f"✅ SUKCES! Przetworzono {result['successful']}/{result['total_processed']} wpisów")
        print(f"🎯 Multimodal: {result['multimodal_successful']} wpisów")
        print(f"📸 Obrazy: {result['images_processed']}, Nitki: {result['threads_collected']}, Wideo: {result['videos_analyzed']}")
        print(f"📁 Wynik: {result['output_file']}")
    else:
        print("❌ BŁĄD podczas przetwarzania")


if __name__ == "__main__":
    main() 