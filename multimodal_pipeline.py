#!/usr/bin/env python3
"""
MULTIMODAL KNOWLEDGE PIPELINE
Kompleksowy pipeline do przetwarzania treści multimodalnych z tweetów

KOMPONENTY:
1. TweetContentAnalyzer - analiza typów treści
2. ContentExtractor - ekstraktowanie treści z linków  
3. ImageContentExtractor - analiza obrazów i OCR
4. ThreadCollector - zbieranie nitek
5. VideoAnalyzer - analiza wideo
6. MultimodalKnowledgePipeline - główny orchestrator
"""

import logging
import json
import re
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import concurrent.futures
from urllib.parse import urlparse

# Importy z naszych modułów
try:
    from tweet_content_analyzer import TweetContentAnalyzer
    from content_extractor import ContentExtractor
    from thread_collector import ThreadCollector
    from fixed_content_processor import FixedContentProcessor
except ImportError as e:
    logging.warning(f"Import error: {e}. Some components may not be available.")

# Próba importu bibliotek do OCR i przetwarzania obrazów
try:
    import pytesseract
    from PIL import Image
    import cv2
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("OCR libraries not available. Install pillow, pytesseract, opencv-python for image processing.")

# Próba importu bibliotek do wideo
try:
    import yt_dlp
    VIDEO_PROCESSING_AVAILABLE = True
except ImportError:
    VIDEO_PROCESSING_AVAILABLE = False
    logging.warning("Video processing libraries not available. Install yt-dlp for video analysis.")


