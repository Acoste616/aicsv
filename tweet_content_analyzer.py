import re
import requests
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs
import logging

# Try to import OCR libraries (optional dependencies)
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("OCR libraries not available. Install pillow and pytesseract for image text extraction.")

class TweetContentAnalyzer:
    """Analizator treści tweetów z zaawansowanymi funkcjami wykrywania typów treści"""
    
    # Regex patterns dla wykrywania numeracji nitek
    THREAD_PATTERNS = [
        r'(\d+)[/.](\d+)',  # Numeracja typu "1/5" lub "1.5"
        r'🧵',              # Emoji nitki
        r'Thread:',         # Słowo "Thread:"
        r'THREAD',          # Słowo "THREAD"
        r'\d+\)',           # Numeracja typu "1)"
        r'^\d+/',           # Numeracja na początku tweeta
    ]
    
    # Regex patterns dla wykrywania mediów
    MEDIA_PATTERNS = {
        'image_urls': r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)',
        'video_urls': r'https?://[^\s]+\.(?:mp4|avi|mov|wmv|flv|webm)',
        'youtube_urls': r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)',
        'twitter_media': r'pic\.twitter\.com/[a-zA-Z0-9]+',
        'general_links': r'https?://[^\s]+',
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_tweet_type(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analizuje tweet i zwraca jego typy treści:
        - has_links: bool
        - has_images: bool 
        - has_video: bool
        - is_thread: bool (sprawdź czy ma "1/" lub "🧵")
        - is_quote_tweet: bool
        - is_reply: bool
        - media_urls: lista URL do mediów
        - thread_id: ID jeśli to część nitki
        """
        
        # Pobierz tekst tweeta
        tweet_text = str(tweet_data.get('content', '')) + ' ' + str(tweet_data.get('rawContent', ''))
        tweet_url = tweet_data.get('url', '')
        
        analysis = {
            'has_links': False,
            'has_images': False,
            'has_video': False,
            'is_thread': False,
            'is_quote_tweet': False,
            'is_reply': False,
            'media_urls': [],
            'thread_id': None,
            'thread_position': None,
            'detected_patterns': []
        }
        
        # Sprawdź czy to część nitki
        analysis.update(self._detect_thread(tweet_text))
        
        # Sprawdź czy to odpowiedź
        analysis['is_reply'] = self._is_reply(tweet_data)
        
        # Sprawdź czy to quote tweet
        analysis['is_quote_tweet'] = self._is_quote_tweet(tweet_data)
        
        # Wykryj media
        media_analysis = self._detect_media(tweet_text, tweet_data)
        analysis.update(media_analysis)
        
        # Wykryj linki
        analysis['has_links'] = bool(re.search(self.MEDIA_PATTERNS['general_links'], tweet_text))
        
        return analysis
    
    def _detect_thread(self, tweet_text: str) -> Dict[str, Any]:
        """Wykrywa czy tweet jest częścią nitki"""
        thread_info = {
            'is_thread': False,
            'thread_position': None,
            'detected_patterns': []
        }
        
        for pattern in self.THREAD_PATTERNS:
            matches = re.findall(pattern, tweet_text, re.IGNORECASE)
            if matches:
                thread_info['is_thread'] = True
                thread_info['detected_patterns'].append(pattern)
                
                # Spróbuj wyodrębnić pozycję w nitce
                if '/' in pattern and matches:
                    try:
                        if isinstance(matches[0], tuple):
                            current, total = matches[0]
                            thread_info['thread_position'] = f"{current}/{total}"
                        else:
                            thread_info['thread_position'] = matches[0]
                    except:
                        pass
                break
        
        return thread_info
    
    def _is_reply(self, tweet_data: Dict[str, Any]) -> bool:
        """Sprawdza czy tweet jest odpowiedzią"""
        # Sprawdź różne możliwe pola wskazujące na odpowiedź
        reply_indicators = [
            tweet_data.get('inReplyToTweetId'),
            tweet_data.get('conversationId') != tweet_data.get('id'),
            tweet_data.get('replyTo'),
            '@' in str(tweet_data.get('content', ''))[:50]  # @ na początku tweeta
        ]
        
        return any(reply_indicators)
    
    def _is_quote_tweet(self, tweet_data: Dict[str, Any]) -> bool:
        """Sprawdza czy tweet jest quote tweetem"""
        quote_indicators = [
            tweet_data.get('quotedTweet'),
            tweet_data.get('isQuoteStatus'),
            'quotedStatusId' in tweet_data,
            'QT:' in str(tweet_data.get('content', ''))
        ]
        
        return any(quote_indicators)
    
    def _detect_media(self, tweet_text: str, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Wykrywa różne typy mediów w tweecie"""
        media_info = {
            'has_images': False,
            'has_video': False,
            'media_urls': []
        }
        
        # Sprawdź w tekście tweeta
        for media_type, pattern in self.MEDIA_PATTERNS.items():
            matches = re.findall(pattern, tweet_text, re.IGNORECASE)
            if matches:
                media_info['media_urls'].extend(matches)
                
                if 'image' in media_type or 'pic.twitter.com' in pattern:
                    media_info['has_images'] = True
                elif 'video' in media_type or 'youtube' in media_type:
                    media_info['has_video'] = True
        
        # Sprawdź w danych strukturalnych tweeta
        if 'media' in tweet_data:
            media_data = tweet_data['media']
            if isinstance(media_data, list):
                for media_item in media_data:
                    if isinstance(media_item, dict):
                        media_url = media_item.get('fullUrl') or media_item.get('url')
                        if media_url:
                            media_info['media_urls'].append(media_url)
                            
                            media_type = media_item.get('type', '').lower()
                            if 'photo' in media_type or 'image' in media_type:
                                media_info['has_images'] = True
                            elif 'video' in media_type:
                                media_info['has_video'] = True
        
        return media_info
    
    def extract_image_text(self, image_url: str) -> Optional[str]:
        """
        Używa OCR (pytesseract) lub Vision API do ekstrakcji tekstu z obrazu
        """
        if not OCR_AVAILABLE:
            self.logger.warning("OCR nie jest dostępne. Zainstaluj pillow i pytesseract.")
            return None
        
        try:
            # Pobierz obraz
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Otwórz obraz
            image = Image.open(requests.get(image_url, stream=True).raw)
            
            # Ekstraktuj tekst używając OCR
            extracted_text = pytesseract.image_to_string(image, lang='pol+eng')
            
            # Oczyść tekst
            cleaned_text = re.sub(r'\s+', ' ', extracted_text).strip()
            
            return cleaned_text if cleaned_text else None
            
        except Exception as e:
            self.logger.error(f"Błąd podczas ekstrakcji tekstu z obrazu {image_url}: {e}")
            return None
    
    def get_video_metadata(self, video_url: str) -> Dict[str, Any]:
        """
        Pobiera tytuł, opis, długość wideo
        """
        metadata = {
            'title': None,
            'description': None,
            'duration': None,
            'thumbnail': None,
            'platform': None
        }
        
        try:
            # Wykryj platformę
            if 'youtube.com' in video_url or 'youtu.be' in video_url:
                metadata['platform'] = 'youtube'
                return self._get_youtube_metadata(video_url)
            elif 'twitter.com' in video_url:
                metadata['platform'] = 'twitter'
                # Twitter video metadata byłyby pobierane przez Twitter API
            elif 'vimeo.com' in video_url:
                metadata['platform'] = 'vimeo'
                # Vimeo metadata
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania metadanych wideo {video_url}: {e}")
            return metadata
    
    def _get_youtube_metadata(self, youtube_url: str) -> Dict[str, Any]:
        """Pobiera metadane YouTube video (wymaga YouTube API key)"""
        # To jest przykładowa implementacja - wymaga YouTube API key
        metadata = {
            'title': None,
            'description': None,
            'duration': None,
            'thumbnail': None,
            'platform': 'youtube'
        }
        
        # Wyodrębnij video ID
        video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', youtube_url)
        if not video_id_match:
            return metadata
        
        video_id = video_id_match.group(1)
        
        # Tutaj byłoby wywołanie YouTube API
        # api_key = "YOUR_YOUTUBE_API_KEY"
        # api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=snippet,contentDetails"
        
        self.logger.info(f"YouTube video ID: {video_id} (API call nie jest zaimplementowane)")
        
        return metadata
    
    def collect_full_thread(self, first_tweet_url: str) -> List[Dict[str, Any]]:
        """
        Zbiera wszystkie tweety z nitki i łączy w jedną treść
        """
        thread_tweets = []
        
        try:
            # To jest przykładowa implementacja
            # W rzeczywistości wymagałoby to integracji z Twitter API lub scraperem
            
            self.logger.info(f"Zbieranie nitki rozpoczynającej się od: {first_tweet_url}")
            
            # Tutaj byłaby logika do:
            # 1. Pobrania tweeta początkowego
            # 2. Znalezienia wszystkich odpowiedzi od tego samego autora
            # 3. Uporządkowania ich chronologicznie
            # 4. Zwrócenia jako lista
            
            return thread_tweets
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zbierania nitki {first_tweet_url}: {e}")
            return []
    
    def get_quote_tweet_content(self, quote_tweet_id: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera treść cytowanego tweeta
        """
        try:
            # To jest przykładowa implementacja
            # W rzeczywistości wymagałoby to integracji z Twitter API lub bazą danych
            
            self.logger.info(f"Pobieranie cytowanego tweeta: {quote_tweet_id}")
            
            # Tutaj byłaby logika do pobrania tweeta o danym ID
            quoted_content = {
                'id': quote_tweet_id,
                'content': None,
                'author': None,
                'created_at': None,
                'url': f"https://twitter.com/i/status/{quote_tweet_id}"
            }
            
            return quoted_content
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania cytowanego tweeta {quote_tweet_id}: {e}")
            return None
    
    def get_comprehensive_tweet_analysis(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Przeprowadza pełną analizę tweeta łącząc wszystkie dostępne informacje
        """
        analysis = self.analyze_tweet_type(tweet_data)
        
        # Dodaj dodatkowe analizy
        if analysis['has_images'] and analysis['media_urls']:
            image_texts = []
            for url in analysis['media_urls']:
                if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    text = self.extract_image_text(url)
                    if text:
                        image_texts.append(text)
            analysis['extracted_image_texts'] = image_texts
        
        if analysis['has_video'] and analysis['media_urls']:
            video_metadata = []
            for url in analysis['media_urls']:
                if 'youtube' in url or any(ext in url.lower() for ext in ['.mp4', '.avi', '.mov']):
                    metadata = self.get_video_metadata(url)
                    if metadata:
                        video_metadata.append(metadata)
            analysis['video_metadata'] = video_metadata
        
        return analysis


# Przykład użycia
if __name__ == "__main__":
    analyzer = TweetContentAnalyzer()
    
    # Przykładowe dane tweeta
    sample_tweet = {
        'content': 'To jest pierwsza część mojej nitki o AI 1/5 🧵',
        'url': 'https://twitter.com/user/status/123456789',
        'media': [
            {'type': 'photo', 'fullUrl': 'https://pbs.twimg.com/media/example.jpg'}
        ]
    }
    
    # Przeprowadź analizę
    result = analyzer.analyze_tweet_type(sample_tweet)
    print("Analiza tweeta:")
    print(json.dumps(result, indent=2, ensure_ascii=False))