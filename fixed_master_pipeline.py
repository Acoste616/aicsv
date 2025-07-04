#!/usr/bin/env python3
"""
PARALLEL PROCESSING MASTER PIPELINE
Zrefaktorowany system przetwarzania CSV z równoległym przetwarzaniem

NOWE FUNKCJE:
1. Parallel processing z ThreadPoolExecutor + asyncio
2. Rate limiting dla różnych API (OpenAI, Anthropic, Google)
3. Enhanced Smart Queue z priorytetami
4. Progress bar z tqdm
5. Graceful error handling
6. Batch size 10-20 tweetów równolegle

CEL: 10x szybsze przetwarzanie przy zachowaniu jakości
"""

import json
import pandas as pd
import time
import logging
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import queue
from dataclasses import dataclass
from enum import Enum
import threading
from tqdm import tqdm

# Importy lokalnych komponentów
from csv_cleaner_and_prep import CSVCleanerAndPrep
from fixed_content_processor import FixedContentProcessor
from content_extractor import ContentExtractor
from multimodal_pipeline import MultimodalKnowledgePipeline
from tweet_content_analyzer import TweetContentAnalyzer
from enhanced_smart_queue import EnhancedSmartProcessingQueue, PrioritizedTweet
from config import PIPELINE_CONFIG, OUTPUT_CONFIG


class APIProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"


@dataclass
class RateLimitConfig:
    """Konfiguracja rate limiting dla API"""
    requests_per_minute: int
    burst_limit: int
    cooldown_seconds: float