class ImageContentExtractor:
    """Klasa do ekstraktowania treści z obrazów"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Wzorce do klasyfikacji typów obrazów
        self.image_type_patterns = {
            'code_screenshot': [
                r'import\s+\w+', r'def\s+\w+\(', r'class\s+\w+', r'function\s+\w+\(',
                r'console\.log', r'print\(', r'return\s+', r'if\s+\w+\s*[==<>]',
                r'var\s+\w+', r'let\s+\w+', r'const\s+\w+'
            ],
            'infographic': [
                r'\d+%', r'\$\d+', r'\d+\s*(million|billion|thousand)',
                r'chart|graph|statistics|data|survey|report'
            ],
            'tutorial_steps': [
                r'step\s+\d+', r'\d+\.\s+', r'first|second|third|next|then|finally',
                r'click|select|choose|navigate|open|close'
            ],
            'social_media_post': [
                r'@\w+', r'#\w+', r'like|share|comment|follow|retweet'
            ],
            'document': [
                r'page\s+\d+', r'chapter\s+\d+', r'section\s+\d+',
                r'table of contents|index|bibliography|references'
            ]
        }
    
    def extract_text_from_image(self, image_url: str) -> Optional[str]:
        """Ekstraktuje tekst z obrazu używając OCR"""
        if not OCR_AVAILABLE:
            self.logger.warning("OCR not available")
            return None
        
        try:
            # Pobierz obraz
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Otwórz obraz z PIL
            image = Image.open(requests.get(image_url, stream=True).raw)
            
            # Wykonaj OCR
            extracted_text = pytesseract.image_to_string(image, lang='pol+eng')
            
            # Oczyść tekst
            cleaned_text = re.sub(r'\s+', ' ', extracted_text).strip()
            
            if len(cleaned_text) < 10:  # Zbyt krótki tekst prawdopodobnie błędny
                return None
                
            return cleaned_text
            
        except Exception as e:
            self.logger.error(f"Error extracting text from image {image_url}: {e}")
            return None
    
    def analyze_image_type(self, image_url: str, extracted_text: str = None) -> str:
        """Analizuje typ obrazu na podstawie ekstraktowanego tekstu"""
        if not extracted_text:
            extracted_text = self.extract_text_from_image(image_url)
        
        if not extracted_text:
            return 'unknown'
        
        text_lower = extracted_text.lower()
        
        # Sprawdź każdy typ obrazu
        for image_type, patterns in self.image_type_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, text_lower, re.IGNORECASE))
            if matches >= 2:  # Jeśli pasuje do 2+ wzorców danego typu
                return image_type
        
        # Fallback classification
        if any(keyword in text_lower for keyword in ['import', 'def', 'function', 'console']):
            return 'code_screenshot'
        elif any(char.isdigit() for char in extracted_text) and '%' in extracted_text:
            return 'infographic'
        else:
            return 'general'
    
    def get_enhanced_image_analysis(self, image_url: str) -> Dict[str, Any]:
        """Pełna analiza obrazu"""
        try:
            extracted_text = self.extract_text_from_image(image_url)
            image_type = self.analyze_image_type(image_url, extracted_text)
            
            analysis = {
                'url': image_url,
                'extracted_text': extracted_text,
                'image_type': image_type,
                'text_length': len(extracted_text) if extracted_text else 0,
                'has_code': bool(extracted_text and any(
                    keyword in extracted_text.lower() 
                    for keyword in ['import', 'def', 'function', 'class', 'var', 'let']
                )),
                'has_data': bool(extracted_text and re.search(r'\d+[%$]|\d+\s*(million|billion)', extracted_text)),
                'processing_timestamp': datetime.now().isoformat(),
                'processing_success': extracted_text is not None
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in enhanced image analysis: {e}")
            return {
                'url': image_url,
                'extracted_text': None,
                'image_type': 'error',
                'processing_success': False,
                'error': str(e)
            }


class VideoAnalyzer:
    """Klasa do analizy metadanych wideo"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_metadata(self, video_url: str) -> Dict[str, Any]:
        """Pobiera metadane wideo"""
        try:
            if 'youtube.com' in video_url or 'youtu.be' in video_url:
                return self._get_youtube_metadata(video_url)
            elif 'twitter.com' in video_url or 'x.com' in video_url:
                return self._get_twitter_video_metadata(video_url)
            elif 'vimeo.com' in video_url:
                return self._get_vimeo_metadata(video_url)
            else:
                return self._get_generic_video_metadata(video_url)
                
        except Exception as e:
            self.logger.error(f"Error getting video metadata for {video_url}: {e}")
            return {
                'url': video_url,
                'title': None,
                'description': None,
                'duration': None,
                'platform': 'unknown',
                'error': str(e)
            }
    
    def _get_youtube_metadata(self, youtube_url: str) -> Dict[str, Any]:
        """Pobiera metadane YouTube używając yt-dlp"""
        if not VIDEO_PROCESSING_AVAILABLE:
            return {'url': youtube_url, 'platform': 'youtube', 'error': 'yt-dlp not available'}
        
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                
                return {
                    'url': youtube_url,
                    'title': info.get('title'),
                    'description': info.get('description', '')[:500],  # Ogranicz opis
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'upload_date': info.get('upload_date'),
                    'uploader': info.get('uploader'),
                    'platform': 'youtube',
                    'thumbnail': info.get('thumbnail'),
                    'tags': info.get('tags', [])[:10]  # Max 10 tagów
                }
                
        except Exception as e:
            self.logger.error(f"Error extracting YouTube metadata: {e}")
            return {'url': youtube_url, 'platform': 'youtube', 'error': str(e)}
    
    def _get_twitter_video_metadata(self, twitter_url: str) -> Dict[str, Any]:
        """Pobiera metadane wideo z Twittera (uproszczone)"""
        return {
            'url': twitter_url,
            'title': 'Twitter Video',
            'description': 'Video from Twitter',
            'platform': 'twitter',
            'note': 'Twitter video metadata requires special API access'
        }
    
    def _get_vimeo_metadata(self, vimeo_url: str) -> Dict[str, Any]:
        """Pobiera metadane Vimeo (uproszczone)"""
        return {
            'url': vimeo_url,
            'title': 'Vimeo Video',
            'description': 'Video from Vimeo',
            'platform': 'vimeo',
            'note': 'Vimeo metadata extraction not implemented'
        }
    
    def _get_generic_video_metadata(self, video_url: str) -> Dict[str, Any]:
        """Generyczne metadane dla innych platform"""
        return {
            'url': video_url,
            'title': f'Video from {urlparse(video_url).netloc}',
            'description': 'Generic video',
            'platform': 'other'
        }


