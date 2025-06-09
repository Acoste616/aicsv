# smart_processing_system.py
"""
System inteligentnego przetwarzania z priorytetyzacją i zaawansowaną obsługą błędów
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from datetime import datetime

class ProcessingPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class ErrorCategory(Enum):
    PAYWALL = "paywall"
    FORBIDDEN = "forbidden"
    TIMEOUT = "timeout"
    REQUIRES_JS = "requires_js"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"

@dataclass
class ProcessingItem:
    """Element kolejki przetwarzania"""
    id: str
    url: str
    tweet_text: str
    tweet_data: Optional[Dict]
    priority: ProcessingPriority
    priority_score: float
    category: Optional[str]
    retry_count: int = 0
    last_error: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ProcessingResult:
    """Wynik przetwarzania"""
    item_id: str
    success: bool
    content_data: Optional[Dict]
    error: Optional[str]
    error_category: Optional[ErrorCategory]
    processing_time: float
    retry_count: int

class SmartProcessingQueue:
    """Inteligentna kolejka przetwarzania z priorytetyzacją"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.queue: List[ProcessingItem] = []
        self.processed_items: Dict[str, ProcessingResult] = {}
        self.error_stats: Dict[ErrorCategory, int] = {}
        self.domain_stats: Dict[str, Dict] = {}
        
        # Konfiguracja priorytetów
        self.priority_domains = [
            'github.com', 'gitlab.com', 'docs.', 'documentation.',
            'arxiv.org', 'scholar.google', 'research.',
            'stackoverflow.com', 'dev.to', 'medium.com'
        ]
        
        self.problematic_domains = [
            'nytimes.com', 'wsj.com', 'bloomberg.com', 'ft.com',
            'economist.com', 'reuters.com', 'washingtonpost.com'
        ]
        
        self.retry_limits = {
            ErrorCategory.TIMEOUT: 3,
            ErrorCategory.RATE_LIMITED: 2,
            ErrorCategory.REQUIRES_JS: 1,
            ErrorCategory.PAYWALL: 0,
            ErrorCategory.FORBIDDEN: 0,
            ErrorCategory.NOT_FOUND: 0
        }

    def add_item(self, url: str, tweet_text: str, tweet_data: Optional[Dict] = None) -> str:
        """Dodaje element do kolejki z automatyczną priorytetyzacją"""
        item_id = self._generate_item_id(url, tweet_text)
        
        # Sprawdź czy już przetwarzany
        if item_id in self.processed_items:
            self.logger.info(f"[Queue] Element {item_id} już przetworzony")
            return item_id
        
        # Oblicz priorytet
        priority, priority_score = self._calculate_priority(url, tweet_text, tweet_data)
        
        # Kategoryzuj treść
        category = self._categorize_content(url, tweet_text)
        
        item = ProcessingItem(
            id=item_id,
            url=url,
            tweet_text=tweet_text,
            tweet_data=tweet_data,
            priority=priority,
            priority_score=priority_score,
            category=category
        )
        
        self.queue.append(item)
        self._sort_queue()
        
        self.logger.info(f"[Queue] Dodano element: {item_id}, priorytet: {priority.name}, score: {priority_score:.2f}")
        return item_id

    def _calculate_priority(self, url: str, tweet_text: str, tweet_data: Optional[Dict]) -> Tuple[ProcessingPriority, float]:
        """Oblicza priorytet przetwarzania"""
        score = 0.0
        domain = urlparse(url).netloc.lower()
        
        # Bonus za wysokopriorytetowe domeny
        if any(prio_domain in domain for prio_domain in self.priority_domains):
            score += 10.0
            self.logger.debug(f"[Priority] Bonus za domenę: +10.0")
        
        # Kara za problematyczne domeny
        if any(prob_domain in domain for prob_domain in self.problematic_domains):
            score -= 5.0
            self.logger.debug(f"[Priority] Kara za problematyczną domenę: -5.0")
        
        # Bonus za thread
        if self._is_thread_tweet(tweet_text, url):
            score += 5.0
            self.logger.debug(f"[Priority] Bonus za thread: +5.0")
        
        # Bonus za długość tweeta
        text_length_bonus = min(len(tweet_text) / 50, 3.0)
        score += text_length_bonus
        self.logger.debug(f"[Priority] Bonus za długość: +{text_length_bonus:.1f}")
        
        # Bonus za engagement (jeśli dostępne)
        if tweet_data:
            likes = tweet_data.get('likes', 0)
            retweets = tweet_data.get('retweets', 0)
            engagement_score = (likes + retweets * 2) / 100
            engagement_bonus = min(engagement_score, 5.0)
            score += engagement_bonus
            self.logger.debug(f"[Priority] Bonus za engagement: +{engagement_bonus:.1f}")
        
        # Bonus za hashtagi i mentions
        hashtag_count = len([word for word in tweet_text.split() if word.startswith('#')])
        mention_count = len([word for word in tweet_text.split() if word.startswith('@')])
        social_bonus = min((hashtag_count + mention_count) * 0.5, 2.0)
        score += social_bonus
        
        # Bonus za techniczne słowa kluczowe
        tech_keywords = ['AI', 'ML', 'python', 'javascript', 'react', 'docker', 'kubernetes', 'aws']
        tech_count = sum(1 for keyword in tech_keywords if keyword.lower() in tweet_text.lower())
        tech_bonus = min(tech_count * 0.5, 3.0)
        score += tech_bonus
        
        # Konwertuj score na priorytet
        if score >= 15.0:
            priority = ProcessingPriority.URGENT
        elif score >= 10.0:
            priority = ProcessingPriority.HIGH
        elif score >= 5.0:
            priority = ProcessingPriority.MEDIUM
        else:
            priority = ProcessingPriority.LOW
        
        return priority, score

    def _is_thread_tweet(self, tweet_text: str, url: str) -> bool:
        """Sprawdza czy to tweet z threada"""
        thread_indicators = [
            r'\d+/\d+', r'\d+/', r'🧵', r'thread', r'wątek',
            r'1\)', r'1\.', r'część \d+', r'part \d+'
        ]
        
        import re
        for pattern in thread_indicators:
            if re.search(pattern, tweet_text, re.IGNORECASE):
                return True
        
        # Sprawdź czy tekst kończy się wielokropkiem
        if tweet_text.strip().endswith(('...', 'cd.', 'c.d.', '→')):
            return True
        
        return False

    def _categorize_content(self, url: str, tweet_text: str) -> str:
        """Kategoryzuje treść"""
        domain = urlparse(url).netloc.lower()
        
        # Kategorie na podstawie domeny
        domain_categories = {
            'technical': ['github.com', 'gitlab.com', 'stackoverflow.com', 'dev.to'],
            'documentation': ['docs.', 'documentation.', 'readthedocs.'],
            'research': ['arxiv.org', 'scholar.google', 'research.'],
            'news': ['techcrunch.com', 'arstechnica.com', 'wired.com'],
            'social': ['twitter.com', 'x.com', 'linkedin.com'],
            'video': ['youtube.com', 'vimeo.com'],
            'blog': ['medium.com', 'substack.com', 'blog.']
        }
        
        for category, domains in domain_categories.items():
            if any(cat_domain in domain for cat_domain in domains):
                return category
        
        # Kategorie na podstawie tekstu tweeta
        text_lower = tweet_text.lower()
        if any(word in text_lower for word in ['tutorial', 'how to', 'guide']):
            return 'tutorial'
        elif any(word in text_lower for word in ['research', 'paper', 'study']):
            return 'research'
        elif any(word in text_lower for word in ['news', 'breaking', 'update']):
            return 'news'
        
        return 'general'

    def _sort_queue(self):
        """Sortuje kolejkę według priorytetów"""
        self.queue.sort(key=lambda x: (x.priority.value, x.priority_score), reverse=True)

    def get_next_item(self) -> Optional[ProcessingItem]:
        """Pobiera następny element do przetworzenia"""
        if not self.queue:
            return None
        
        # Sprawdź czy nie ma elementów o wyższym priorytecie, które można retry
        for item in self.queue:
            if item.error_category and self._can_retry(item):
                self.queue.remove(item)
                return item
        
        # Pobierz pierwszy element z kolejki
        return self.queue.pop(0) if self.queue else None

    def _can_retry(self, item: ProcessingItem) -> bool:
        """Sprawdza czy element można ponowić"""
        if not item.error_category:
            return True
        
        max_retries = self.retry_limits.get(item.error_category, 1)
        return item.retry_count < max_retries

    def mark_completed(self, item_id: str, success: bool, content_data: Optional[Dict] = None, 
                      error: Optional[str] = None, processing_time: float = 0.0):
        """Oznacza element jako zakończony"""
        # Znajdź element w kolejce
        item = None
        for i, queue_item in enumerate(self.queue):
            if queue_item.id == item_id:
                item = self.queue.pop(i)
                break
        
        if not item:
            # Może być już przetworzony
            if item_id in self.processed_items:
                return
            self.logger.warning(f"[Queue] Nie znaleziono elementu {item_id}")
            return
        
        # Kategoryzuj błąd jeśli wystąpił
        error_category = None
        if not success and error:
            error_category = self._categorize_error(error, item.url)
            self._update_error_stats(error_category)
            self._update_domain_stats(item.url, success, error_category)
        
        # Sprawdź czy można ponowić
        if not success and error_category and self._can_retry(item):
            item.retry_count += 1
            item.last_error = error
            item.error_category = error_category
            
            # Zmniejsz priorytet przy retry
            item.priority_score *= 0.8
            
            self.queue.append(item)
            self._sort_queue()
            
            self.logger.info(f"[Queue] Retry {item.retry_count} dla {item_id}: {error_category.value}")
            return
        
        # Zapisz wynik
        result = ProcessingResult(
            item_id=item_id,
            success=success,
            content_data=content_data,
            error=error,
            error_category=error_category,
            processing_time=processing_time,
            retry_count=item.retry_count
        )
        
        self.processed_items[item_id] = result
        
        status = "SUKCES" if success else f"BŁĄD ({error_category.value if error_category else 'unknown'})"
        self.logger.info(f"[Queue] Zakończono {item_id}: {status}")

    def _categorize_error(self, error: str, url: str) -> ErrorCategory:
        """Kategoryzuje błąd"""
        error_lower = error.lower()
        
        if any(indicator in error_lower for indicator in ['paywall', 'subscription', 'premium']):
            return ErrorCategory.PAYWALL
        elif any(indicator in error_lower for indicator in ['403', 'forbidden', 'access denied']):
            return ErrorCategory.FORBIDDEN
        elif any(indicator in error_lower for indicator in ['timeout', 'timed out']):
            return ErrorCategory.TIMEOUT
        elif any(indicator in error_lower for indicator in ['javascript', 'js required', 'enable js']):
            return ErrorCategory.REQUIRES_JS
        elif any(indicator in error_lower for indicator in ['404', 'not found']):
            return ErrorCategory.NOT_FOUND
        elif any(indicator in error_lower for indicator in ['429', 'rate limit', 'too many requests']):
            return ErrorCategory.RATE_LIMITED
        else:
            return ErrorCategory.UNKNOWN

    def _update_error_stats(self, error_category: ErrorCategory):
        """Aktualizuje statystyki błędów"""
        if error_category not in self.error_stats:
            self.error_stats[error_category] = 0
        self.error_stats[error_category] += 1

    def _update_domain_stats(self, url: str, success: bool, error_category: Optional[ErrorCategory]):
        """Aktualizuje statystyki domeny"""
        domain = urlparse(url).netloc
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {
                'total': 0,
                'success': 0,
                'errors': {}
            }
        
        self.domain_stats[domain]['total'] += 1
        if success:
            self.domain_stats[domain]['success'] += 1
        elif error_category:
            error_key = error_category.value
            if error_key not in self.domain_stats[domain]['errors']:
                self.domain_stats[domain]['errors'][error_key] = 0
            self.domain_stats[domain]['errors'][error_key] += 1

    def _generate_item_id(self, url: str, tweet_text: str) -> str:
        """Generuje unikalny ID dla elementu"""
        content = f"{url}:{tweet_text}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def get_queue_status(self) -> Dict:
        """Zwraca status kolejki"""
        priority_counts = {}
        category_counts = {}
        
        for item in self.queue:
            # Priorytet
            if item.priority not in priority_counts:
                priority_counts[item.priority] = 0
            priority_counts[item.priority] += 1
            
            # Kategoria
            if item.category not in category_counts:
                category_counts[item.category] = 0
            category_counts[item.category] += 1
        
        return {
            'queue_length': len(self.queue),
            'processed_count': len(self.processed_items),
            'priority_distribution': {p.name: count for p, count in priority_counts.items()},
            'category_distribution': category_counts,
            'error_stats': {cat.value: count for cat, count in self.error_stats.items()},
            'top_problematic_domains': self._get_problematic_domains()
        }

    def _get_problematic_domains(self, limit: int = 5) -> List[Dict]:
        """Zwraca najbardziej problematyczne domeny"""
        domain_scores = []
        
        for domain, stats in self.domain_stats.items():
            if stats['total'] < 3:  # Ignoruj domeny z małą liczbą prób
                continue
            
            success_rate = stats['success'] / stats['total']
            error_count = stats['total'] - stats['success']
            
            domain_scores.append({
                'domain': domain,
                'total_attempts': stats['total'],
                'success_rate': success_rate,
                'error_count': error_count,
                'main_errors': stats.get('errors', {})
            })
        
        # Sortuj według najgorszego success rate
        domain_scores.sort(key=lambda x: x['success_rate'])
        return domain_scores[:limit]

    def export_analytics(self) -> Dict:
        """Eksportuje analytics do raportu"""
        successful_items = [r for r in self.processed_items.values() if r.success]
        failed_items = [r for r in self.processed_items.values() if not r.success]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_processed': len(self.processed_items),
                'successful': len(successful_items),
                'failed': len(failed_items),
                'success_rate': len(successful_items) / len(self.processed_items) if self.processed_items else 0,
                'queue_remaining': len(self.queue)
            },
            'error_analysis': self.error_stats,
            'domain_analysis': self.domain_stats,
            'processing_times': {
                'avg_success': sum(r.processing_time for r in successful_items) / len(successful_items) if successful_items else 0,
                'avg_failed': sum(r.processing_time for r in failed_items) / len(failed_items) if failed_items else 0
            },
            'retry_analysis': {
                'items_retried': len([r for r in self.processed_items.values() if r.retry_count > 0]),
                'avg_retries': sum(r.retry_count for r in self.processed_items.values()) / len(self.processed_items) if self.processed_items else 0
            }
        }

    def clear_queue(self):
        """Czyści kolejkę"""
        self.queue.clear()
        self.logger.info("[Queue] Kolejka wyczyszczona")

    def get_recommendations(self) -> List[str]:
        """Zwraca rekomendacje na podstawie analizy"""
        recommendations = []
        
        # Analiza error stats
        if ErrorCategory.PAYWALL in self.error_stats and self.error_stats[ErrorCategory.PAYWALL] > 5:
            recommendations.append("Rozważ implementację alternatywnych strategii dla domen z paywallem")
        
        if ErrorCategory.TIMEOUT in self.error_stats and self.error_stats[ErrorCategory.TIMEOUT] > 10:
            recommendations.append("Zwiększ timeout dla requestów lub zoptymalizuj extractory")
        
        # Analiza success rate
        total = len(self.processed_items)
        if total > 10:
            success_rate = len([r for r in self.processed_items.values() if r.success]) / total
            if success_rate < 0.5:
                recommendations.append("Ogólny success rate jest niski - rozważ rewizję strategii")
        
        # Analiza domen
        problematic = self._get_problematic_domains(3)
        if problematic:
            worst_domain = problematic[0]
            if worst_domain['success_rate'] < 0.3:
                recommendations.append(f"Domena {worst_domain['domain']} ma bardzo niski success rate - rozważ blacklistę")
        
        return recommendations