class RateLimiter:
    """Rate limiter z supportem dla różnych API"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_times = []
        self.lock = threading.Lock()
        
    def wait_if_needed(self):
        """Czeka jeśli przekroczono limity"""
        with self.lock:
            now = time.time()
            
            # Usuń stare requesty (starsze niż minuta)
            minute_ago = now - 60
            self.request_times = [t for t in self.request_times if t > minute_ago]
            
            # Sprawdź czy przekroczono limit
            if len(self.request_times) >= self.config.requests_per_minute:
                sleep_time = 60 - (now - self.request_times[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            # Sprawdź burst limit
            if len(self.request_times) >= self.config.burst_limit:
                time.sleep(self.config.cooldown_seconds)
            
            # Zapisz czas tego requestu
            self.request_times.append(now)


class EnhancedSmartQueue:
    """Enhanced Queue z priorytetami dla równoległego przetwarzania"""
    
    def __init__(self, max_size: int = 100):
        self.queue = queue.PriorityQueue(maxsize=max_size)
        self.processing_queue = EnhancedSmartProcessingQueue()
        self.completed_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()
        
    def add_tweets(self, tweets: List[Dict]):
        """Dodaje tweety do kolejki z priorytetami"""
        prioritized_tweets = self.processing_queue.prioritize_tweets(tweets)
        
        for i, tweet in enumerate(prioritized_tweets):
            # Używaj negatywnego score dla PriorityQueue (max heap)
            priority = -tweet.priority_score
            self.queue.put((priority, i, tweet))
    
    def get_next_batch(self, batch_size: int) -> List[PrioritizedTweet]:
        """Pobiera następny batch tweetów"""
        batch = []
        for _ in range(min(batch_size, self.queue.qsize())):
            try:
                _, _, tweet = self.queue.get_nowait()
                batch.append(tweet)
            except queue.Empty:
                break
        return batch
    
    def mark_completed(self, success: bool = True):
        """Oznacza tweet jako zakończony"""
        with self.lock:
            if success:
                self.completed_count += 1
            else:
                self.failed_count += 1
    
    def get_stats(self) -> Dict:
        """Zwraca statystyki kolejki"""
        with self.lock:
            return {
                'remaining': self.queue.qsize(),
                'completed': self.completed_count,
                'failed': self.failed_count,
                'total_processed': self.completed_count + self.failed_count
            }


class ParallelMasterPipeline:
    """
    Zrefaktorowany pipeline z równoległym przetwarzaniem
    """
    
    def __init__(self, max_workers: int = 15, batch_size: int = 15):
        self.setup_logging()
        self.max_workers = max_workers
        self.batch_size = batch_size
        
        # Inicjalizacja komponentów
        self.csv_cleaner = CSVCleanerAndPrep()
        self.content_processor = FixedContentProcessor()
        self.content_extractor = ContentExtractor()
        
        # Komponenty multimodalne
        self.multimodal_pipeline = MultimodalKnowledgePipeline()
        self.tweet_analyzer = TweetContentAnalyzer()
        
        # Enhanced Smart Queue
        self.smart_queue = EnhancedSmartQueue(max_size=200)
        
        # Rate limiters dla różnych API
        self.rate_limiters = {
            APIProvider.OPENAI: RateLimiter(RateLimitConfig(
                requests_per_minute=3500,
                burst_limit=10,
                cooldown_seconds=0.1
            )),
            APIProvider.ANTHROPIC: RateLimiter(RateLimitConfig(
                requests_per_minute=1000,
                burst_limit=5,
                cooldown_seconds=0.2
            )),
            APIProvider.GOOGLE: RateLimiter(RateLimitConfig(
                requests_per_minute=300,
                burst_limit=3,
                cooldown_seconds=0.5
            )),
            APIProvider.LOCAL: RateLimiter(RateLimitConfig(
                requests_per_minute=600,  # Conservative dla local models
                burst_limit=8,
                cooldown_seconds=0.05
            ))
        }
        
        # Konfiguracja z config.py
        self.config = PIPELINE_CONFIG.copy()
        self.config.update({
            'parallel_batch_size': batch_size,
            'max_workers': max_workers,
            'progress_update_interval': 2,
            'checkpoint_frequency': 25,
            'retry_failed_batches': True,
            'max_retries': 3
        })
        
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
            "parallel_batches_completed": 0,
            "rate_limit_delays": 0,
            "avg_processing_time": 0,
            "start_time": None,
            "checkpoints": [],
            "processed_urls": set(),
            "url_hashes": set(),
            "api_usage": defaultdict(int),
            "error_categories": defaultdict(int),
        }
        
        # Przygotuj folder outputu
        self.output_dir = Path(OUTPUT_CONFIG["output_dir"])
        self.output_dir.mkdir(exist_ok=True)
        
        # Thread pool executor
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
    def setup_logging(self):
        """Konfiguracja logowania z supportem dla parallel processing"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('parallel_pipeline.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def detect_api_provider(self, url: str, content: str) -> APIProvider:
        """Wykrywa który API użyć na podstawie URL i treści"""
        # Prosta heurystyka - można rozszerzyć
        if 'github.com' in url:
            return APIProvider.OPENAI  # GitHub content = OpenAI
        elif 'arxiv.org' in url or 'research' in url:
            return APIProvider.ANTHROPIC  # Research = Anthropic
        elif 'youtube.com' in url or 'video' in content.lower():
            return APIProvider.GOOGLE  # Video = Google
        else:
            return APIProvider.LOCAL  # Default = Local
    
    def apply_rate_limiting(self, api_provider: APIProvider):
        """Aplikuje rate limiting dla określonego API"""
        if api_provider in self.rate_limiters:
            self.rate_limiters[api_provider].wait_if_needed()
            self.state["api_usage"][api_provider.value] += 1
            
    def enhance_content_extraction(self, url: str, original_text: str) -> Dict:
        """Uproszczona ekstrakcja treści z rate limiting"""
        try:
            # Detect API provider
            api_provider = self.detect_api_provider(url, original_text)
            
            # Apply rate limiting
            self.apply_rate_limiting(api_provider)
            
            # Prosta ekstrakcja
            extracted_content = self.content_extractor.extract_with_retry(url)
            
            return {
                "content": extracted_content if extracted_content else original_text,
                "extracted_length": len(extracted_content) if extracted_content else 0,
                "url": url,
                "api_provider": api_provider.value
            }
            
        except Exception as e:
            self.logger.error(f"Błąd ekstrakcji {url}: {e}")
            self.state["error_categories"]["extraction_error"] += 1
            return {
                "content": original_text,
                "extracted_length": 0,
                "url": url,
                "api_provider": "unknown"
            }
    
    def process_single_entry_parallel(self, prioritized_tweet: PrioritizedTweet) -> Dict:
        """
        Przetwarza pojedynczy wpis w kontekście równoległym
        """
        entry = prioritized_tweet.original_data
        start_time = time.time()
        
        # Mapowanie kolumn CSV
        url = entry.get('url', '')
        original_text = entry.get('tweet_text', '')
        
        result = {
            "url": url,
            "original_text": original_text,
            "priority_score": prioritized_tweet.priority_score,
            "urgency_level": prioritized_tweet.urgency_level.name,
            "content_type": prioritized_tweet.content_type.name,
            "estimated_time": prioritized_tweet.estimated_processing_time,
            "actual_processing_time": 0,
            "processing_start": start_time,
            "success": False,
            "multimodal_processing": False,
            "content_statistics": {},
            "llm_result": None,
            "errors": [],
            "api_provider": "unknown",
            "thread_id": threading.current_thread().name
        }
        
        # Debug log z priority info
        self.logger.info(f"[{result['thread_id']}] Processing (P:{prioritized_tweet.priority_score}): {url[:50]}...")
        
        try:
            # Detect API provider
            api_provider = self.detect_api_provider(url, original_text)
            result["api_provider"] = api_provider.value
            
            # Apply rate limiting
            self.apply_rate_limiting(api_provider)
            
            # Przygotuj dane tweeta
            tweet_data = {
                'url': url,
                'content': original_text,
                'rawContent': '',
                'id': entry.get('id', ''),
                'author': entry.get('author', ''),
                'timestamp': entry.get('timestamp', ''),
                'media': entry.get('media', []) if entry.get('media') else [],
                'priority_score': prioritized_tweet.priority_score,
                'priority_reasons': prioritized_tweet.reasons
            }
            
            # Użyj MultimodalKnowledgePipeline
            try:
                multimodal_result = self.multimodal_pipeline.process_tweet_complete(tweet_data)
                
                processing_success = multimodal_result.get('processing_metadata', {}).get('processing_success', False)
                
                if processing_success and multimodal_result.get('tweet_url'):
                    # Sukces multimodalny
                    result["llm_result"] = multimodal_result
                    result["success"] = True
                    result["multimodal_processing"] = True
                    
                    # Aktualizuj statystyki
                    content_stats = multimodal_result.get('content_statistics', {})
                    result["content_statistics"] = content_stats
                    
                    self.logger.info(f"[{result['thread_id']}] MULTIMODAL SUCCESS: {url[:50]}... - Title: {multimodal_result.get('title', 'N/A')[:30]}...")
                    
                else:
                    # Fallback na standardowe przetwarzanie
                    self.logger.warning(f"[{result['thread_id']}] Multimodal failed, fallback: {url[:50]}...")
                    
                    content_data = self.enhance_content_extraction(url, original_text)
                    result["api_provider"] = content_data["api_provider"]
                    
                    llm_result = self.content_processor.process_single_item(
                        url=url,
                        tweet_text=original_text,
                        extracted_content=content_data["content"]
                    )
                    
                    if llm_result and isinstance(llm_result, dict) and "title" in llm_result:
                        result["llm_result"] = llm_result
                        result["success"] = True
                        self.logger.info(f"[{result['thread_id']}] FALLBACK SUCCESS: {url[:50]}...")
                    else:
                        result["errors"].append("Both multimodal and fallback processing failed")
                        
            except Exception as multimodal_error:
                result["errors"].append(f"Multimodal processing exception: {str(multimodal_error)}")
                self.logger.error(f"[{result['thread_id']}] MULTIMODAL ERROR {url}: {multimodal_error}")
                self.state["error_categories"]["multimodal_error"] += 1
                
                # Fallback na standardowe przetwarzanie
                try:
                    content_data = self.enhance_content_extraction(url, original_text)
                    result["api_provider"] = content_data["api_provider"]
                    
                    llm_result = self.content_processor.process_single_item(
                        url=url,
                        tweet_text=original_text,
                        extracted_content=content_data["content"]
                    )
                    
                    if llm_result and isinstance(llm_result, dict) and "title" in llm_result:
                        result["llm_result"] = llm_result
                        result["success"] = True
                        self.logger.info(f"[{result['thread_id']}] FALLBACK SUCCESS: {url[:50]}...")
                    else:
                        result["errors"].append("Fallback processing also failed")
                        
                except Exception as fallback_error:
                    result["errors"].append(f"Fallback processing exception: {str(fallback_error)}")
                    self.logger.error(f"[{result['thread_id']}] FALLBACK ERROR {url}: {fallback_error}")
                    self.state["error_categories"]["fallback_error"] += 1
                
        except Exception as e:
            result["errors"].append(f"Main processing exception: {str(e)}")
            self.logger.error(f"[{result['thread_id']}] MAIN ERROR {url}: {e}")
            self.state["error_categories"]["main_error"] += 1
            
        finally:
            result["actual_processing_time"] = time.time() - start_time
            
        return result
    
    def process_batch_parallel(self, batch: List[PrioritizedTweet]) -> List[Dict]:
        """
        Przetwarza batch tweetów równolegle
        """
        batch_start = time.time()
        self.logger.info(f"🚀 Processing batch of {len(batch)} tweets in parallel...")
        
        # Submit all tasks to executor
        future_to_tweet = {
            self.executor.submit(self.process_single_entry_parallel, tweet): tweet 
            for tweet in batch
        }
        
        results = []
        completed_count = 0
        
        # Collect results as they complete
        for future in as_completed(future_to_tweet):
            try:
                result = future.result()
                results.append(result)
                completed_count += 1
                
                # Update queue stats
                self.smart_queue.mark_completed(result["success"])
                
                # Update global stats
                with threading.Lock():
                    self.state["processed_count"] += 1
                    if result["success"]:
                        self.state["success_count"] += 1
                        if result["multimodal_processing"]:
                            self.state["multimodal_success"] += 1
                    else:
                        self.state["failed_count"] += 1
                        
            except Exception as e:
                tweet = future_to_tweet[future]
                self.logger.error(f"❌ Future failed for {tweet.original_data.get('url', '')}: {e}")
                self.state["failed_count"] += 1
                self.state["error_categories"]["future_error"] += 1
                
        batch_time = time.time() - batch_start
        self.state["parallel_batches_completed"] += 1
        
        # Update average processing time
        total_time = sum(r["actual_processing_time"] for r in results)
        self.state["avg_processing_time"] = total_time / len(results) if results else 0
        
        self.logger.info(f"✅ Batch completed in {batch_time:.2f}s, avg per tweet: {self.state['avg_processing_time']:.2f}s")
        
        return results
    
    def save_checkpoint(self, results: List[Dict], checkpoint_id: int):
        """Zapisuje checkpoint z rezultatami i enhanced stats"""
        checkpoint_file = self.output_dir / f"parallel_checkpoint_{checkpoint_id}.json"
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "state": self.state.copy(),
            "results": results,
            "parallel_stats": {
                "max_workers": self.max_workers,
                "batch_size": self.batch_size,
                "queue_stats": self.smart_queue.get_stats(),
                "rate_limiting_stats": {
                    provider.value: limiter.config.requests_per_minute 
                    for provider, limiter in self.rate_limiters.items()
                }
            }
        }
        
        # Convert sets to lists for JSON serialization
        checkpoint_data["state"]["url_hashes"] = list(self.state["url_hashes"])
        checkpoint_data["state"]["processed_urls"] = list(self.state["processed_urls"])
        checkpoint_data["state"]["api_usage"] = dict(self.state["api_usage"])
        checkpoint_data["state"]["error_categories"] = dict(self.state["error_categories"])
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
        self.state["checkpoints"].append(checkpoint_id)
        self.logger.info(f"💾 CHECKPOINT {checkpoint_id} saved ({len(results)} results)")
        
    def generate_progress_report(self) -> str:
        """Generuje raport postępu z parallel processing stats"""
        total = self.state["processed_count"]
        success_rate = (self.state["success_count"] / total * 100) if total > 0 else 0
        multimodal_rate = (self.state["multimodal_success"] / total * 100) if total > 0 else 0
        
        elapsed_time = time.time() - self.state["start_time"] if self.state["start_time"] else 0
        
        # Enhanced estimates based on parallel processing
        avg_time_per_tweet = self.state["avg_processing_time"] if self.state["avg_processing_time"] > 0 else 30
        parallel_efficiency = self.max_workers * 0.8  # 80% efficiency assumption
        estimated_remaining_time = (98 - total) * avg_time_per_tweet / parallel_efficiency
        
        queue_stats = self.smart_queue.get_stats()
        
        return f"""
🚀 PARALLEL PROCESSING PIPELINE - RAPORT POSTĘPU:
• Przetworzono: {total}/98 ({total/98*100:.1f}%) | Batch: {self.state['parallel_batches_completed']}
• Sukces: {self.state['success_count']} ({success_rate:.1f}%)
• Multimodal sukces: {self.state['multimodal_success']} ({multimodal_rate:.1f}%)
• Błędy: {self.state['failed_count']} | Rate limit delays: {self.state['rate_limit_delays']}

⚡ RÓWNOLEGŁE PRZETWARZANIE:
• Workers: {self.max_workers} | Batch size: {self.batch_size}
• Avg time per tweet: {avg_time_per_tweet:.2f}s
• Queue remaining: {queue_stats['remaining']} | Completed: {queue_stats['completed']}

🎯 TREŚCI MULTIMODALNE:
• Obrazy: {self.state['images_processed']} | Nitki: {self.state['threads_collected']}
• Wideo: {self.state['videos_analyzed']}

📊 API USAGE:
{chr(10).join(f"• {api}: {count} requests" for api, count in self.state['api_usage'].items())}

⏰ CZAS:
• Elapsed: {elapsed_time/60:.1f}min | Remaining: ~{estimated_remaining_time/60:.1f}min
• Projected total: ~{(elapsed_time + estimated_remaining_time)/60:.1f}min
        """
    
    def process_csv_parallel(self, csv_file: str) -> Dict:
        """
        Główna metoda przetwarzająca CSV równolegle
        """
        self.logger.info(f"🚀 PARALLEL PIPELINE - ROZPOCZYNAM: {csv_file}")
        self.state["start_time"] = time.time()
        
        # 1. Wczytaj CSV
        self.logger.info("📋 Wczytywanie CSV...")
        df = pd.read_csv(csv_file)
        
        # Debug - sprawdź kolumny
        self.logger.info(f"Kolumny CSV: {list(df.columns)}")
        
        # 2. Konwertuj do słowników
        entries = df.to_dict('records')
        total_entries = len(entries)
        
        self.logger.info(f"Do przetworzenia: {total_entries} wpisów")
        
        # 3. Dodaj wszystkie tweety do smart queue
        self.logger.info("🧠 Priorytetyzowanie tweetów...")
        self.smart_queue.add_tweets(entries)
        
        all_results = []
        
        # 4. Progress bar setup
        with tqdm(total=total_entries, desc="Processing tweets", unit="tweet") as pbar:
            
            # 5. Przetwarzanie w parallel batches
            while self.smart_queue.get_stats()['remaining'] > 0:
                # Pobierz następny batch
                batch = self.smart_queue.get_next_batch(self.batch_size)
                
                if not batch:
                    break
                
                # Przetwórz batch równolegle
                batch_results = self.process_batch_parallel(batch)
                all_results.extend(batch_results)
                
                # Update progress bar
                pbar.update(len(batch_results))
                
                # Update stats for progress bar
                successful_in_batch = sum(1 for r in batch_results if r["success"])
                pbar.set_postfix({
                    'Success': f'{self.state["success_count"]}/{total_entries}',
                    'Multimodal': f'{self.state["multimodal_success"]}',
                    'Avg Time': f'{self.state["avg_processing_time"]:.2f}s',
                    'Workers': self.max_workers
                })
                
                # Progress report
                if self.state["processed_count"] % (self.config["progress_update_interval"] * self.batch_size) == 0:
                    self.logger.info(self.generate_progress_report())
                    
                # Checkpoint
                if self.state["processed_count"] % self.config["checkpoint_frequency"] == 0:
                    checkpoint_id = self.state["processed_count"] // self.config["checkpoint_frequency"]
                    self.save_checkpoint(all_results, checkpoint_id)
                    
                # Small delay to prevent overwhelming
                time.sleep(0.1)
        
        # 6. Końcowy checkpoint
        final_checkpoint = len(self.state["checkpoints"]) + 1
        self.save_checkpoint(all_results, final_checkpoint)
        
        # 7. Generuj final output
        final_output = self.generate_final_output(all_results)
        
        # 8. Cleanup
        self.executor.shutdown(wait=True)
        
        # 9. Raport końcowy
        total_time = time.time() - self.state["start_time"]
        multimodal_rate = (self.state['multimodal_success'] / total_entries * 100) if total_entries > 0 else 0
        speedup = (total_entries * 30) / total_time  # Assuming 30s per tweet sequential
        
        final_stats = {
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
            "parallel_batches_completed": self.state["parallel_batches_completed"],
            "avg_processing_time": self.state["avg_processing_time"],
            "total_processing_time": total_time,
            "estimated_speedup": f"{speedup:.1f}x",
            "api_usage": dict(self.state["api_usage"]),
            "error_categories": dict(self.state["error_categories"]),
            "output_file": final_output,
            "max_workers": self.max_workers,
            "batch_size": self.batch_size
        }
        
        self.logger.info(f"""
🎉 PARALLEL PIPELINE - UKOŃCZONO!
📊 Czas total: {total_time/60:.1f} minut (estimated speedup: {speedup:.1f}x)
⚡ Parallel batches: {self.state['parallel_batches_completed']} | Avg time/tweet: {self.state['avg_processing_time']:.2f}s
✅ Sukces: {self.state['success_count']}/{total_entries} ({self.state['success_count']/total_entries*100:.1f}%)
🎯 Multimodal sukces: {self.state['multimodal_success']}/{total_entries} ({multimodal_rate:.1f}%)
❌ Błędy: {self.state['failed_count']} | Rate limit delays: {self.state['rate_limit_delays']}

🔧 KONFIGURACJA:
• Max workers: {self.max_workers} | Batch size: {self.batch_size}
• API calls: {sum(self.state['api_usage'].values())}

📊 API USAGE:
{chr(10).join(f"• {api}: {count} requests" for api, count in self.state['api_usage'].items())}

📸 TREŚCI MULTIMODALNE:
• Obrazy: {self.state['images_processed']} | Nitki: {self.state['threads_collected']}
• Wideo: {self.state['videos_analyzed']}

📁 Output: {final_output}
        """)
        
        return final_stats
    
    def generate_final_output(self, results: List[Dict]) -> str:
        """Generuje końcowy plik output z parallel processing stats"""
        # Filtruj tylko udane rezultaty
        successful_results = []
        multimodal_results = []
        standard_results = []
        
        # Enhanced stats
        total_images = 0
        total_videos = 0
        total_articles = 0
        total_threads = 0
        content_type_stats = {"article": 0, "thread": 0, "multimedia": 0, "mixed": 0}
        processing_time_stats = {"min": float('inf'), "max": 0, "avg": 0}
        priority_distribution = defaultdict(int)
        api_provider_stats = defaultdict(int)
        
        for r in results:
            if r["success"] and r["llm_result"]:
                entry = {
                    "url": r["url"],
                    "original_text": r["original_text"],
                    "priority_score": r["priority_score"],
                    "urgency_level": r["urgency_level"],
                    "content_type": r["content_type"],
                    "processing_timestamp": datetime.fromtimestamp(r["processing_start"]).isoformat(),
                    "actual_processing_time": r["actual_processing_time"],
                    "multimodal_processing": r.get("multimodal_processing", False),
                    "content_statistics": r.get("content_statistics", {}),
                    "api_provider": r["api_provider"],
                    "thread_id": r["thread_id"]
                }
                
                # Dodaj dane z LLM
                llm_data = r["llm_result"].copy()
                entry.update(llm_data)
                
                successful_results.append(entry)
                
                # Collect enhanced stats
                if r.get("multimodal_processing", False):
                    multimodal_results.append(entry)
                else:
                    standard_results.append(entry)
                
                # Processing time stats
                proc_time = r["actual_processing_time"]
                processing_time_stats["min"] = min(processing_time_stats["min"], proc_time)
                processing_time_stats["max"] = max(processing_time_stats["max"], proc_time)
                
                # Priority distribution
                priority_distribution[r["urgency_level"]] += 1
                
                # API provider stats
                api_provider_stats[r["api_provider"]] += 1
        
        # Calculate averages
        if successful_results:
            total_proc_time = sum(r["actual_processing_time"] for r in results if r["success"])
            processing_time_stats["avg"] = total_proc_time / len(successful_results)
        
        output_file = self.output_dir / f"parallel_knowledge_base_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        final_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "pipeline_version": "parallel_v1.0",
                "total_entries": len(results),
                "successful_entries": len(successful_results),
                "multimodal_entries": len(multimodal_results),
                "standard_entries": len(standard_results),
                "processing_config": self.config,
                "parallel_config": {
                    "max_workers": self.max_workers,
                    "batch_size": self.batch_size,
                    "total_batches": self.state["parallel_batches_completed"],
                    "avg_processing_time": self.state["avg_processing_time"],
                    "total_processing_time": time.time() - self.state["start_time"]
                },
                "statistics": {
                    "success_rate": len(successful_results) / len(results) if results else 0,
                    "multimodal_rate": len(multimodal_results) / len(results) if results else 0,
                    "duplicates_removed": self.state["duplicates_count"],
                    "quality_failures": self.state["quality_fails"],
                    "images_processed": self.state["images_processed"],
                    "threads_collected": self.state["threads_collected"],
                    "videos_analyzed": self.state["videos_analyzed"],
                    "rate_limit_delays": self.state["rate_limit_delays"],
                    "processing_time_stats": processing_time_stats,
                    "priority_distribution": dict(priority_distribution),
                    "api_provider_stats": dict(api_provider_stats)
                }
            },
            "entries": successful_results
        }
        
        # Zapisz główny plik
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📁 Final output saved to: {output_file}")
        return str(output_file)


def main():
    """Główny punkt wejścia dla parallel processing"""
    # Konfiguracja parallel processing
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '15'))
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '15'))
    
    pipeline = ParallelMasterPipeline(
        max_workers=MAX_WORKERS,
        batch_size=BATCH_SIZE
    )
    
    csv_file = "bookmarks_cleaned.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ Plik {csv_file} nie istnieje!")
        return
        
    print(f"🚀 PARALLEL PROCESSING PIPELINE - START (Workers: {MAX_WORKERS}, Batch: {BATCH_SIZE})")
    result = pipeline.process_csv_parallel(csv_file)
    
    if result["success"]:
        print(f"✅ SUKCES! Przetworzono {result['successful']}/{result['total_processed']} wpisów")
        print(f"🎯 Multimodal: {result['multimodal_successful']} wpisów")
        print(f"⚡ Speedup: {result['estimated_speedup']} | Avg time: {result['avg_processing_time']:.2f}s")
        print(f"📊 Parallel batches: {result['parallel_batches_completed']} | Workers: {result['max_workers']}")
        print(f"📁 Wynik: {result['output_file']}")
    else:
        print("❌ BŁĄD podczas przetwarzania")


if __name__ == "__main__":
    main() 