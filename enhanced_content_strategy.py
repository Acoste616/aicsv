# enhanced_content_strategy.py
"""
Inteligentna strategia pozyskiwania treści z wielopoziomowym fallback'iem
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional, Any
import re
import time
import json
import hashlib
from urllib.parse import urlparse, parse_qs
from content_extractor import ContentExtractor
from config import EXTRACTION_CONFIG, LLM_CONFIG
import os

class EnhancedContentStrategy:
    """Inteligentna strategia pozyskiwania treści z wielopoziomowym fallback'iem"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.content_extractor = ContentExtractor()
        self.session = requests.Session()
        self.cache = {}
        self._setup_session()
        
        # Konfiguracja strategii
        self.quality_levels = {
            'high': {'min_length': 1000, 'confidence': 0.9},
            'medium': {'min_length': 200, 'confidence': 0.6},
            'low': {'min_length': 50, 'confidence': 0.3}
        }
        
        # Domeny z wysokim priorytetem
        self.priority_domains = [
            'github.com', 'gitlab.com', 'docs.', 'documentation.',
            'arxiv.org', 'scholar.google', 'research.',
            'blog.', 'medium.com', 'dev.to', 'stackoverflow.com'
        ]
        
        # Domeny problematyczne (paywall, etc.)
        self.problematic_domains = [
            'nytimes.com', 'wsj.com', 'bloomberg.com', 'ft.com',
            'economist.com', 'reuters.com', 'washingtonpost.com'
        ]

    def _setup_session(self):
        """Konfiguruje sesję HTTP"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

    def get_content(self, url: str, tweet_text: str, tweet_data: Optional[Dict] = None) -> Dict:
        """
        Wielopoziomowa strategia pozyskiwania treści
        
        Args:
            url: URL do analizy
            tweet_text: Tekst tweeta
            tweet_data: Dodatkowe dane tweeta (opcjonalne)
            
        Returns:
            Dict z treścią, źródłem i jakością
        """
        self.logger.info(f"[Strategy] Analizuję: {url}")
        
        # Cache check
        cache_key = self._get_cache_key(url, tweet_text)
        if cache_key in self.cache:
            self.logger.info("[Strategy] Używam cache")
            return self.cache[cache_key]
        
        result = None
        
        try:
            # 1. Najpierw sprawdź czy URL jest dostępny publicznie
            if self._is_publicly_accessible(url):
                self.logger.info("[Strategy] URL publicznie dostępny - pełna ekstrakcja")
                result = self._extract_full_content(url, tweet_text)
                if result and result['quality'] == 'high':
                    self.cache[cache_key] = result
                    return result
            
            # 2. Jeśli nie, użyj metadanych
            self.logger.info("[Strategy] Próba metadanych")
            metadata = self._extract_metadata(url)
            if metadata and metadata.get('description') and len(metadata['description']) > 100:
                result = {
                    'content': self._format_metadata_content(metadata, tweet_text),
                    'source': 'metadata',
                    'quality': 'medium',
                    'confidence': 0.6,
                    'url': url,
                    'metadata': metadata
                }
                self.cache[cache_key] = result
                return result
            
            # 3. Użyj preview/summary API jeśli dostępne
            self.logger.info("[Strategy] Próba preview API")
            preview = self._get_preview_content(url)
            if preview:
                result = {
                    'content': preview,
                    'source': 'preview_api',
                    'quality': 'medium',
                    'confidence': 0.6,
                    'url': url
                }
                self.cache[cache_key] = result
                return result
            
            # 4. Wzbogać tweet o kontekst z threadów
            if self._is_thread_tweet(tweet_text, url):
                self.logger.info("[Strategy] Wykryto thread - zbieranie")
                thread_content = self._collect_full_thread(url, tweet_text)
                if thread_content:
                    result = {
                        'content': thread_content,
                        'source': 'thread',
                        'quality': 'high',
                        'confidence': 0.8,
                        'url': url
                    }
                    self.cache[cache_key] = result
                    return result
            
            # 5. Sprawdź alternatywne źródła
            self.logger.info("[Strategy] Próba alternatywnych źródeł")
            alternative = self._get_alternative_content(url)
            if alternative:
                result = alternative
                self.cache[cache_key] = result
                return result
            
            # 6. Użyj samego tweeta z dodatkowym kontekstem
            self.logger.info("[Strategy] Fallback do wzbogaconego tweeta")
            result = {
                'content': self._enrich_tweet_context(tweet_text, url, tweet_data),
                'source': 'tweet_enriched',
                'quality': 'low',
                'confidence': 0.3,
                'url': url
            }
            
        except Exception as e:
            self.logger.error(f"[Strategy] Błąd: {e}")
            result = {
                'content': self._enrich_tweet_context(tweet_text, url, tweet_data),
                'source': 'tweet_fallback',
                'quality': 'low',
                'confidence': 0.2,
                'url': url,
                'error': str(e)
            }
        
        self.cache[cache_key] = result
        return result

    def _is_publicly_accessible(self, url: str) -> bool:
        """Sprawdza czy URL jest publicznie dostępny"""
        try:
            # Sprawdź domenę
            domain = urlparse(url).netloc.lower()
            
            # Problematyczne domeny
            if any(prob_domain in domain for prob_domain in self.problematic_domains):
                self.logger.info(f"[Strategy] Domena {domain} na liście problematycznych")
                return False
            
            # Priorytetowe domeny
            if any(prio_domain in domain for prio_domain in self.priority_domains):
                self.logger.info(f"[Strategy] Domena {domain} ma wysoki priorytet")
                return True
            
            # Szybki test HEAD request
            try:
                response = self.session.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' in content_type:
                        return True
            except:
                pass
            
            return False
            
        except Exception as e:
            self.logger.warning(f"[Strategy] Błąd sprawdzania dostępności: {e}")
            return False

    def _extract_full_content(self, url: str, tweet_text: str) -> Dict:
        """Ekstrakcja pełnej treści artykułu"""
        try:
            content = self.content_extractor.extract_with_retry(url)
            
            if content and len(content) > self.quality_levels['high']['min_length']:
                return {
                    'content': content,
                    'source': 'full_extraction',
                    'quality': 'high',
                    'confidence': 0.9,
                    'url': url,
                    'length': len(content)
                }
            elif content and len(content) > self.quality_levels['medium']['min_length']:
                return {
                    'content': content,
                    'source': 'partial_extraction',
                    'quality': 'medium',
                    'confidence': 0.6,
                    'url': url,
                    'length': len(content)
                }
            
        except Exception as e:
            self.logger.error(f"[Strategy] Błąd pełnej ekstrakcji: {e}")
        
        return None

    def _extract_metadata(self, url: str) -> Optional[Dict]:
        """Ekstraktuje metadane ze strony"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            metadata = {}
            
            # Open Graph tags
            og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
            for tag in og_tags:
                prop = tag.get('property', '').replace('og:', '')
                content = tag.get('content', '')
                if content:
                    metadata[f'og_{prop}'] = content
            
            # Twitter Card tags
            twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
            for tag in twitter_tags:
                name = tag.get('name', '').replace('twitter:', '')
                content = tag.get('content', '')
                if content:
                    metadata[f'twitter_{name}'] = content
            
            # Standard meta tags
            description_tag = soup.find('meta', attrs={'name': 'description'})
            if description_tag:
                metadata['description'] = description_tag.get('content', '')
            
            # Title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text(strip=True)
            
            self.logger.info(f"[Strategy] Metadane: {len(metadata)} tagów")
            return metadata if metadata else None
            
        except Exception as e:
            self.logger.warning(f"[Strategy] Błąd metadanych: {e}")
            return None

    def _format_metadata_content(self, metadata: Dict, tweet_text: str) -> str:
        """Formatuje treść z metadanych"""
        parts = []
        
        # Tytuł
        title = metadata.get('title') or metadata.get('og_title') or metadata.get('twitter_title')
        if title:
            parts.append(f"Tytuł: {title}")
        
        # Opis
        description = (metadata.get('og_description') or 
                      metadata.get('twitter_description') or 
                      metadata.get('description'))
        if description:
            parts.append(f"Opis: {description}")
        
        # Typ treści
        og_type = metadata.get('og_type')
        if og_type:
            parts.append(f"Typ: {og_type}")
        
        # Kontekst z tweeta
        if tweet_text:
            parts.append(f"Komentarz autora: {tweet_text}")
        
        return '\n\n'.join(parts)

    def _get_preview_content(self, url: str) -> Optional[str]:
        """Próba pobrania preview z API (placeholder)"""
        # Tu można dodać integrację z serwisami typu:
        # - Mercury Parser API
        # - Readability API
        # - Extract API
        
        # Na razie zwracamy None
        return None

    def _is_thread_tweet(self, tweet_text: str, url: str) -> bool:
        """Sprawdza czy to tweet z threada"""
        thread_indicators = [
            r'\d+/\d+', r'\d+/', r'🧵', r'thread', r'wątek',
            r'1\)', r'1\.', r'część \d+', r'part \d+'
        ]
        
        # Sprawdź URL - czy ma pattern threada
        if 'twitter.com' in url or 'x.com' in url:
            if re.search(r'/status/\d+', url):
                # Sprawdź tekst tweeta
                for pattern in thread_indicators:
                    if re.search(pattern, tweet_text, re.IGNORECASE):
                        return True
        
        # Sprawdź czy tekst kończy się wielokropkiem lub "cd."
        if tweet_text.strip().endswith(('...', 'cd.', 'c.d.', '→')):
            return True
        
        return False

    def _collect_full_thread(self, url: str, tweet_text: str) -> Optional[str]:
        """Zbiera pełny thread z Twittera (uproszczona implementacja)"""
        try:
            # Próba pobrania strony tweeta
            content = self.content_extractor.get_webpage_content(url)
            if not content:
                return None
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Zbierz wszystkie tweety z threada
            tweet_elements = soup.find_all(attrs={'data-testid': 'tweet'})
            thread_parts = []
            
            for element in tweet_elements:
                tweet_content = element.find(attrs={'data-testid': 'tweetText'})
                if tweet_content:
                    text = tweet_content.get_text(strip=True)
                    if text and text not in thread_parts:
                        thread_parts.append(text)
            
            if len(thread_parts) > 1:
                thread_text = '\n\n'.join(thread_parts)
                self.logger.info(f"[Strategy] Zebrano thread: {len(thread_parts)} części")
                return f"Thread ({len(thread_parts)} części):\n\n{thread_text}"
            
        except Exception as e:
            self.logger.warning(f"[Strategy] Błąd zbierania threada: {e}")
        
        return None

    def _get_alternative_content(self, url: str) -> Optional[Dict]:
        """Próba alternatywnych źródeł treści"""
        try:
            # 1. Sprawdź Archive.org
            wayback_content = self._check_wayback_machine(url)
            if wayback_content:
                return {
                    'content': wayback_content,
                    'source': 'wayback_machine',
                    'quality': 'medium',
                    'confidence': 0.5,
                    'url': url
                }
            
            # 2. Dla YouTube - spróbuj pobrać metadane
            if 'youtube.com' in url or 'youtu.be' in url:
                youtube_info = self._get_youtube_info(url)
                if youtube_info:
                    return {
                        'content': youtube_info,
                        'source': 'youtube_metadata',
                        'quality': 'medium',
                        'confidence': 0.6,
                        'url': url
                    }
            
            # 3. Dla GitHub - użyj API
            if 'github.com' in url:
                github_info = self._get_github_info(url)
                if github_info:
                    return {
                        'content': github_info,
                        'source': 'github_api',
                        'quality': 'high',
                        'confidence': 0.8,
                        'url': url
                    }
            
        except Exception as e:
            self.logger.warning(f"[Strategy] Błąd alternatywnych źródeł: {e}")
        
        return None

    def _check_wayback_machine(self, url: str) -> Optional[str]:
        """Sprawdza Archive.org (placeholder)"""
        # Implementacja do Archive.org API
        return None

    def _get_youtube_info(self, url: str) -> Optional[str]:
        """Pobiera info o filmie YouTube z metadanych strony"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tytuł
            title_tag = soup.find('meta', attrs={'name': 'title'})
            title = title_tag.get('content', '') if title_tag else ''
            
            # Opis
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            description = desc_tag.get('content', '') if desc_tag else ''
            
            if title or description:
                return f"Film YouTube:\nTytuł: {title}\n\nOpis: {description}"
            
        except Exception as e:
            self.logger.warning(f"[Strategy] Błąd YouTube: {e}")
        
        return None

    def _get_github_info(self, url: str) -> Optional[str]:
        """Pobiera info z GitHub (placeholder dla API)"""
        try:
            # Parse URL to get owner/repo
            path_parts = urlparse(url).path.strip('/').split('/')
            if len(path_parts) >= 2:
                owner, repo = path_parts[0], path_parts[1]
                
                # Podstawowe info z strony
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Opis repo
                    desc_element = soup.find('p', class_='f4')
                    description = desc_element.get_text(strip=True) if desc_element else ''
                    
                    # README preview
                    readme_element = soup.find('div', class_='Box-body')
                    readme_preview = ''
                    if readme_element:
                        readme_text = readme_element.get_text(strip=True)
                        readme_preview = readme_text[:500] + '...' if len(readme_text) > 500 else readme_text
                    
                    if description or readme_preview:
                        return f"Repozytorium GitHub: {owner}/{repo}\n\nOpis: {description}\n\nREADME:\n{readme_preview}"
            
        except Exception as e:
            self.logger.warning(f"[Strategy] Błąd GitHub: {e}")
        
        return None

    def _enrich_tweet_context(self, tweet_text: str, url: str, tweet_data: Optional[Dict] = None) -> str:
        """Wzbogaca kontekst tweeta"""
        parts = [f"Tweet: {tweet_text}"]
        
        # Dodaj URL
        if url:
            domain = urlparse(url).netloc
            parts.append(f"Link: {url} (domena: {domain})")
        
        # Dodaj dodatkowe info jeśli dostępne
        if tweet_data:
            if tweet_data.get('author'):
                parts.append(f"Autor: {tweet_data['author']}")
            
            if tweet_data.get('timestamp'):
                parts.append(f"Data: {tweet_data['timestamp']}")
            
            if tweet_data.get('likes') or tweet_data.get('retweets'):
                engagement = f"Reakcje: {tweet_data.get('likes', 0)} lajków, {tweet_data.get('retweets', 0)} RT"
                parts.append(engagement)
        
        # Wykryj encje w tweecie
        entities = self._extract_entities(tweet_text)
        if entities:
            parts.append(f"Wykryte tematy: {', '.join(entities)}")
        
        # Kategoryzuj domenę
        if url:
            category = self._categorize_domain(url)
            if category:
                parts.append(f"Kategoria: {category}")
        
        return '\n'.join(parts)

    def _extract_entities(self, text: str) -> List[str]:
        """Prosta ekstrakcja encji (hashtagi, mentions, słowa kluczowe)"""
        entities = []
        
        # Hashtagi
        hashtags = re.findall(r'#\w+', text)
        entities.extend([tag.lower() for tag in hashtags])
        
        # Mentions
        mentions = re.findall(r'@\w+', text)
        entities.extend(mentions)
        
        # Słowa kluczowe techniczne
        tech_keywords = [
            'AI', 'ML', 'python', 'javascript', 'react', 'vue', 'angular',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'tensorflow',
            'pytorch', 'blockchain', 'crypto', 'nft', 'startup', 'fintech'
        ]
        
        text_lower = text.lower()
        for keyword in tech_keywords:
            if keyword.lower() in text_lower:
                entities.append(keyword)
        
        return list(set(entities))

    def _categorize_domain(self, url: str) -> Optional[str]:
        """Kategoryzuje domenę"""
        domain = urlparse(url).netloc.lower()
        
        categories = {
            'development': ['github.com', 'gitlab.com', 'stackoverflow.com', 'dev.to'],
            'documentation': ['docs.', 'documentation.', 'readthedocs.'],
            'research': ['arxiv.org', 'scholar.google', 'research.'],
            'news': ['techcrunch.com', 'arstechnica.com', 'wired.com'],
            'social': ['twitter.com', 'x.com', 'linkedin.com'],
            'video': ['youtube.com', 'vimeo.com'],
            'blog': ['medium.com', 'substack.com', 'blog.']
        }
        
        for category, domains in categories.items():
            if any(cat_domain in domain for cat_domain in domains):
                return category
        
        return 'other'

    def _get_cache_key(self, url: str, text: str) -> str:
        """Generuje klucz cache"""
        content = f"{url}:{text}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_processing_priority(self, url: str, tweet_text: str) -> int:
        """Zwraca priorytet przetwarzania (wyższy = ważniejszy)"""
        priority = 0
        domain = urlparse(url).netloc.lower()
        
        # Wysokie priorytety
        if any(prio_domain in domain for prio_domain in self.priority_domains):
            priority += 10
        
        # Thread bonus
        if self._is_thread_tweet(tweet_text, url):
            priority += 5
        
        # Długość tweeta
        if len(tweet_text) > 100:
            priority += 2
        
        # Hashtagi/mentions
        if re.search(r'[#@]\w+', tweet_text):
            priority += 1
        
        return priority

    def close(self):
        """Cleanup resources"""
        if hasattr(self.content_extractor, 'close'):
            self.content_extractor.close()