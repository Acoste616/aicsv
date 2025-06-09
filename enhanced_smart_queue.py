# enhanced_smart_queue.py
"""
Ulepszona wersja SmartProcessingQueue zintegrowana z Enhanced Content Strategy
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import Enum
from enhanced_content_strategy import EnhancedContentStrategy

class ContentType(Enum):
    THREAD = "thread"
    GITHUB = "github" 
    RESEARCH = "research"
    DOCUMENTATION = "documentation"
    NEWS = "news"
    VIDEO = "video"
    BLOG = "blog"
    UNKNOWN = "unknown"

class UrgencyLevel(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1

@dataclass
class PrioritizedTweet:
    """Tweet z obliczonym priorytetem"""
    original_data: Dict
    priority_score: float
    urgency_level: UrgencyLevel
    content_type: ContentType
    estimated_processing_time: int  # sekundy
    reasons: List[str]  # powody wysokiego/niskiego priorytetu

class EnhancedSmartProcessingQueue:
    """
    Rozszerzona wersja SmartProcessingQueue z zaawansowaną priorytetyzacją
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.content_strategy = EnhancedContentStrategy()
        
        # Konfiguracja priorytetów
        self.domain_priorities = {
            # Najwyższy priorytet - development/research
            'github.com': 10,
            'gitlab.com': 9,
            'arxiv.org': 10,
            'scholar.google.com': 9,
            'docs.': 8,
            'documentation.': 8,
            'stackoverflow.com': 8,
            
            # Wysokie priorytety - edukacja/tech
            'dev.to': 7,
            'medium.com': 6,
            'blog.': 5,
            'techcrunch.com': 6,
            'arstechnica.com': 6,
            
            # Średnie priorytety - news
            'wired.com': 5,
            'theverge.com': 5,
            
            # Niskie priorytety - paywall/problematyczne
            'nytimes.com': -2,
            'wsj.com': -3,
            'bloomberg.com': -2,
            'economist.com': -2
        }
        
        # Słowa kluczowe zwiększające priorytet
        self.high_value_keywords = {
            'ai': 3, 'machine learning': 3, 'deep learning': 3,
            'python': 2, 'javascript': 2, 'react': 2, 'vue': 2,
            'docker': 2, 'kubernetes': 2, 'aws': 2, 'azure': 2,
            'blockchain': 2, 'crypto': 1, 'web3': 1,
            'tutorial': 3, 'guide': 2, 'how to': 2,
            'research': 3, 'paper': 2, 'study': 2,
            'breakthrough': 4, 'innovation': 3, 'release': 2
        }
        
        # Statystyki
        self.processing_stats = {
            'total_processed': 0,
            'by_priority': {},
            'avg_processing_times': {},
            'success_rates': {}
        }

    def prioritize_tweets(self, tweets: List[Dict]) -> List[PrioritizedTweet]:
        """
        Ulepszona wersja priorytetyzacji z zaawansowanymi kryteriami
        """
        self.logger.info(f"[Queue] Priorytetuję {len(tweets)} tweetów...")
        
        prioritized_tweets = []
        
        for tweet in tweets:
            try:
                prioritized = self._calculate_comprehensive_priority(tweet)
                prioritized_tweets.append(prioritized)
            except Exception as e:
                self.logger.error(f"[Queue] Błąd priorytetyzacji tweeta: {e}")
                # Fallback - niski priorytet
                prioritized_tweets.append(PrioritizedTweet(
                    original_data=tweet,
                    priority_score=1.0,
                    urgency_level=UrgencyLevel.LOW,
                    content_type=ContentType.UNKNOWN,
                    estimated_processing_time=30,
                    reasons=['Błąd podczas analizy']
                ))
        
        # Sortuj według priorytetu
        prioritized_tweets.sort(key=lambda x: (x.urgency_level.value, x.priority_score), reverse=True)
        
        self._log_prioritization_results(prioritized_tweets)
        return prioritized_tweets

    def _calculate_comprehensive_priority(self, tweet: Dict) -> PrioritizedTweet:
        """
        Oblicza kompleksowy priorytet dla tweeta
        """
        score = 0.0
        reasons = []
        
        text = tweet.get('text', '')
        url = tweet.get('url', '')
        
        # 1. PODSTAWOWE KRYTERIA (z oryginalnego kodu)
        
        # Thready - najwyższy priorytet
        if self._is_thread(text):
            score += 10
            reasons.append("Thread Twitter (+10)")
        
        # Engagement
        likes = tweet.get('likes', 0)
        retweets = tweet.get('retweets', 0)
        engagement_score = (likes + retweets * 2) / 100
        if engagement_score > 0:
            score += min(engagement_score, 8)  # Cap na 8 punktów
            reasons.append(f"Engagement: {likes}❤️ {retweets}🔄 (+{engagement_score:.1f})")
        
        # Obrazy
        if tweet.get('has_images'):
            score += 3
            reasons.append("Ma obrazy (+3)")
        
        # 2. ROZSZERZONE KRYTERIA
        
        # Analiza domeny
        domain_score = self._analyze_domain(url)
        if domain_score != 0:
            score += domain_score
            domain = urlparse(url).netloc
            reasons.append(f"Domena {domain} ({domain_score:+.1f})")
        
        # Analiza słów kluczowych
        keyword_score = self._analyze_keywords(text)
        if keyword_score > 0:
            score += keyword_score
            reasons.append(f"Słowa kluczowe (+{keyword_score:.1f})")
        
        # Analiza czasu
        time_score = self._analyze_temporal_factors(tweet)
        if time_score != 0:
            score += time_score
            reasons.append(f"Faktor czasowy ({time_score:+.1f})")
        
        # Analiza autora
        author_score = self._analyze_author(tweet)
        if author_score > 0:
            score += author_score
            reasons.append(f"Autor (+{author_score:.1f})")
        
        # 3. IDENTYFIKACJA TYPU TREŚCI
        content_type = self._identify_content_type(url, text)
        
        # 4. BONUS ZA TYP TREŚCI
        type_bonus = self._get_content_type_bonus(content_type)
        if type_bonus > 0:
            score += type_bonus
            reasons.append(f"Typ: {content_type.value} (+{type_bonus})")
        
        # 5. OKREŚL POZIOM URGENCY
        urgency = self._determine_urgency_level(score, content_type, tweet)
        
        # 6. SZACUJ CZAS PRZETWARZANIA
        estimated_time = self._estimate_processing_time(content_type, url)
        
        # 7. ZASTOSUJ MODYFIKATORY KONTEKSTOWE
        context_modifier = self._apply_context_modifiers(tweet, score)
        if context_modifier != 1.0:
            original_score = score
            score *= context_modifier
            reasons.append(f"Modyfikator kontekstowy: {original_score:.1f} × {context_modifier:.2f} = {score:.1f}")
        
        return PrioritizedTweet(
            original_data=tweet,
            priority_score=round(score, 2),
            urgency_level=urgency,
            content_type=content_type,
            estimated_processing_time=estimated_time,
            reasons=reasons
        )

    def _is_thread(self, text: str) -> bool:
        """Sprawdza czy tweet jest częścią threada"""
        thread_indicators = [
            r'\d+/\d+',      # 1/5, 2/10 itp
            r'\d+/',         # 1/, 2/ itp  
            r'🧵',           # emoji thread
            r'thread',       # słowo "thread"
            r'wątek',        # polskie "wątek"
            r'1\)',          # 1) na początku
            r'1\.',          # 1. na początku
            r'część \d+',    # część 1, część 2
            r'part \d+',     # part 1, part 2
            r'cd\.',         # ciąg dalszy
            r'c\.d\.',       # ciąg dalszy
        ]
        
        for pattern in thread_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Sprawdź czy kończy się wielokropkiem (często oznacza kontynuację)
        if text.strip().endswith(('...', '→', '➡️')):
            return True
        
        return False

    def _analyze_domain(self, url: str) -> float:
        """Analizuje domenę i zwraca score"""
        if not url:
            return 0
        
        try:
            domain = urlparse(url).netloc.lower()
            
            # Sprawdź dokładne dopasowania
            if domain in self.domain_priorities:
                return self.domain_priorities[domain]
            
            # Sprawdź częściowe dopasowania
            for domain_pattern, score in self.domain_priorities.items():
                if domain_pattern in domain:
                    return score
            
            return 0
            
        except Exception:
            return 0

    def _analyze_keywords(self, text: str) -> float:
        """Analizuje słowa kluczowe w tekście"""
        text_lower = text.lower()
        total_score = 0
        
        for keyword, score in self.high_value_keywords.items():
            if keyword in text_lower:
                total_score += score
        
        # Cap na 10 punktów za słowa kluczowe
        return min(total_score, 10)

    def _analyze_temporal_factors(self, tweet: Dict) -> float:
        """Analizuje czynniki czasowe"""
        score = 0
        text = tweet.get('text', '').lower()
        
        # Słowa wskazujące na aktualność
        urgent_indicators = ['breaking', 'urgent', 'just released', 'new', 'today', 'now']
        for indicator in urgent_indicators:
            if indicator in text:
                score += 2
                break
        
        # Słowa wskazujące na starą treść
        old_indicators = ['old', 'outdated', 'legacy', 'deprecated']
        for indicator in old_indicators:
            if indicator in text:
                score -= 3
                break
        
        return score

    def _analyze_author(self, tweet: Dict) -> float:
        """Analizuje autora tweeta"""
        author = tweet.get('author', '').lower()
        
        # Wzory wskazujące na wartościowych autorów
        valuable_patterns = [
            'dev', 'engineer', 'researcher', 'scientist', 'founder',
            'cto', 'ceo', 'tech', 'ai', 'ml', 'data'
        ]
        
        for pattern in valuable_patterns:
            if pattern in author:
                return 2
        
        return 0

    def _identify_content_type(self, url: str, text: str) -> ContentType:
        """Identyfikuje typ treści"""
        if not url:
            return ContentType.UNKNOWN
        
        domain = urlparse(url).netloc.lower()
        text_lower = text.lower()
        
        # Thread
        if self._is_thread(text):
            return ContentType.THREAD
        
        # GitHub
        if 'github.com' in domain or 'gitlab.com' in domain:
            return ContentType.GITHUB
        
        # Research
        if any(d in domain for d in ['arxiv.org', 'scholar.google', 'research.']):
            return ContentType.RESEARCH
        
        # Documentation
        if any(d in domain for d in ['docs.', 'documentation.', 'readthedocs']):
            return ContentType.DOCUMENTATION
        
        # Video
        if any(d in domain for d in ['youtube.com', 'vimeo.com', 'youtu.be']):
            return ContentType.VIDEO
        
        # News
        if any(d in domain for d in ['techcrunch.com', 'arstechnica.com', 'wired.com']):
            return ContentType.NEWS
        
        # Blog
        if any(d in domain for d in ['medium.com', 'dev.to', 'blog.']):
            return ContentType.BLOG
        
        # Analiza na podstawie tekstu
        if any(word in text_lower for word in ['tutorial', 'guide', 'how to']):
            return ContentType.DOCUMENTATION
        
        return ContentType.UNKNOWN

    def _get_content_type_bonus(self, content_type: ContentType) -> float:
        """Bonus punktów za typ treści"""
        bonuses = {
            ContentType.THREAD: 5,        # Threads są bardzo wartościowe
            ContentType.GITHUB: 4,        # Kod jest praktyczny
            ContentType.RESEARCH: 4,      # Research ma wysoką wartość
            ContentType.DOCUMENTATION: 3,  # Dokumentacja jest przydatna
            ContentType.VIDEO: 2,         # Video może być wartościowe
            ContentType.BLOG: 2,          # Blogi bywają przydatne
            ContentType.NEWS: 1,          # News ma średnią wartość
            ContentType.UNKNOWN: 0        # Nieznane - brak bonusu
        }
        
        return bonuses.get(content_type, 0)

    def _determine_urgency_level(self, score: float, content_type: ContentType, tweet: Dict) -> UrgencyLevel:
        """Określa poziom urgency"""
        
        # Specjalne przypadki
        if content_type == ContentType.THREAD and score >= 15:
            return UrgencyLevel.CRITICAL
        
        if content_type == ContentType.GITHUB and score >= 12:
            return UrgencyLevel.CRITICAL
        
        # Standardowe progi
        if score >= 20:
            return UrgencyLevel.CRITICAL
        elif score >= 12:
            return UrgencyLevel.HIGH
        elif score >= 6:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW

    def _estimate_processing_time(self, content_type: ContentType, url: str) -> int:
        """Szacuje czas przetwarzania w sekundach"""
        
        base_times = {
            ContentType.THREAD: 45,        # Threads wymagają więcej czasu
            ContentType.GITHUB: 30,        # GitHub API może być szybsze
            ContentType.RESEARCH: 60,      # Research papers są długie
            ContentType.DOCUMENTATION: 35, # Docs zazwyczaj dostępne
            ContentType.VIDEO: 25,         # Tylko metadane
            ContentType.BLOG: 30,          # Standardowe artykuły
            ContentType.NEWS: 20,          # Krótsze artykuły
            ContentType.UNKNOWN: 15        # Prawdopodobnie błąd/paywall
        }
        
        base_time = base_times.get(content_type, 30)
        
        # Modyfikator na podstawie domeny
        if any(problematic in url for problematic in ['nytimes.', 'wsj.', 'bloomberg.']):
            base_time = 10  # Prawdopodobnie paywall - szybki błąd
        
        return base_time

    def _apply_context_modifiers(self, tweet: Dict, current_score: float) -> float:
        """Stosuje modyfikatory kontekstowe"""
        modifier = 1.0
        
        # Modyfikator dla bardzo wysokiego engagement
        likes = tweet.get('likes', 0)
        retweets = tweet.get('retweets', 0)
        total_engagement = likes + retweets * 2
        
        if total_engagement > 1000:
            modifier *= 1.2  # +20% dla viral content
        elif total_engagement > 10000:
            modifier *= 1.5  # +50% dla bardzo viral content
        
        # Modyfikator dla długości tweeta
        text_length = len(tweet.get('text', ''))
        if text_length > 200:
            modifier *= 1.1  # +10% dla długich, przemyślanych tweetów
        elif text_length < 50:
            modifier *= 0.9  # -10% dla bardzo krótkich tweetów
        
        return modifier

    def _log_prioritization_results(self, prioritized_tweets: List[PrioritizedTweet]):
        """Loguje wyniki priorytetyzacji"""
        if not prioritized_tweets:
            return
        
        self.logger.info(f"[Queue] Priorytetyzacja zakończona:")
        
        # Statystyki poziomów urgency
        urgency_counts = {}
        for tweet in prioritized_tweets:
            level = tweet.urgency_level.name
            urgency_counts[level] = urgency_counts.get(level, 0) + 1
        
        for level, count in urgency_counts.items():
            self.logger.info(f"  {level}: {count} tweetów")
        
        # Top 3 tweety
        self.logger.info("  Top 3 tweety:")
        for i, tweet in enumerate(prioritized_tweets[:3], 1):
            url_short = tweet.original_data.get('url', '')[:50] + '...'
            self.logger.info(f"    {i}. Score: {tweet.priority_score}, Urgency: {tweet.urgency_level.name}")
            self.logger.info(f"       URL: {url_short}")
            self.logger.info(f"       Powody: {', '.join(tweet.reasons[:2])}")

    def get_processing_order(self, tweets: List[Dict]) -> List[Dict]:
        """
        Zwraca tweety w kolejności przetwarzania (kompatybilność z oryginalnym API)
        """
        prioritized = self.prioritize_tweets(tweets)
        return [pt.original_data for pt in prioritized]

    def get_priority_analytics(self, prioritized_tweets: List[PrioritizedTweet]) -> Dict:
        """Zwraca analytics priorytetyzacji"""
        
        analytics = {
            'total_tweets': len(prioritized_tweets),
            'urgency_distribution': {},
            'content_type_distribution': {},
            'avg_score_by_type': {},
            'estimated_total_time': 0,
            'top_domains': {},
            'common_reasons': {}
        }
        
        # Rozkład urgency
        for tweet in prioritized_tweets:
            urgency = tweet.urgency_level.name
            analytics['urgency_distribution'][urgency] = analytics['urgency_distribution'].get(urgency, 0) + 1
            
            # Rozkład typów treści
            content_type = tweet.content_type.name
            analytics['content_type_distribution'][content_type] = analytics['content_type_distribution'].get(content_type, 0) + 1
            
            # Szacowany czas
            analytics['estimated_total_time'] += tweet.estimated_processing_time
            
            # Domeny
            url = tweet.original_data.get('url', '')
            if url:
                domain = urlparse(url).netloc
                analytics['top_domains'][domain] = analytics['top_domains'].get(domain, 0) + 1
            
            # Powody
            for reason in tweet.reasons:
                analytics['common_reasons'][reason] = analytics['common_reasons'].get(reason, 0) + 1
        
        # Średnie score per typ
        type_scores = {}
        type_counts = {}
        
        for tweet in prioritized_tweets:
            content_type = tweet.content_type.name
            if content_type not in type_scores:
                type_scores[content_type] = 0
                type_counts[content_type] = 0
            
            type_scores[content_type] += tweet.priority_score
            type_counts[content_type] += 1
        
        for content_type in type_scores:
            analytics['avg_score_by_type'][content_type] = type_scores[content_type] / type_counts[content_type]
        
        # Konwertuj czas na minuty
        analytics['estimated_total_time_minutes'] = analytics['estimated_total_time'] / 60
        
        return analytics