class MultimodalKnowledgePipeline:
    """
    Główny pipeline do kompleksowego przetwarzania treści multimodalnych
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Inicjalizuj wszystkie komponenty
        try:
            self.tweet_analyzer = TweetContentAnalyzer()
            self.logger.info("TweetContentAnalyzer initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize TweetContentAnalyzer: {e}")
            self.tweet_analyzer = None
        
        try:
            self.content_extractor = ContentExtractor()
            self.logger.info("ContentExtractor initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize ContentExtractor: {e}")
            self.content_extractor = None
        
        self.image_extractor = ImageContentExtractor()
        self.thread_collector = ThreadCollector()
        self.video_analyzer = VideoAnalyzer()
        
        try:
            self.content_processor = FixedContentProcessor()
            self.logger.info("FixedContentProcessor initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize FixedContentProcessor: {e}")
            self.content_processor = None
        
        self.logger.info("MultimodalKnowledgePipeline initialized successfully")
    
    def process_tweet_complete(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Kompletne przetwarzanie tweeta ze wszystkimi typami treści
        
        Args:
            tweet_data: Dane tweeta (musi zawierać 'url' i 'content')
            
        Returns:
            Pełna analiza ze zsyntetyzowaną wiedzą
        """
        self.logger.info(f"Starting complete processing for tweet: {tweet_data.get('url', 'unknown')}")
        
        try:
            # Krok 1: Analizuj typ treści
            content_types = self._analyze_content_types(tweet_data)
            
            # Krok 2: Ekstraktuj treści odpowiednio do typu
            extracted_contents = self._extract_all_contents(tweet_data, content_types)
            
            # Krok 3: Syntezuj wiedzę ze WSZYSTKICH źródeł
            knowledge = self.synthesize_knowledge(extracted_contents, tweet_data)
            
            # Krok 4: Dodaj metadane procesu
            knowledge['processing_metadata'] = {
                'timestamp': datetime.now().isoformat(),
                'content_types_detected': content_types,
                'sources_processed': list(extracted_contents.keys()),
                'processing_success': True
            }
            
            self.logger.info("Complete processing finished successfully")
            return knowledge
            
        except Exception as e:
            self.logger.error(f"Error in complete processing: {e}")
            return {
                'error': str(e),
                'processing_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'processing_success': False
                }
            }
    
    def _analyze_content_types(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analizuje typy treści w tweecie"""
        if not self.tweet_analyzer:
            self.logger.warning("TweetContentAnalyzer not available, using fallback")
            return self._fallback_content_analysis(tweet_data)
        
        try:
            return self.tweet_analyzer.analyze_tweet_type(tweet_data)
        except Exception as e:
            self.logger.error(f"Error in content type analysis: {e}")
            return self._fallback_content_analysis(tweet_data)
    
    def _fallback_content_analysis(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analiza typów treści"""
        content = tweet_data.get('content', '') + ' ' + tweet_data.get('rawContent', '')
        
        return {
            'has_links': 'http' in content,
            'has_images': 'pic.twitter.com' in content or any(ext in content for ext in ['.jpg', '.png', '.gif']),
            'has_video': 'video' in content.lower() or 'youtube' in content,
            'is_thread': any(pattern in content for pattern in ['1/', '🧵', 'thread']),
            'is_quote_tweet': False,
            'is_reply': '@' in content[:50],
            'media_urls': re.findall(r'https?://[^\s]+', content)
        }
    
    def _extract_all_contents(self, tweet_data: Dict[str, Any], content_types: Dict[str, Any]) -> Dict[str, Any]:
        """Ekstraktuje wszystkie dostępne treści równolegle"""
        extracted_contents = {
            'tweet_text': tweet_data.get('content', '') + ' ' + tweet_data.get('rawContent', '')
        }
        
        # Lista zadań do wykonania równolegle
        tasks = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # Artykuły z linków
            if content_types.get('has_links') and content_types.get('media_urls'):
                for link in content_types['media_urls']:
                    if self._is_article_link(link):
                        task = executor.submit(self._extract_article_content, link)
                        tasks.append(('article', link, task))
            
            # Obrazy
            if content_types.get('has_images') and content_types.get('media_urls'):
                for img_url in content_types['media_urls']:
                    if self._is_image_url(img_url):
                        task = executor.submit(self.image_extractor.get_enhanced_image_analysis, img_url)
                        tasks.append(('image', img_url, task))
            
            # Nitka
            if content_types.get('is_thread'):
                task = executor.submit(self.thread_collector.collect_thread, tweet_data.get('url', ''))
                tasks.append(('thread', 'main', task))
            
            # Wideo
            if content_types.get('has_video') and content_types.get('media_urls'):
                for video_url in content_types['media_urls']:
                    if self._is_video_url(video_url):
                        task = executor.submit(self.video_analyzer.get_metadata, video_url)
                        tasks.append(('video', video_url, task))
            
            # Zbierz wyniki
            for content_type, url, task in tasks:
                try:
                    result = task.result(timeout=30)  # 30 sekund timeout
                    if result:
                        extracted_contents.setdefault(f'{content_type}s', []).append(result)
                except concurrent.futures.TimeoutError:
                    self.logger.warning(f"Timeout processing {content_type}: {url}")
                except Exception as e:
                    self.logger.error(f"Error processing {content_type} {url}: {e}")
        
        return extracted_contents
    
    def _extract_article_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Ekstraktuje treść artykułu"""
        if not self.content_extractor:
            return None
        
        try:
            content = self.content_extractor.extract_content(url)
            return {
                'url': url,
                'content': content,
                'extraction_success': bool(content)
            }
        except Exception as e:
            self.logger.error(f"Error extracting article {url}: {e}")
            return None
    
    def _is_article_link(self, url: str) -> bool:
        """Sprawdza czy link to artykuł"""
        article_domains = ['medium.com', 'dev.to', 'github.com', 'stackoverflow.com', 'blog', 'news', 'article']
        return any(domain in url.lower() for domain in article_domains)
    
    def _is_image_url(self, url: str) -> bool:
        """Sprawdza czy URL to obraz"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        return any(ext in url.lower() for ext in image_extensions) or 'pic.twitter.com' in url
    
    def _is_video_url(self, url: str) -> bool:
        """Sprawdza czy URL to wideo"""
        video_platforms = ['youtube.com', 'youtu.be', 'vimeo.com', 'video.', '.mp4', '.avi']
        return any(platform in url.lower() for platform in video_platforms)
    
    def synthesize_knowledge(self, extracted_contents: Dict[str, Any], tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Syntezuje wiedzę ze WSZYSTKICH źródeł używając LLM
        """
        self.logger.info("Starting knowledge synthesis")
        
        try:
            # Przygotuj dane do syntezy
            synthesis_data = self._prepare_synthesis_data(extracted_contents, tweet_data)
            
            # Użyj FixedContentProcessor do stworzenia multimodalnego promptu
            if self.content_processor:
                try:
                    analysis = self.content_processor.process_multimodal_item(tweet_data, synthesis_data)
                    if analysis:
                        return self._enhance_analysis(analysis, extracted_contents)
                except Exception as e:
                    self.logger.error(f"Error in multimodal processing: {e}")
            
            # Fallback synthesis
            return self._fallback_synthesis(extracted_contents, tweet_data)
            
        except Exception as e:
            self.logger.error(f"Error in knowledge synthesis: {e}")
            return self._fallback_synthesis(extracted_contents, tweet_data)
    
    def _prepare_synthesis_data(self, extracted_contents: Dict[str, Any], tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Przygotowuje dane do syntezy w formacie oczekiwanym przez FixedContentProcessor"""
        synthesis_data = {}
        
        # Tweet text
        synthesis_data['tweet_text'] = extracted_contents.get('tweet_text', '')
        
        # Articles
        if 'articles' in extracted_contents:
            synthesis_data['article_contents'] = [
                article.get('content', '') for article in extracted_contents['articles']
                if article and article.get('content')
            ]
        
        # Images
        if 'images' in extracted_contents:
            synthesis_data['image_texts'] = [
                img.get('extracted_text', '') for img in extracted_contents['images']
                if img and img.get('extracted_text')
            ]
        
        # Videos
        if 'videos' in extracted_contents:
            synthesis_data['video_metadata'] = [
                {
                    'title': video.get('title', ''),
                    'description': video.get('description', ''),
                    'platform': video.get('platform', '')
                }
                for video in extracted_contents['videos']
                if video
            ]
        
        # Thread
        if 'threads' in extracted_contents and extracted_contents['threads']:
            thread = extracted_contents['threads'][0]  # Bierzemy pierwszą nitkę
            synthesis_data['thread_content'] = thread.get('combined_content', '')
        
        return synthesis_data
    
    def _enhance_analysis(self, analysis: Dict[str, Any], extracted_contents: Dict[str, Any]) -> Dict[str, Any]:
        """Wzbogaca analizę o dodatkowe informacje z ekstraktowanych treści"""
        
        # Wzbogać extracted_from o rzeczywiste dane
        if 'extracted_from' in analysis:
            # Artykuły
            if 'articles' in extracted_contents:
                analysis['extracted_from']['articles'] = [
                    article.get('url', '') for article in extracted_contents['articles']
                    if article and article.get('url')
                ]
            
            # Obrazy
            if 'images' in extracted_contents:
                analysis['extracted_from']['images'] = [
                    img.get('url', '') for img in extracted_contents['images']
                    if img and img.get('url')
                ]
            
            # Wideo
            if 'videos' in extracted_contents:
                analysis['extracted_from']['videos'] = [
                    video.get('url', '') for video in extracted_contents['videos']
                    if video and video.get('url')
                ]
            
            # Długość nitki
            if 'threads' in extracted_contents and extracted_contents['threads']:
                thread = extracted_contents['threads'][0]
                analysis['extracted_from']['thread_length'] = thread.get('tweet_count', 0)
        
        # Wzbogać media_analysis o rzeczywiste dane
        if 'media_analysis' in analysis:
            # Obrazy
            if 'images' in extracted_contents:
                analysis['media_analysis']['images'] = []
                for img in extracted_contents['images']:
                    if img:
                        img_analysis = {
                            "type": img.get('image_type', 'unknown'),
                            "content": img.get('extracted_text', '')[:200],  # Ogranicz długość
                            "key_concepts": self._extract_key_concepts_from_text(img.get('extracted_text', ''))
                        }
                        analysis['media_analysis']['images'].append(img_analysis)
            
            # Wideo
            if 'videos' in extracted_contents:
                analysis['media_analysis']['videos'] = []
                for video in extracted_contents['videos']:
                    if video:
                        video_analysis = {
                            "platform": video.get('platform', 'unknown'),
                            "title": video.get('title', ''),
                            "key_topics": self._extract_key_concepts_from_text(
                                f"{video.get('title', '')} {video.get('description', '')}"
                            )
                        }
                        analysis['media_analysis']['videos'].append(video_analysis)
        
        # Wzbogać thread_summary jeśli jest nitka
        if 'threads' in extracted_contents and extracted_contents['threads'] and 'thread_summary' in analysis:
            thread = extracted_contents['threads'][0]
            structure = thread.get('structure_analysis', {})
            
            # Główne punkty z analizy struktury
            main_points = [point.get('content', '')[:100] for point in structure.get('main_points', [])]
            if main_points:
                analysis['thread_summary']['main_points'] = main_points
            
            # Wniosek
            if structure.get('conclusion'):
                analysis['thread_summary']['conclusion'] = structure['conclusion'][:200]
            
            # Ekspertyza autora (na podstawie długości i jakości nitki)
            expertise_level = self._assess_author_expertise(thread)
            analysis['thread_summary']['author_expertise'] = expertise_level
        
        # Dodaj statystyki treści (zachowaj dla kompatybilności)
        analysis['content_statistics'] = {
            'total_images': len(extracted_contents.get('images', [])),
            'total_videos': len(extracted_contents.get('videos', [])),
            'total_articles': len(extracted_contents.get('articles', [])),
            'total_threads': len(extracted_contents.get('threads', [])),
            'has_code': any(
                img.get('has_code', False) for img in extracted_contents.get('images', [])
            ),
            'has_data_visualizations': any(
                img.get('image_type') == 'infographic' for img in extracted_contents.get('images', [])
            )
        }
        
        # Dodaj surowe dane z ekstraktowania
        analysis['raw_extracted_contents'] = extracted_contents
        
        return analysis
    
    def _fallback_synthesis(self, extracted_contents: Dict[str, Any], tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback synthesis bez LLM - nowy format"""
        tweet_text = extracted_contents.get('tweet_text', '')
        
        # Określ content_type
        content_type = "mixed"
        if 'threads' in extracted_contents and extracted_contents['threads']:
            content_type = "thread"
        elif 'articles' in extracted_contents and extracted_contents['articles']:
            content_type = "article"
        elif any(key in extracted_contents for key in ['images', 'videos']):
            content_type = "multimedia"
        
        # Przygotuj extracted_from
        extracted_from = {
            "articles": [art.get('url', '') for art in extracted_contents.get('articles', [])],
            "images": [img.get('url', '') for img in extracted_contents.get('images', [])],
            "videos": [vid.get('url', '') for vid in extracted_contents.get('videos', [])],
            "thread_length": extracted_contents.get('threads', [{}])[0].get('tweet_count', 0) if extracted_contents.get('threads') else 0
        }
        
        # Przygotuj media_analysis
        media_analysis = {
            "images": [],
            "videos": []
        }
        
        for img in extracted_contents.get('images', []):
            if img:
                media_analysis['images'].append({
                    "type": img.get('image_type', 'unknown'),
                    "content": img.get('extracted_text', '')[:100],
                    "key_concepts": self._extract_key_concepts_from_text(img.get('extracted_text', ''))
                })
        
        for video in extracted_contents.get('videos', []):
            if video:
                media_analysis['videos'].append({
                    "platform": video.get('platform', 'unknown'),
                    "title": video.get('title', ''),
                    "key_topics": self._extract_key_concepts_from_text(video.get('title', ''))
                })
        
        return {
            'tweet_url': tweet_data.get('url', ''),
            'title': tweet_text[:50] + '...' if len(tweet_text) > 50 else tweet_text,
            'short_description': 'Automated analysis of multimodal tweet content',
            'detailed_analysis': f'Processed tweet with {len(extracted_contents)} content types',
            'category': 'Multimodal',
            'content_type': content_type,
            'tags': ['multimodal', 'automated'] + list(extracted_contents.keys()),
            'extracted_from': extracted_from,
            'knowledge': {
                'main_topic': 'Automated multimodal analysis',
                'key_insights': [f'Contains {len(extracted_contents)} types of content'],
                'code_snippets': [],
                'data_points': [],
                'visual_elements': []
            },
            'thread_summary': {
                'main_points': ['Fallback analysis'],
                'conclusion': 'Automated processing',
                'author_expertise': 'Unknown'
            },
            'media_analysis': media_analysis,
            'technical_level': 'unknown',
            'has_tutorial': 'tutorial' in tweet_text.lower(),
            'has_data': any(char.isdigit() for char in tweet_text),
            'fallback_synthesis': True,
            'raw_extracted_contents': extracted_contents
        }
    
    def _extract_key_concepts_from_text(self, text: str) -> List[str]:
        """Wyodrębnia kluczowe koncepcje z tekstu"""
        if not text:
            return []
        
        # Słowa techniczne i koncepcje
        tech_keywords = [
            'python', 'javascript', 'react', 'api', 'github', 'docker', 'ai', 'ml', 
            'chatgpt', 'gpt', 'llm', 'database', 'sql', 'nosql', 'cloud', 'aws',
            'microservices', 'devops', 'kubernetes', 'tensorflow', 'pytorch',
            'blockchain', 'cryptocurrency', 'web3', 'nft', 'defi'
        ]
        
        concepts = []
        text_lower = text.lower()
        
        # Znajdź techniczne słowa kluczowe
        for keyword in tech_keywords:
            if keyword in text_lower:
                concepts.append(keyword.upper())
        
        # Znajdź wzorce programistyczne
        if re.search(r'import\s+\w+', text_lower):
            concepts.append('Import')
        if re.search(r'def\s+\w+', text_lower):
            concepts.append('Function')
        if re.search(r'class\s+\w+', text_lower):
            concepts.append('Class')
        if re.search(r'async\s+', text_lower):
            concepts.append('Async')
        
        # Znajdź liczby i metryki
        if re.search(r'\d+%', text):
            concepts.append('Percentage')
        if re.search(r'\$\d+', text):
            concepts.append('Price')
        
        return list(set(concepts))[:5]  # Max 5 konceptów
    
    def _assess_author_expertise(self, thread: Dict[str, Any]) -> str:
        """Ocenia ekspertyzę autora na podstawie nitki"""
        if not thread:
            return "Nieznana"
        
        tweet_count = thread.get('tweet_count', 0)
        combined_content = thread.get('combined_content', '')
        knowledge = thread.get('knowledge_extraction', {})
        
        # Czynniki oceny ekspertyzy
        expertise_score = 0
        
        # Długość nitki (dłuższe nitki = więcej wysiłku)
        if tweet_count >= 10:
            expertise_score += 3
        elif tweet_count >= 5:
            expertise_score += 2
        elif tweet_count >= 3:
            expertise_score += 1
        
        # Techniczne pojęcia
        tech_tools = knowledge.get('mentioned_tools', [])
        if len(tech_tools) >= 3:
            expertise_score += 2
        elif len(tech_tools) >= 1:
            expertise_score += 1
        
        # Dane liczbowe
        data_points = knowledge.get('data_points', [])
        if len(data_points) >= 3:
            expertise_score += 2
        
        # Długość treści
        if len(combined_content) > 1000:
            expertise_score += 2
        elif len(combined_content) > 500:
            expertise_score += 1
        
        # Klasyfikacja
        if expertise_score >= 7:
            return "Ekspert - szczegółowa analiza z danymi i narzędziami"
        elif expertise_score >= 5:
            return "Zaawansowany - dobra znajomość tematu"
        elif expertise_score >= 3:
            return "Średnio zaawansowany - podstawowa wiedza"
        else:
            return "Początkujący - ogólne informacje"
    
    def get_processing_summary(self, result: Dict[str, Any]) -> str:
        """Generuje podsumowanie przetwarzania"""
        if not result.get('processing_metadata', {}).get('processing_success', False):
            return "Processing failed"
        
        title = result.get('title', 'Unknown')
        content_type = result.get('content_type', 'unknown')
        
        # Statystyki z extracted_from
        extracted_from = result.get('extracted_from', {})
        sources_info = []
        if extracted_from.get('articles'):
            sources_info.append(f"{len(extracted_from['articles'])} articles")
        if extracted_from.get('images'):
            sources_info.append(f"{len(extracted_from['images'])} images")
        if extracted_from.get('videos'):
            sources_info.append(f"{len(extracted_from['videos'])} videos")
        if extracted_from.get('thread_length', 0) > 1:
            sources_info.append(f"thread({extracted_from['thread_length']})")
        
        sources_text = ", ".join(sources_info) if sources_info else "tweet only"
        
        return f"[{content_type.upper()}] {title[:30]}... | Sources: {sources_text}"


# Przykład użycia i testy
if __name__ == "__main__":
    # Skonfiguruj logging
    logging.basicConfig(level=logging.INFO)
    
    # Stwórz pipeline
    pipeline = MultimodalKnowledgePipeline()
    
    # Test z przykładowym tweetem
    test_tweet = {
        'url': 'https://twitter.com/user/status/123456789',
        'content': 'Check out this amazing tutorial on building RAG systems! 🧵 1/5',
        'rawContent': 'https://example.com/article pic.twitter.com/example123',
        'media': [
            {'type': 'photo', 'fullUrl': 'https://pbs.twimg.com/media/example.jpg'}
        ]
    }
    
    print("=== TEST MULTIMODAL PIPELINE ===")
    print(f"Processing tweet: {test_tweet['url']}")
    
    # Przetwórz tweet
    result = pipeline.process_tweet_complete(test_tweet)
    
    # Wyświetl wyniki
    if result.get('processing_metadata', {}).get('processing_success'):
        print(f"\n✅ Processing successful!")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Category: {result.get('category', 'N/A')}")
        print(f"Content types: {result.get('content_types', [])}")
        print(f"Key insights: {result.get('key_insights', [])}")
        
        summary = pipeline.get_processing_summary(result)
        print(f"Summary: {summary}")
        
        # Pokaż statystyki
        stats = result.get('content_statistics', {})
        if stats:
            print(f"\nContent Statistics:")
            for key, value in stats.items():
                print(f"- {key}: {value}")
    else:
        print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
    
    print(f"\nRaw result keys: {list(result.keys())}")