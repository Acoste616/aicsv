#!/usr/bin/env python3
"""
THREAD COLLECTOR
Klasa do zbierania i analizowania nitek tweetów (Twitter threads)

FUNKCJE:
1. Zbieranie pełnych nitek tweetów
2. Parsowanie struktury nitek
3. Ekstraktowanie wiedzy z nitek
4. Obsługa różnych metod pobierania (API/scraping)
"""

import re
import requests
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import time

class ThreadCollector:
    """
    Klasa do zbierania i analizowania nitek tweetów
    """
    
    # Wzorce do wykrywania numeracji nitek
    THREAD_NUMBER_PATTERNS = [
        r'(\d+)/(\d+)',           # "1/5", "2/5"
        r'(\d+)\.(\d+)',          # "1.5", "2.5"
        r'(\d+)\)',               # "1)", "2)"
        r'^(\d+)/',               # "1/" na początku
        r'^\d+\.',                # "1." na początku
        r'🧵.*?(\d+)',            # Emoji nitki z numerem
    ]
    
    # Wzorce strukturalne
    STRUCTURE_PATTERNS = {
        'introduction': r'(?i)(wprowadzenie|wstęp|zacznijmy|thread about|🧵)',
        'conclusion': r'(?i)(podsumowanie|wnioski|conclusion|końcowe|summary|to wrap up)',
        'list_item': r'(?i)(•|-)?\s*(\d+[\.)]\s*|[a-z][\.)]\s*)',
        'question': r'(?i)(dlaczego|jak|co|why|how|what|czy|whether)\??',
        'emphasis': r'(?i)(ważne|important|uwaga|note|remember|pamiętaj)',
        'source': r'(?i)(źródło|source|link|więcej|read more|h/t)'
    }
    
    def __init__(self, twitter_api_client=None, rate_limit_delay=1.0):
        """
        Inicjalizuje ThreadCollector
        
        Args:
            twitter_api_client: Opcjonalny klient API Twittera
            rate_limit_delay: Opóźnienie między requestami (sekundy)
        """
        self.logger = logging.getLogger(__name__)
        self.api_client = twitter_api_client
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        
        # Ustawienia dla web scrapingu (fallback)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def collect_thread(self, first_tweet_url: str) -> Dict[str, Any]:
        """
        Zbiera pełną nitkę rozpoczynającą się od podanego tweeta
        
        1. Znajdź wszystkie tweety w nitce:
           - Szukaj "2/", "3/" itd
           - Lub odpowiedzi tego samego autora
        2. Posortuj chronologicznie
        3. Połącz treści zachowując strukturę
        4. Wyodrębnij media z każdego tweeta
        
        Args:
            first_tweet_url: URL pierwszego tweeta w nitce
            
        Returns:
            Słownik z pełną analizą nitki
        """
        self.logger.info(f"Collecting thread starting from: {first_tweet_url}")
        
        try:
            # Parsuj URL i wyodrębnij informacje
            tweet_info = self._parse_tweet_url(first_tweet_url)
            if not tweet_info:
                self.logger.error(f"Could not parse tweet URL: {first_tweet_url}")
                return self._create_empty_thread_result(first_tweet_url)
            
            # Zbierz tweety w nitce
            thread_tweets = self._collect_thread_tweets(tweet_info)
            
            if not thread_tweets:
                self.logger.warning(f"No thread tweets found for: {first_tweet_url}")
                return self._create_empty_thread_result(first_tweet_url)
            
            # Posortuj chronologicznie
            sorted_tweets = self._sort_tweets_chronologically(thread_tweets)
            
            # Połącz treści
            combined_content = self._combine_thread_content(sorted_tweets)
            
            # Wyodrębnij wszystkie media
            all_media = self._extract_all_media(sorted_tweets)
            
            # Parsuj strukturę
            structure_analysis = self.parse_thread_structure(sorted_tweets)
            
            # Ekstraktuj wiedzę
            knowledge_extraction = self.extract_thread_knowledge(combined_content)
            
            # Stwórz pełny wynik
            thread_result = {
                'thread_url': first_tweet_url,
                'tweet_count': len(sorted_tweets),
                'author': tweet_info.get('author', 'unknown'),
                'combined_content': combined_content,
                'individual_tweets': [self._clean_tweet_data(tweet) for tweet in sorted_tweets],
                'all_media': all_media,
                'structure_analysis': structure_analysis,
                'knowledge_extraction': knowledge_extraction,
                'collection_timestamp': datetime.now().isoformat(),
                'collection_success': True
            }
            
            self.logger.info(f"Successfully collected thread with {len(sorted_tweets)} tweets")
            return thread_result
            
        except Exception as e:
            self.logger.error(f"Error collecting thread {first_tweet_url}: {e}")
            return self._create_empty_thread_result(first_tweet_url, error=str(e))
    
    def _parse_tweet_url(self, tweet_url: str) -> Optional[Dict[str, str]]:
        """Parsuje URL tweeta i wyodrębnia informacje"""
        try:
            # Obsługa różnych formatów URL Twittera
            patterns = [
                r'twitter\.com/([^/]+)/status/(\d+)',
                r'x\.com/([^/]+)/status/(\d+)',
                r't\.co/([a-zA-Z0-9]+)'  # Skrócone linki
            ]
            
            for pattern in patterns:
                match = re.search(pattern, tweet_url)
                if match:
                    if len(match.groups()) == 2:
                        username, tweet_id = match.groups()
                        return {
                            'username': username,
                            'tweet_id': tweet_id,
                            'original_url': tweet_url
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing tweet URL {tweet_url}: {e}")
            return None
    
    def _collect_thread_tweets(self, tweet_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Zbiera wszystkie tweety w nitce"""
        try:
            # Strategia 1: Użyj API jeśli dostępne
            if self.api_client:
                return self._collect_via_api(tweet_info)
            
            # Strategia 2: Web scraping (fallback)
            return self._collect_via_scraping(tweet_info)
            
        except Exception as e:
            self.logger.error(f"Error collecting thread tweets: {e}")
            return []
    
    def _collect_via_api(self, tweet_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Zbiera tweety przez API"""
        # To jest przykładowa implementacja - wymaga konkretnego API
        self.logger.info("Collecting via API (not implemented)")
        return []
    
    def _collect_via_scraping(self, tweet_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Zbiera tweety przez web scraping (uproszczona wersja)"""
        self.logger.info("Collecting via web scraping (simplified)")
        
        # To jest przykładowa implementacja
        # W rzeczywistości wymagałaby to bardziej zaawansowanego scrapingu
        
        # Symulujemy znalezienie nitek na podstawie wzorców numeracji
        sample_tweets = []
        
        # Dla celów demonstracyjnych zwracamy przykładowe dane
        base_content = f"Tweet from {tweet_info.get('username', 'user')}"
        
        for i in range(1, 4):  # Symulujemy 3-częściową nitkę
            tweet = {
                'id': f"{tweet_info.get('tweet_id', '12345')}{i}",
                'content': f"{base_content} - część {i}/3",
                'author': tweet_info.get('username', 'user'),
                'timestamp': datetime.now().isoformat(),
                'thread_position': f"{i}/3",
                'media': [],
                'urls': []
            }
            sample_tweets.append(tweet)
        
        return sample_tweets
    
    def _sort_tweets_chronologically(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sortuje tweety chronologicznie"""
        try:
            # Sortuj według timestamp jeśli dostępny
            if all('timestamp' in tweet for tweet in tweets):
                return sorted(tweets, key=lambda x: x['timestamp'])
            
            # Fallback: sortuj według pozycji w nitce
            def extract_thread_number(tweet):
                content = tweet.get('content', '')
                for pattern in self.THREAD_NUMBER_PATTERNS:
                    match = re.search(pattern, content)
                    if match:
                        try:
                            return int(match.group(1))
                        except:
                            continue
                return 999  # Na końcu jeśli nie ma numeru
            
            return sorted(tweets, key=extract_thread_number)
            
        except Exception as e:
            self.logger.error(f"Error sorting tweets: {e}")
            return tweets
    
    def _combine_thread_content(self, tweets: List[Dict[str, Any]]) -> str:
        """Łączy treści tweetów w jeden spójny tekst"""
        try:
            combined_parts = []
            
            for i, tweet in enumerate(tweets, 1):
                content = tweet.get('content', '')
                
                # Oczyść treść z numeracji nitki
                cleaned_content = content
                for pattern in self.THREAD_NUMBER_PATTERNS:
                    cleaned_content = re.sub(pattern, '', cleaned_content).strip()
                
                # Dodaj separator między tweetami
                if i > 1:
                    combined_parts.append('\n\n---\n\n')
                
                combined_parts.append(f"[Część {i}] {cleaned_content}")
            
            return ''.join(combined_parts)
            
        except Exception as e:
            self.logger.error(f"Error combining thread content: {e}")
            return ""
    
    def _extract_all_media(self, tweets: List[Dict[str, Any]]) -> Dict[str, List]:
        """Wyodrębnia wszystkie media z nitek"""
        all_media = {
            'images': [],
            'videos': [],
            'links': []
        }
        
        try:
            for tweet in tweets:
                media = tweet.get('media', [])
                urls = tweet.get('urls', [])
                
                for media_item in media:
                    media_type = media_item.get('type', '').lower()
                    media_url = media_item.get('url', '')
                    
                    if 'photo' in media_type or 'image' in media_type:
                        all_media['images'].append(media_url)
                    elif 'video' in media_type:
                        all_media['videos'].append(media_url)
                
                all_media['links'].extend(urls)
            
            # Usuń duplikaty
            for media_type in all_media:
                all_media[media_type] = list(set(all_media[media_type]))
            
            return all_media
            
        except Exception as e:
            self.logger.error(f"Error extracting media: {e}")
            return all_media
    
    def parse_thread_structure(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analizuj strukturę nitki:
        - Główne punkty
        - Podpunkty
        - Konkluzje
        - Przypisy/źródła
        """
        structure = {
            'introduction': None,
            'main_points': [],
            'conclusion': None,
            'sources': [],
            'questions': [],
            'emphasis_points': [],
            'total_tweets': len(tweets)
        }
        
        try:
            for i, tweet in enumerate(tweets):
                content = tweet.get('content', '')
                
                # Wykryj wprowadzenie (zazwyczaj pierwszy tweet)
                if i == 0 or re.search(self.STRUCTURE_PATTERNS['introduction'], content):
                    structure['introduction'] = content
                
                # Wykryj konkluzję (ostatni tweet lub zawierający słowa kluczowe)
                if i == len(tweets) - 1 or re.search(self.STRUCTURE_PATTERNS['conclusion'], content):
                    structure['conclusion'] = content
                
                # Wykryj główne punkty (listy, enumeracje)
                if re.search(self.STRUCTURE_PATTERNS['list_item'], content):
                    structure['main_points'].append({
                        'tweet_number': i + 1,
                        'content': content,
                        'type': 'list_item'
                    })
                
                # Wykryj pytania
                if re.search(self.STRUCTURE_PATTERNS['question'], content):
                    structure['questions'].append(content)
                
                # Wykryj punkty do podkreślenia
                if re.search(self.STRUCTURE_PATTERNS['emphasis'], content):
                    structure['emphasis_points'].append(content)
                
                # Wykryj źródła
                if re.search(self.STRUCTURE_PATTERNS['source'], content):
                    structure['sources'].append(content)
            
            # Analiza struktury
            structure['has_clear_structure'] = bool(
                structure['introduction'] and 
                structure['main_points'] and 
                structure['conclusion']
            )
            
            structure['thread_type'] = self._classify_thread_type(structure, tweets)
            
            return structure
            
        except Exception as e:
            self.logger.error(f"Error parsing thread structure: {e}")
            return structure
    
    def _classify_thread_type(self, structure: Dict, tweets: List[Dict]) -> str:
        """Klasyfikuje typ nitki"""
        content = ' '.join([tweet.get('content', '') for tweet in tweets]).lower()
        
        if any(keyword in content for keyword in ['tutorial', 'how to', 'guide', 'step']):
            return 'tutorial'
        elif any(keyword in content for keyword in ['opinion', 'think', 'believe', 'perspective']):
            return 'opinion'
        elif any(keyword in content for keyword in ['news', 'breaking', 'update', 'reported']):
            return 'news'
        elif len(structure.get('main_points', [])) > 2:
            return 'listicle'
        elif structure.get('questions'):
            return 'discussion'
        else:
            return 'general'
    
    def extract_thread_knowledge(self, thread_content: str) -> Dict[str, Any]:
        """
        Specjalna analiza dla nitek:
        - Często są to mini-artykuły
        - Mają strukturę: wstęp → rozwinięcie → wnioski
        """
        knowledge = {
            'key_topics': [],
            'main_arguments': [],
            'data_points': [],
            'actionable_insights': [],
            'mentioned_tools': [],
            'mentioned_people': [],
            'hashtags': [],
            'content_length': len(thread_content),
            'reading_time_minutes': len(thread_content.split()) / 200,  # ~200 słów/min
        }
        
        try:
            # Wyodrębnij hashtagi
            knowledge['hashtags'] = re.findall(r'#\w+', thread_content)
            
            # Wyodrębnij wzmianki o osobach
            knowledge['mentioned_people'] = re.findall(r'@\w+', thread_content)
            
            # Wykryj narzędzia/technologie (uproszczone)
            tools_pattern = r'\b(Python|JavaScript|React|API|GitHub|Docker|AI|ML|ChatGPT|GPT|LLM)\b'
            knowledge['mentioned_tools'] = list(set(re.findall(tools_pattern, thread_content, re.IGNORECASE)))
            
            # Wykryj liczby i dane (mogą być ważne)
            numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', thread_content)
            knowledge['data_points'] = list(set(numbers))
            
            # Wykryj kluczowe tematy (słowa powtarzające się)
            words = re.findall(r'\b[a-zA-Z]{4,}\b', thread_content.lower())
            word_freq = {}
            for word in words:
                if word not in ['that', 'this', 'with', 'from', 'they', 'have', 'will', 'been', 'were']:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Top 5 najczęstszych słów jako kluczowe tematy
            knowledge['key_topics'] = [
                word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # Wykryj zdania z akcentem (duże litery, wykrzykniki)
            emphasis_sentences = re.findall(r'[A-Z][^.!?]*[!]{1,3}', thread_content)
            knowledge['actionable_insights'] = emphasis_sentences[:3]  # Max 3
            
            # Klasyfikuj poziom trudności
            advanced_words = ['algorithm', 'implementation', 'architecture', 'optimization', 'scalability']
            knowledge['technical_level'] = 'advanced' if any(word in thread_content.lower() for word in advanced_words) else 'intermediate'
            
            return knowledge
            
        except Exception as e:
            self.logger.error(f"Error extracting thread knowledge: {e}")
            return knowledge
    
    def _clean_tweet_data(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """Czyści dane tweeta pozostawiając tylko najważniejsze informacje"""
        return {
            'id': tweet.get('id'),
            'content': tweet.get('content'),
            'author': tweet.get('author'),
            'timestamp': tweet.get('timestamp'),
            'thread_position': tweet.get('thread_position'),
            'media_count': len(tweet.get('media', [])),
            'urls_count': len(tweet.get('urls', []))
        }
    
    def _create_empty_thread_result(self, url: str, error: str = None) -> Dict[str, Any]:
        """Tworzy pusty wynik dla przypadków błędów"""
        return {
            'thread_url': url,
            'tweet_count': 0,
            'author': 'unknown',
            'combined_content': '',
            'individual_tweets': [],
            'all_media': {'images': [], 'videos': [], 'links': []},
            'structure_analysis': {},
            'knowledge_extraction': {},
            'collection_timestamp': datetime.now().isoformat(),
            'collection_success': False,
            'error': error
        }
    
    def get_thread_summary(self, thread_result: Dict[str, Any]) -> str:
        """Generuje krótkie podsumowanie nitki"""
        if not thread_result.get('collection_success'):
            return "Nie udało się zebrać nitki"
        
        tweet_count = thread_result.get('tweet_count', 0)
        author = thread_result.get('author', 'unknown')
        thread_type = thread_result.get('structure_analysis', {}).get('thread_type', 'general')
        key_topics = thread_result.get('knowledge_extraction', {}).get('key_topics', [])
        
        summary = f"Nitka {author} ({tweet_count} tweetów, typ: {thread_type})"
        if key_topics:
            summary += f" | Tematy: {', '.join(key_topics[:3])}"
        
        return summary


# Przykład użycia i testy
if __name__ == "__main__":
    # Skonfiguruj logging
    logging.basicConfig(level=logging.INFO)
    
    # Stwórz kolektor
    collector = ThreadCollector()
    
    # Test z przykładowym URL
    test_url = "https://twitter.com/user/status/123456789"
    
    print("=== TEST THREAD COLLECTOR ===")
    print(f"Testing with URL: {test_url}")
    
    # Zbierz nitkę
    result = collector.collect_thread(test_url)
    
    # Wyświetl wyniki
    print(f"\nResults:")
    print(f"Success: {result['collection_success']}")
    print(f"Tweet count: {result['tweet_count']}")
    print(f"Author: {result['author']}")
    
    if result['collection_success']:
        summary = collector.get_thread_summary(result)
        print(f"Summary: {summary}")
        
        print(f"\nStructure analysis:")
        structure = result['structure_analysis']
        print(f"- Type: {structure.get('thread_type', 'unknown')}")
        print(f"- Has clear structure: {structure.get('has_clear_structure', False)}")
        print(f"- Main points: {len(structure.get('main_points', []))}")
        
        print(f"\nKnowledge extraction:")
        knowledge = result['knowledge_extraction']
        print(f"- Key topics: {knowledge.get('key_topics', [])}")
        print(f"- Technical level: {knowledge.get('technical_level', 'unknown')}")
        print(f"- Reading time: {knowledge.get('reading_time_minutes', 0):.1f} min")