# Demo i testy
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test data
    sample_tweets = [
        {
            'text': '🧵 Thread about AI safety 1/7',
            'url': 'https://github.com/anthropic/safety',
            'likes': 234,
            'retweets': 67,
            'has_images': True,
            'author': 'ai_researcher'
        },
        {
            'text': 'Interesting article about web development',
            'url': 'https://medium.com/some-article',
            'likes': 45,
            'retweets': 12,
            'has_images': False,
            'author': 'webdev_guy'
        },
        {
            'text': 'Breaking: New Python release!',
            'url': 'https://docs.python.org/3.12/',
            'likes': 567,
            'retweets': 123,
            'has_images': False,
            'author': 'python_dev'
        },
        {
            'text': 'Check out this paywall article',
            'url': 'https://nytimes.com/some-article',
            'likes': 23,
            'retweets': 5,
            'has_images': False,
            'author': 'news_bot'
        }
    ]
    
    # Test Enhanced Queue
    queue = EnhancedSmartProcessingQueue()
    
    print("🚀 DEMO: Enhanced Smart Processing Queue")
    print("=" * 60)
    
    prioritized = queue.prioritize_tweets(sample_tweets)
    
    print(f"\n📊 WYNIKI PRIORYTETYZACJI:")
    for i, tweet in enumerate(prioritized, 1):
        print(f"\n{i}. PRIORYTET: {tweet.urgency_level.name} (Score: {tweet.priority_score})")
        print(f"   URL: {tweet.original_data['url'][:50]}...")
        print(f"   Typ: {tweet.content_type.name}")
        print(f"   Czas: ~{tweet.estimated_processing_time}s")
        print(f"   Powody: {', '.join(tweet.reasons[:3])}")
    
    # Analytics
    analytics = queue.get_priority_analytics(prioritized)
    print(f"\n📈 ANALYTICS:")
    print(f"   Łączny czas: ~{analytics['estimated_total_time_minutes']:.1f} min")
    print(f"   Urgency: {analytics['urgency_distribution']}")
    print(f"   Typy treści: {analytics['content_type_distribution']}")