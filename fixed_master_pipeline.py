#!/usr/bin/env python3
"""
PARALLEL PROCESSING PIPELINE
Zrefaktoryzowany system przetwarzania CSV z równoległym przetwarzaniem

KLUCZOWE ULEPSZENIA:
1. Równoległe przetwarzanie z ThreadPoolExecutor
2. Rate limiting dla różnych API (OpenAI: 3500 RPM, Anthropic: 1000 RPM, Google: 300 RPM)
3. Progress bar z tqdm
4. Batch processing 10-20 tweetów równolegle
5. Graceful error handling
6. Zachowanie EnhancedSmartQueue dla priorytetyzacji
"""

import json
import pandas as pd
import time
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from threading import Lock, Semaphore
from queue import PriorityQueue
import threading
from dataclasses import dataclass
from tqdm import tqdm
from collections import defaultdict

# Importy lokalnych komponentów
from csv_cleaner_and_prep import CSVCleanerAndPrep
from fixed_content_processor import FixedContentProcessor
from content_extractor import ContentExtractor
from multimodal_pipeline import MultimodalKnowledgePipeline
from tweet_content_analyzer import TweetContentAnalyzer
from enhanced_smart_queue import EnhancedSmartProcessingQueue, PrioritizedTweet
from config import PIPELINE_CONFIG, OUTPUT_CONFIG

# Rate limiting configuration
RATE_LIMITS = {
    "openai": {"rpm": 3500, "concurrent": 20},
    "anthropic": {"rpm": 1000, "concurrent": 10},
    "google": {"rpm": 300, "concurrent": 5},
    "local": {"rpm": 10000, "concurrent": 50}  # Local LLM ma wyższe limity
}

@dataclass
class ProcessingTask:
    """Zadanie przetwarzania z priorytetem"""
    priority: float
    entry: Dict
    future: Optional[Future] = None

    def __lt__(self, other):
        # Wyższy priorytet = niższa wartość (dla PriorityQueue)
        return self.priority > other.priority

class RateLimiter:
    """Rate limiter dla różnych API"""
    
    def __init__(self):
        self.locks = {}
        self.counters = defaultdict(int)
        self.reset_times = defaultdict(lambda: time.time())
        
        # Inicjalizacja semaforów dla każdego API
        for api, limits in RATE_LIMITS.items():
            self.locks[api] = Semaphore(limits["concurrent"])
    
    def wait_if_needed(self, api_type: str):
        """Czeka jeśli trzeba przestrzegać rate limit"""
        limits = RATE_LIMITS.get(api_type, RATE_LIMITS["local"])
        rpm = limits["rpm"]
        
        # Sprawdź czy minęła minuta od resetu
        current_time = time.time()
        if current_time - self.reset_times[api_type] >= 60:
            self.counters[api_type] = 0
            self.reset_times[api_type] = current_time
        
        # Jeśli przekroczono limit, czekaj
        if self.counters[api_type] >= rpm:
            sleep_time = 60 - (current_time - self.reset_times[api_type])
            if sleep_time > 0:
                time.sleep(sleep_time)
                self.counters[api_type] = 0
                self.reset_times[api_type] = time.time()
        
        self.counters[api_type] += 1
    
    def acquire(self, api_type: str):
        """Pobiera semafor dla API"""
        return self.locks.get(api_type, self.locks["local"]).acquire()
    
    def release(self, api_type: str):
        """Zwalnia semafor dla API"""
        self.locks.get(api_type, self.locks["local"]).release()

