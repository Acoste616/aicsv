# smart_queue.py
"""
Inteligentna kolejka przetwarzania z priorytetyzacją
"""

import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import Enum
import hashlib
import re

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
    id: str
    url: str
    tweet_text: str
    priority: ProcessingPriority
    priority_score: float
    category: str
    retry_count: int = 0
    last_error: Optional[str] = None

class SmartProcessingQueue:
    """Inteligentna kolejka z priorytetyzacją"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.queue: List[ProcessingItem] = []
        self.processed_items: Dict[str, bool] = {}
        self.error_stats: Dict[str, int] = {}
        
        # Domeny wysokiego priorytetu
        self.priority_domains = [
            'github.com', 'gitlab.com', 'docs.', 'documentation.',
            'arxiv.org', 'scholar.google', 'stackoverflow.com'
        ]
        
        # Domeny problematyczne
        self.problematic_domains = [
            'nytimes.com', 'wsj.com', 'bloomberg.com'
        ]

    def add_item(self, url: str, tweet_text: str, tweet_data: Optional[Dict] = None) -> str:
        """Dodaje element do kolejki z priorytetyzacją"""
        item_id = self._generate_item_id(url, tweet_text)
        
        # Sprawdź czy już przetwarzany
        if item_id in self.processed_items:
            return item_id
        
        # Oblicz priorytet
        priority, score = self._calculate_priority(url, tweet_text, tweet_data)
        category = self._categorize_content(url, tweet_text)
        
        item = ProcessingItem(
            id=item_id,
            url=url,
            tweet_text=tweet_text,
            priority=priority,
            priority_score=score,
            category=category
        )
        
        self.queue.append(item)
        self._sort_queue()
        
        self.logger.info(f"[Queue] Dodano: {item_id}, priorytet: {priority.name}")
        return item_id

    def _calculate_priority(self, url: str, tweet_text: str, tweet_data: Optional[Dict]) -> Tuple[ProcessingPriority, float]:
        """Oblicza priorytet"""
        score = 0.0
        domain = urlparse(url).netloc.lower()
        
        # Bonus za wysokopriorytetowe domeny
        if any(d in domain for d in self.priority_domains):
            score += 10.0
        
        # Kara za problematyczne domeny
        if any(d in domain for d in self.problematic_domains):
            score -= 5.0
        
        # Bonus za thread
        if self._is_thread_tweet(tweet_text):
            score += 5.0
        
        # Bonus za długość tweeta
        score += min(len(tweet_text) / 50, 3.0)
        
        # Bonus za engagement
        if tweet_data:
            likes = tweet_data.get('likes', 0)
            retweets = tweet_data.get('retweets', 0)
            score += min((likes + retweets * 2) / 100, 5.0)
        
        # Konwertuj na priorytet
        if score >= 15.0:
            return ProcessingPriority.URGENT, score
        elif score >= 10.0:
            return ProcessingPriority.HIGH, score
        elif score >= 5.0:
            return ProcessingPriority.MEDIUM, score
        else:
            return ProcessingPriority.LOW, score

    def _is_thread_tweet(self, tweet_text: str) -> bool:
        """Sprawdza czy to thread"""
        thread_patterns = [r'\d+/\d+', r'🧵', r'thread', r'1\)']
        for pattern in thread_patterns:
            if re.search(pattern, tweet_text, re.IGNORECASE):
                return True
        return tweet_text.strip().endswith(('...', 'cd.'))

    def _categorize_content(self, url: str, tweet_text: str) -> str:
        """Kategoryzuje treść"""
        domain = urlparse(url).netloc.lower()
        
        if 'github.com' in domain:
            return 'code'
        elif any(d in domain for d in ['docs.', 'documentation.']):
            return 'documentation'
        elif 'youtube.com' in domain:
            return 'video'
        elif any(word in tweet_text.lower() for word in ['tutorial', 'guide']):
            return 'tutorial'
        else:
            return 'general'

    def _sort_queue(self):
        """Sortuje kolejkę według priorytetów"""
        self.queue.sort(key=lambda x: (x.priority.value, x.priority_score), reverse=True)

    def get_next_item(self) -> Optional[ProcessingItem]:
        """Pobiera następny element"""
        return self.queue.pop(0) if self.queue else None

    def mark_completed(self, item_id: str, success: bool, error: Optional[str] = None):
        """Oznacza jako zakończone"""
        self.processed_items[item_id] = success
        
        if not success and error:
            error_category = self._categorize_error(error)
            self.error_stats[error_category] = self.error_stats.get(error_category, 0) + 1

    def _categorize_error(self, error: str) -> str:
        """Kategoryzuje błąd"""
        error_lower = error.lower()
        
        if 'paywall' in error_lower:
            return 'paywall'
        elif '403' in error_lower or 'forbidden' in error_lower:
            return 'forbidden'
        elif 'timeout' in error_lower:
            return 'timeout'
        elif 'javascript' in error_lower:
            return 'requires_js'
        else:
            return 'unknown'

    def _generate_item_id(self, url: str, tweet_text: str) -> str:
        """Generuje ID"""
        content = f"{url}:{tweet_text}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def get_status(self) -> Dict:
        """Status kolejki"""
        return {
            'queue_length': len(self.queue),
            'processed_count': len(self.processed_items),
            'success_rate': sum(self.processed_items.values()) / len(self.processed_items) if self.processed_items else 0,
            'error_stats': self.error_stats
        } 