class ParallelMasterPipeline:
    """
    Pipeline z równoległym przetwarzaniem i zaawansowaną priorytetyzacją.
    """
    
    def __init__(self, batch_size: int = 15, max_workers: int = 10):
        self.setup_logging()
        
        # Parametry równoległego przetwarzania
        self.batch_size = batch_size
        self.max_workers = max_workers
        
        # Inicjalizacja komponentów
        self.csv_cleaner = CSVCleanerAndPrep()
        self.content_processor = FixedContentProcessor()
        self.content_extractor = ContentExtractor()
        self.multimodal_pipeline = MultimodalKnowledgePipeline()
        self.tweet_analyzer = TweetContentAnalyzer()
        
        # Enhanced Smart Queue dla priorytetyzacji
        self.smart_queue = EnhancedSmartProcessingQueue()
        
        # Rate limiting
        self.rate_limiter = RateLimiter()
        
        # Konfiguracja
        self.config = PIPELINE_CONFIG.copy()
        self.config["batch_size"] = self.batch_size
        
        # Stan przetwarzania (thread-safe)
        self.state_lock = Lock()
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
            "processing_times": [],
            "api_calls": defaultdict(int)
        }
        
        # Progress tracking
        self.progress_bar = None
        
        # Przygotuj folder outputu
        self.output_dir = Path(OUTPUT_CONFIG["output_dir"])
        self.output_dir.mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Konfiguracja logowania."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('parallel_pipeline.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def update_state(self, key: str, value: Any = 1, operation: str = "add"):
        """Thread-safe aktualizacja stanu"""
        with self.state_lock:
            if operation == "add":
                if isinstance(self.state[key], (int, float)):
                    self.state[key] += value
                elif isinstance(self.state[key], list):
                    self.state[key].append(value)
                elif isinstance(self.state[key], set):
                    self.state[key].add(value)
            elif operation == "set":
                self.state[key] = value
            elif operation == "increment":
                self.state[key] += 1
    
    def determine_api_type(self, url: str) -> str:
        """Określa typ API na podstawie URL lub konfiguracji"""
        # Tu możesz dodać logikę określania które API będzie używane
        # Na razie zakładamy lokalne LLM
        return "local"
        
    def process_single_entry_parallel(self, prioritized_tweet: PrioritizedTweet) -> Dict:
        """
        Przetwarza pojedynczy wpis z obsługą rate limiting.
        """
        entry = prioritized_tweet.original_data
        start_time = time.time()
        
        # Mapowanie kolumn CSV
        url = entry.get('url', '')
        original_text = entry.get('tweet_text', '')
        
        # Określ typ API
        api_type = self.determine_api_type(url)
        
        result = {
            "url": url,
            "original_text": original_text,
            "priority_score": prioritized_tweet.priority_score,
            "content_type": prioritized_tweet.content_type.value,
            "processing_time": 0,
            "success": False,
            "multimodal_processing": False,
            "content_statistics": {},
            "llm_result": None,
            "errors": [],
            "thread_id": threading.current_thread().name
        }
        
        try:
            # Rate limiting
            self.rate_limiter.wait_if_needed(api_type)
            
            # Acquire semaphore
            acquired = self.rate_limiter.acquire(api_type)
            if not acquired:
                result["errors"].append("Could not acquire rate limit semaphore")
                return result
            
            try:
                # Przygotuj dane tweeta
                tweet_data = {
                    'url': url,
                    'content': original_text,
                    'rawContent': '',
                    'id': entry.get('id', ''),
                    'author': entry.get('author', ''),
                    'timestamp': entry.get('timestamp', ''),
                    'media': entry.get('media', []) if entry.get('media') else []
                }
                
                # Multimodal processing
                try:
                    multimodal_result = self.multimodal_pipeline.process_tweet_complete(tweet_data)
                    
                    processing_success = multimodal_result.get('processing_metadata', {}).get('processing_success', False)
                    
                    if processing_success and multimodal_result.get('tweet_url'):
                        result["llm_result"] = multimodal_result
                        result["success"] = True
                        result["multimodal_processing"] = True
                        
                        # Aktualizuj statystyki
                        self.update_state("success_count")
                        self.update_state("multimodal_success")
                        self.update_state("api_calls", {api_type: 1}, "add")
                        
                        content_stats = multimodal_result.get('content_statistics', {})
                        if content_stats.get('total_images', 0) > 0:
                            self.update_state("images_processed", content_stats['total_images'])
                        if content_stats.get('total_videos', 0) > 0:
                            self.update_state("videos_analyzed", content_stats['total_videos'])
                        
                        result["content_statistics"] = content_stats
                    else:
                        # Fallback na standardowe przetwarzanie
                        content_data = self.enhance_content_extraction(url, original_text)
                        
                        llm_result = self.content_processor.process_single_item(
                            url=url,
                            tweet_text=original_text,
                            extracted_content=content_data["content"]
                        )
                        
                        if llm_result and isinstance(llm_result, dict) and "title" in llm_result:
                            result["llm_result"] = llm_result
                            result["success"] = True
                            self.update_state("success_count")
                        else:
                            result["errors"].append("Processing failed")
                            
                except Exception as e:
                    result["errors"].append(f"Processing error: {str(e)}")
                    self.logger.error(f"Error processing {url}: {e}")
                    
            finally:
                # Zawsze zwolnij semafor
                self.rate_limiter.release(api_type)
                
        except Exception as e:
            result["errors"].append(f"Critical error: {str(e)}")
            self.logger.error(f"Critical error for {url}: {e}")
        finally:
            result["processing_time"] = time.time() - start_time
            self.update_state("processing_times", result["processing_time"], "add")
            
            if not result["success"]:
                self.update_state("failed_count")
            
            # Aktualizuj progress bar
            if self.progress_bar:
                self.progress_bar.update(1)
        
        return result
        
    def enhance_content_extraction(self, url: str, original_text: str) -> Dict:
        """Uproszczona ekstrakcja treści."""
        try:
            extracted_content = self.content_extractor.extract_with_retry(url)
            
            return {
                "content": extracted_content if extracted_content else original_text,
                "extracted_length": len(extracted_content) if extracted_content else 0,
                "url": url
            }
        except Exception as e:
            self.logger.error(f"Błąd ekstrakcji {url}: {e}")
            return {
                "content": original_text,
                "extracted_length": 0,
                "url": url
            }
    
    def process_batch_parallel(self, entries: List[Dict]) -> List[Dict]:
        """
        Przetwarza batch wpisów równolegle z priorytetyzacją.
        """
        # Priorytetyzacja przez EnhancedSmartQueue
        prioritized_tweets = self.smart_queue.prioritize_tweets(entries)
        
        # Logowanie priorytetów
        self.logger.info(f"Batch priorytetyzacja:")
        for pt in prioritized_tweets[:3]:  # Top 3
            self.logger.info(f"  Score: {pt.priority_score:.1f}, Type: {pt.content_type.value}, URL: {pt.original_data['url'][:50]}...")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submituj zadania
            future_to_tweet = {}
            for prioritized_tweet in prioritized_tweets:
                future = executor.submit(self.process_single_entry_parallel, prioritized_tweet)
                future_to_tweet[future] = prioritized_tweet
            
            # Zbieraj wyniki
            for future in as_completed(future_to_tweet):
                try:
                    result = future.result(timeout=60)  # 60s timeout per task
                    results.append(result)
                    self.update_state("processed_count")
                except Exception as e:
                    # Graceful error handling
                    prioritized_tweet = future_to_tweet[future]
                    self.logger.error(f"Task failed for {prioritized_tweet.original_data['url']}: {e}")
                    
                    # Dodaj failed result
                    results.append({
                        "url": prioritized_tweet.original_data['url'],
                        "original_text": prioritized_tweet.original_data.get('tweet_text', ''),
                        "success": False,
                        "errors": [f"Task execution failed: {str(e)}"],
                        "processing_time": 0
                    })
                    self.update_state("failed_count")
                    self.update_state("processed_count")
                    
                    if self.progress_bar:
                        self.progress_bar.update(1)
        
        return results
    
    def save_checkpoint(self, results: List[Dict], checkpoint_id: int):
        """Zapisuje checkpoint z rezultatami."""
        checkpoint_file = self.output_dir / f"checkpoint_{checkpoint_id}.json"
        
        with self.state_lock:
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "timestamp": datetime.now().isoformat(),
                "state": {
                    k: list(v) if isinstance(v, set) else dict(v) if isinstance(v, defaultdict) else v
                    for k, v in self.state.items()
                },
                "results": results
            }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        self.update_state("checkpoints", checkpoint_id, "add")
        self.logger.info(f"CHECKPOINT {checkpoint_id} saved ({len(results)} results)")
    
    def generate_processing_stats(self) -> Dict:
        """Generuje statystyki przetwarzania"""
        with self.state_lock:
            total = self.state["processed_count"]
            if total == 0:
                return {}
            
            avg_time = sum(self.state["processing_times"]) / len(self.state["processing_times"]) if self.state["processing_times"] else 0
            
            return {
                "total_processed": total,
                "success_rate": self.state["success_count"] / total * 100,
                "multimodal_rate": self.state["multimodal_success"] / total * 100,
                "avg_processing_time": avg_time,
                "throughput_per_minute": total / ((time.time() - self.state["start_time"]) / 60) if self.state["start_time"] else 0,
                "api_calls_distribution": dict(self.state["api_calls"])
            }
    
    def process_csv(self, csv_file: str) -> Dict:
        """
        Główna metoda przetwarzająca cały CSV równolegle.
        """
        self.logger.info(f"🚀 PARALLEL PIPELINE - START: {csv_file}")
        self.state["start_time"] = time.time()
        
        # Wczytaj CSV
        self.logger.info("📋 Wczytywanie CSV...")
        df = pd.read_csv(csv_file)
        entries = df.to_dict('records')
        total_entries = len(entries)
        
        self.logger.info(f"Do przetworzenia: {total_entries} wpisów")
        self.logger.info(f"Batch size: {self.batch_size}, Max workers: {self.max_workers}")
        
        all_results = []
        
        # Inicjalizuj progress bar
        self.progress_bar = tqdm(
            total=total_entries,
            desc="Processing tweets",
            unit="tweet",
            ncols=100,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
        
        # Przetwarzanie w batchach
        for i in range(0, total_entries, self.batch_size):
            batch = entries[i:i + self.batch_size]
            
            # Przetwarzaj batch równolegle
            batch_results = self.process_batch_parallel(batch)
            all_results.extend(batch_results)
            
            # Checkpoint co określoną liczbę wpisów
            if len(all_results) % (self.config["checkpoint_frequency"] * 5) == 0:
                checkpoint_id = len(all_results) // (self.config["checkpoint_frequency"] * 5)
                self.save_checkpoint(all_results, checkpoint_id)
            
            # Wyświetl statystyki co kilka batchy
            if i > 0 and i % (self.batch_size * 3) == 0:
                stats = self.generate_processing_stats()
                self.progress_bar.set_postfix({
                    'Success': f"{stats['success_rate']:.1f}%",
                    'Multimodal': f"{stats['multimodal_rate']:.1f}%",
                    'Speed': f"{stats['throughput_per_minute']:.1f}/min"
                })
        
        # Zamknij progress bar
        self.progress_bar.close()
        
        # Końcowy checkpoint
        final_checkpoint = len(self.state["checkpoints"]) + 1
        self.save_checkpoint(all_results, final_checkpoint)
        
        # Generuj final output
        final_output = self.generate_final_output(all_results)
        
        # Statystyki końcowe
        total_time = time.time() - self.state["start_time"]
        stats = self.generate_processing_stats()
        
        self.logger.info(f"""
🎉 PARALLEL PIPELINE - UKOŃCZONO!
📊 Czas total: {total_time/60:.1f} minut
✅ Sukces: {self.state['success_count']}/{total_entries} ({stats['success_rate']:.1f}%)
🎯 Multimodal sukces: {self.state['multimodal_success']}/{total_entries} ({stats['multimodal_rate']:.1f}%)
⚡ Prędkość: {stats['throughput_per_minute']:.1f} tweets/min
🔧 Avg processing time: {stats['avg_processing_time']:.2f}s/tweet
❌ Błędy: {self.state['failed_count']}

📸 TREŚCI MULTIMODALNE:
• Obrazy przetworzone: {self.state['images_processed']}
• Nitki zebrane: {self.state['threads_collected']}
• Wideo przeanalizowane: {self.state['videos_analyzed']}

🔌 API CALLS:
{json.dumps(stats['api_calls_distribution'], indent=2)}

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
            "processing_time": total_time,
            "throughput_per_minute": stats['throughput_per_minute']
        }
    
    def generate_final_output(self, results: List[Dict]) -> str:
        """Generuje końcowy plik output."""
        successful_results = []
        
        # Statystyki
        processing_time_by_type = defaultdict(list)
        success_by_type = defaultdict(int)
        total_by_type = defaultdict(int)
        
        for r in results:
            if r["success"] and r["llm_result"]:
                entry = {
                    "url": r["url"],
                    "original_text": r["original_text"],
                    "priority_score": r.get("priority_score", 0),
                    "content_type": r.get("content_type", "unknown"),
                    "processing_timestamp": datetime.now().isoformat(),
                    "processing_time": r["processing_time"],
                    "multimodal_processing": r.get("multimodal_processing", False),
                    "content_statistics": r.get("content_statistics", {}),
                }
                
                # Dodaj dane z LLM
                llm_data = r["llm_result"].copy()
                entry.update(llm_data)
                
                successful_results.append(entry)
                
                # Zbieraj statystyki
                content_type = r.get("content_type", "unknown")
                processing_time_by_type[content_type].append(r["processing_time"])
                success_by_type[content_type] += 1
            
            total_by_type[r.get("content_type", "unknown")] += 1
        
        # Oblicz średnie czasy i success rates per typ
        type_stats = {}
        for content_type in total_by_type:
            type_stats[content_type] = {
                "total": total_by_type[content_type],
                "successful": success_by_type[content_type],
                "success_rate": success_by_type[content_type] / total_by_type[content_type] * 100 if total_by_type[content_type] > 0 else 0,
                "avg_processing_time": sum(processing_time_by_type[content_type]) / len(processing_time_by_type[content_type]) if processing_time_by_type[content_type] else 0
            }
        
        output_file = self.output_dir / f"parallel_knowledge_base_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        final_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "pipeline_version": "parallel_v2.0",
                "total_entries": len(results),
                "successful_entries": len(successful_results),
                "processing_config": {
                    "batch_size": self.batch_size,
                    "max_workers": self.max_workers,
                    "rate_limits": RATE_LIMITS
                },
                "performance_stats": self.generate_processing_stats(),
                "content_type_stats": type_stats
            },
            "entries": successful_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        return str(output_file)


def main():
    """Główny punkt wejścia."""
    # Parametry równoległego przetwarzania
    batch_size = 15  # 10-20 tweetów równolegle jak w wymaganiach
    max_workers = 10  # Liczba wątków
    
    pipeline = ParallelMasterPipeline(batch_size=batch_size, max_workers=max_workers)
    
    csv_file = "bookmarks_cleaned.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ Plik {csv_file} nie istnieje!")
        return
    
    print(f"🚀 PARALLEL PIPELINE - START")
    print(f"⚙️ Batch size: {batch_size}, Max workers: {max_workers}")
    
    result = pipeline.process_csv(csv_file)
    
    if result["success"]:
        print(f"\n✅ SUKCES! Przetworzono {result['successful']}/{result['total_processed']} wpisów")
        print(f"⚡ Prędkość: {result['throughput_per_minute']:.1f} tweets/min")
        print(f"🎯 Multimodal: {result['multimodal_successful']} wpisów")
        print(f"📸 Obrazy: {result['images_processed']}, Nitki: {result['threads_collected']}, Wideo: {result['videos_analyzed']}")
        print(f"📁 Wynik: {result['output_file']}")
    else:
        print("❌ BŁĄD podczas przetwarzania")


if __name__ == "__main__":
    main() 