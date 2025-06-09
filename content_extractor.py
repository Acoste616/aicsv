# content_extractor.py
import requests
from bs4 import BeautifulSoup
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import random

class ContentExtractor:
    """
    Zaawansowana klasa do ekstrakcji treści z mechanizmami anty-detekcji.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        self._setup_session()
        self.driver = self._init_selenium_driver()

    def _setup_session(self):
        """Konfiguruje sesję requests z realistycznymi headerami."""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,pl;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })

    def _init_selenium_driver(self):
        """Inicjalizuje sterownik z zaawansowanymi technikami anty-detekcji."""
        try:
            self.logger.info("[Selenium] Inicjalizacja sterownika Chrome z anty-detekcją...")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Anty-detekcja - zaawansowane
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            
            # Realistyczny user-agent z rotacją
            user_agent = random.choice(self.user_agents)
            chrome_options.add_argument(f"--user-agent={user_agent}")
            
            # Ukryj DevTools ale pozwól na JS
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--silent")
            chrome_options.add_argument("--disable-logging")
            
            # Optymalizacje dla JS-heavy stron
            prefs = {
                "profile.default_content_setting_values": {
                    "images": 2,  # Blokuj obrazy dla szybkości
                    "plugins": 2,
                    "popups": 2,
                    "geolocation": 2,
                    "notifications": 2,
                    "media_stream": 2,
                },
                "profile.managed_default_content_settings": {
                    "images": 2
                }
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Usuń flagi automatyzacji
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array")
            driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise")
            driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol")
            
            # Zwiększone timeouty dla JS-heavy stron
            driver.set_page_load_timeout(60)  # Zwiększone z 45 do 60
            driver.implicitly_wait(15)        # Zwiększone z 10 do 15
            
            self.logger.info("[Selenium] Sterownik Chrome z anty-detekcją gotowy.")
            return driver
            
        except Exception as e:
            self.logger.error(f"[Selenium] KRYTYCZNY BŁĄD: {e}")
            return None

    def _get_final_url(self, url: str) -> str:
        """Rozwiązuje przekierowania z inteligentnym czekaniem na JS."""
        if not self.driver:
            self.logger.error("[Selenium] Sterownik niedostępny")
            return url
            
        try:
            self.logger.info(f"[Selenium] Ładowanie URL: {url}")
            
            # Rotuj user-agent przy każdym żądaniu
            new_ua = random.choice(self.user_agents)
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": new_ua})
            
            # Losowe opóźnienie przed ładowaniem
            time.sleep(random.uniform(2, 4))
            
            self.driver.get(url)
            
            # Zwiększone czekanie z 20 do 30 sekund
            wait = WebDriverWait(self.driver, 30)
            
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                self.logger.info("[Selenium] Body załadowane")
            except TimeoutException:
                self.logger.warning("[Selenium] Timeout na body - kontynuuję")
            
            # Specjalne czekanie dla różnych typów stron
            if 'twitter.com' in url or 'x.com' in url:
                self._wait_for_twitter_content(wait)
            elif 'openai.com' in url:
                self._wait_for_openai_content(wait)
            else:
                # Ogólne czekanie na JS
                self._wait_for_js_content(wait)
            
            # Dodatkowe czekanie i symulacja zachowania
            time.sleep(random.uniform(3, 7))
            
            # Sprawdź czy strona jest w pełni załadowana
            self._check_page_readiness()
            
            # Symuluj naturalne zachowanie użytkownika
            self._simulate_user_behavior()
            
            final_url = self.driver.current_url
            if url != final_url:
                self.logger.info(f"[Selenium] Rozwinięto: {url} -> {final_url}")
                
            return final_url
            
        except Exception as e:
            self.logger.error(f"[Selenium] Błąd: {e}")
            return url

    def _wait_for_twitter_content(self, wait):
        """Specjalne czekanie dla Twitter/X."""
        self.logger.info("[Twitter] Czekam na załadowanie tweeta...")
        try:
            # Czekaj na jeden z możliwych selektorów Twitter
            selectors_to_try = [
                "article[data-testid='tweet']",
                "[data-testid='tweetText']", 
                "[data-testid='tweet']",
                "article",
                "[role='article']"
            ]
            
            for selector in selectors_to_try:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    self.logger.info(f"[Twitter] Znaleziono element: {selector}")
                    break
                except TimeoutException:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"[Twitter] Nie znaleziono treści tweeta: {e}")

    def _wait_for_openai_content(self, wait):
        """Specjalne czekanie dla OpenAI."""
        self.logger.info("[OpenAI] Czekam na załadowanie treści...")
        try:
            # Możliwe selektory dla OpenAI
            selectors = [
                "article",
                "main",
                "[data-testid='article']",
                ".prose",
                ".blog-post"
            ]
            
            for selector in selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    self.logger.info(f"[OpenAI] Załadowano: {selector}")
                    break
                except TimeoutException:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"[OpenAI] Problem z ładowaniem: {e}")

    def _wait_for_js_content(self, wait):
        """Ogólne czekanie na załadowanie treści JS."""
        try:
            # Czekaj aż jQuery/React/Vue się załaduje (jeśli używane)
            self.driver.execute_script("""
                return new Promise((resolve) => {
                    if (document.readyState === 'complete') {
                        setTimeout(resolve, 1000);
                    } else {
                        window.addEventListener('load', () => setTimeout(resolve, 1000));
                    }
                });
            """)
        except Exception:
            pass

    def _check_page_readiness(self):
        """Sprawdza czy strona jest gotowa."""
        try:
            ready_state = self.driver.execute_script("return document.readyState")
            self.logger.info(f"[Selenium] Ready state: {ready_state}")
            
            if ready_state != 'complete':
                self.logger.warning("[Selenium] Strona nie w pełni załadowana")
                time.sleep(5)
                
            # Sprawdź ile elementów ma strona
            element_count = self.driver.execute_script("return document.querySelectorAll('*').length")
            self.logger.info(f"[Selenium] Elementy DOM: {element_count}")
            
        except Exception as e:
            self.logger.warning(f"[Selenium] Błąd sprawdzania gotowości: {e}")

    def _simulate_user_behavior(self):
        """Symuluje naturalne zachowanie użytkownika."""
        try:
            # Przewijanie strony w kilku krokach
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if total_height > 500:
                # Przewiń w dół po kawałku
                for i in range(3):
                    scroll_to = (total_height // 3) * (i + 1)
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                    time.sleep(random.uniform(0.5, 1.5))
                
                # Wróć na górę
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
        except Exception as e:
            self.logger.warning(f"[Selenium] Błąd symulacji: {e}")

    def _try_requests_fallback(self, url: str) -> str:
        """Fallback do requests dla prostych stron."""
        try:
            self.logger.info(f"[Fallback] Próba requests dla {url}")
            
            # Zaktualizuj headers z rotacją
            self.session.headers['User-Agent'] = random.choice(self.user_agents)
            self.session.headers['Referer'] = 'https://www.google.com/'
            
            response = self.session.get(url, timeout=20, allow_redirects=True)
            response.raise_for_status()
            
            if len(response.text) > 1000:  # Zwiększone z 500
                self.logger.info(f"[Fallback] Sukces requests - {len(response.text)} znaków")
                return response.text
                
        except Exception as e:
            self.logger.warning(f"[Fallback] Requests nie zadziałał: {e}")
        
        return ""

    def get_webpage_content(self, url: str) -> str:
        """Pobiera treść z wielopoziomową strategią."""
        final_url = ""
        page_source = ""
        
        try:
            # Strategia 1: Selenium z JS (główna)
            final_url = self._get_final_url(url)
            
            if self.driver and self.driver.current_url == final_url:
                page_source = self.driver.page_source
                self.logger.info(f"[Extractor] Pobrano źródło przez Selenium ({len(page_source)} znaków)")
            
            # Strategia 2: Fallback tylko jeśli bardzo mało
            if len(page_source) < 5000:  # Zwiększone z 1000
                self.logger.warning("[Extractor] Selenium dał mało treści, próbuję requests...")
                fallback_content = self._try_requests_fallback(final_url or url)
                if len(fallback_content) > len(page_source):
                    page_source = fallback_content
                    self.logger.info("[Extractor] Użyto fallback requests")
            
            if not page_source:
                self.logger.error("[Extractor] Brak treści ze wszystkich źródeł")
                return ""
            
            # Parsowanie z debug info
            soup = BeautifulSoup(page_source, 'lxml')
            self._debug_page_structure(soup, final_url)
            
            # Usuń niepotrzebne elementy
            for element in soup(["script", "style", "nav", "footer", "header", 
                               "aside", "form", "button", "noscript", "iframe", "svg"]):
                element.decompose()
            
            # Strategia ekstrakcji z priorytetem dla trudnych stron
            content = self._extract_content_smart(soup, final_url)
            
            # Specjalne przypadki dla bot-blocked stron
            if self._is_bot_blocked(content):
                self.logger.warning(f"[Extractor] Wykryto blokadę bota dla {final_url}")
                content = self._handle_bot_blocked_site(soup, final_url)
            
            # Ogranicz długość
            max_length = 4000
            if len(content) > max_length:
                content = content[:max_length] + "..."
            
            self.logger.info(f"[Extractor] Końcowy wynik: {len(content)} znaków z {final_url}")
            
            return content
            
        except Exception as e:
            self.logger.error(f"[Extractor] Błąd: {e}")
            return ""

    def _debug_page_structure(self, soup, url):
        """Debug - pokazuje strukturę strony."""
        try:
            title = soup.find('title')
            articles = soup.find_all('article')
            mains = soup.find_all('main')
            
            self.logger.info(f"[Debug] Strona: {url}")
            self.logger.info(f"[Debug] Tytuł: {title.get_text()[:100] if title else 'BRAK'}")
            self.logger.info(f"[Debug] Articles: {len(articles)}, Mains: {len(mains)}")
            
            # Dla Twitter/X sprawdź specjalne elementy
            if 'twitter.com' in url or 'x.com' in url:
                tweets = soup.find_all(attrs={'data-testid': 'tweet'})
                tweet_texts = soup.find_all(attrs={'data-testid': 'tweetText'})
                self.logger.info(f"[Debug] Twitter - tweets: {len(tweets)}, tweetTexts: {len(tweet_texts)}")
                
        except Exception as e:
            self.logger.warning(f"[Debug] Błąd debug: {e}")

    def _extract_content_smart(self, soup, url):
        """Inteligentna ekstrakcja z priorytetem dla różnych typów stron."""
        
        # Strategia 1: Spróbuj specjalizowane selektory najpierw
        if 'twitter.com' in url or 'x.com' in url:
            content = self._extract_twitter_content(soup)
            if content and len(content) > 100:
                return content
                
        elif 'openai.com' in url:
            content = self._extract_openai_content(soup)
            if content and len(content) > 100:
                return content
        
        # Strategia 2: Standardowe selektory
        content = self._extract_main_content(soup)
        if content and len(content) > 200:
            return content
            
        # Strategia 3: Fallback do wszystkiego
        return self._extract_all_text(soup)

    def _extract_twitter_content(self, soup):
        """Specjalna ekstrakcja dla Twitter/X."""
        self.logger.info("[Twitter] Próba ekstrakcji treści tweeta...")
        
        # Lista selektorów Twitter/X w kolejności priorytetu
        twitter_selectors = [
            ('[data-testid="tweetText"]', 'Tweet text'),
            ('article[data-testid="tweet"]', 'Tweet article'),
            ('[data-testid="tweet"]', 'Tweet element'),
            ('article', 'Article'),
            ('[role="article"]', 'Role article'),
            ('.tweet-text', 'Classic tweet text'),
            ('.TweetTextSize', 'Tweet text size')
        ]
        
        text_parts = []
        
        for selector, desc in twitter_selectors:
            try:
                elements = soup.select(selector)
                self.logger.info(f"[Twitter] {desc}: znaleziono {len(elements)} elementów")
                
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 20:  # Ignoruj krótkie fragmenty
                        text_parts.append(text)
                        self.logger.info(f"[Twitter] Dodano tekst: {text[:100]}...")
                        
            except Exception as e:
                self.logger.warning(f"[Twitter] Błąd z {selector}: {e}")
        
        if text_parts:
            result = '\n\n'.join(text_parts[:3])  # Max 3 fragmenty
            self.logger.info(f"[Twitter] Wyodrębniono {len(result)} znaków")
            return result
            
        return ""

    def _extract_openai_content(self, soup):
        """Specjalna ekstrakcja dla OpenAI."""
        self.logger.info("[OpenAI] Próba ekstrakcji treści...")
        
        openai_selectors = [
            ('article', 'Main article'),
            ('main', 'Main content'),
            ('.prose', 'Prose content'),
            ('.blog-post', 'Blog post'),
            ('[data-testid="article"]', 'Article testid'),
            ('.post-content', 'Post content'),
            ('.content', 'Generic content')
        ]
        
        for selector, desc in openai_selectors:
            try:
                elements = soup.select(selector)
                self.logger.info(f"[OpenAI] {desc}: znaleziono {len(elements)} elementów")
                
                if elements:
                    best_element = max(elements, key=lambda e: len(e.get_text(strip=True)))
                    text = best_element.get_text(separator='\n', strip=True)
                    
                    if len(text) > 200:
                        self.logger.info(f"[OpenAI] Sukces z {selector}: {len(text)} znaków")
                        return text
                        
            except Exception as e:
                self.logger.warning(f"[OpenAI] Błąd z {selector}: {e}")
        
        return ""

    def _is_bot_blocked(self, content):
        """Sprawdza czy strona blokuje boty."""
        if not content or len(content) < 500:
            bot_indicators = [
                'browser is not supported',
                'javascript is disabled',
                'enable javascript',
                'please switch to a supported browser',
                'twoja przeglądarka nie jest',
                'application error',
                'client-side exception',
                'access denied',
                'forbidden',
                'please enable cookies',
                'captcha'
            ]
            
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in bot_indicators)
        
        return False

    def _handle_bot_blocked_site(self, soup, url):
        """Obsługuje strony blokujące boty."""
        self.logger.info("[Handler] Próba obejścia blokady bota...")
        
        # Strategia 1: Spróbuj znaleźć ukrytą treść
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_title = soup.find('meta', attrs={'property': 'og:title'})
        meta_content = soup.find('meta', attrs={'property': 'og:description'})
        
        fallback_content = []
        
        if meta_title and meta_title.get('content'):
            fallback_content.append(f"Tytuł: {meta_title['content']}")
        
        if meta_desc and meta_desc.get('content'):
            fallback_content.append(f"Opis: {meta_desc['content']}")
            
        if meta_content and meta_content.get('content'):
            fallback_content.append(f"Treść: {meta_content['content']}")
        
        # Strategia 2: Dla Twitter/X - spróbuj pobrać podstawowe info
        if 'twitter.com' in url or 'x.com' in url:
            tweet_id_match = re.search(r'/status/(\d+)', url)
            if tweet_id_match:
                fallback_content.append(f"Tweet ID: {tweet_id_match.group(1)}")
                fallback_content.append("Platforma: Twitter/X (treść niedostępna - wymagane logowanie)")
        
        result = "\n".join(fallback_content) if fallback_content else "Treść niedostępna - strona blokuje automatyzację"
        
        if len(result) > 50:
            self.logger.info(f"[Handler] Odzyskano {len(result)} znaków z metadanych")
            return result
        
        return "Treść niedostępna - strona wymaga pełnej przeglądarki użytkownika"

    def _extract_main_content(self, soup):
        """Próbuje znaleźć główną treść strony używając popularnych selektorów."""
        content_selectors = [
            ('article', {}),
            ('main', {}),
            ('div', {'class': re.compile(r'(content|article|post|entry)', re.I)}),
            ('div', {'id': re.compile(r'(content|article|post|main)', re.I)}),
            ('div', {'data-testid': 'tweetText'}),
            ('div', {'class': re.compile(r'tweet', re.I)}),
            ('div', {'class': re.compile(r'(blog|story|narrative)', re.I)}),
            ('div', {'class': re.compile(r'(story-body|article-body)', re.I)}),
            ('section', {'class': re.compile(r'(main|primary)', re.I)}),
            ('div', {'role': 'main'}),
        ]
        
        for tag, attrs in content_selectors:
            elements = soup.find_all(tag, attrs)
            if elements:
                best_element = max(elements, key=lambda e: len(e.get_text(strip=True)))
                text = best_element.get_text(separator='\n', strip=True)
                
                if len(text) > 200:
                    self.logger.info(f"[Extractor] Użyto selektora: {tag} {attrs}")
                    return text
        
        return None

    def _extract_all_text(self, soup):
        """Fallback - pobiera cały tekst ze strony."""
        body = soup.find('body') or soup
        text_parts = []
        
        title = soup.find('title')
        if title:
            text_parts.append(f"Tytuł: {title.get_text(strip=True)}")
        
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            text_parts.append(f"Opis: {meta['content']}")
        
        for element in body.find_all(['h1', 'h2', 'h3', 'p', 'li']):
            text = element.get_text(strip=True)
            if text and len(text) > 20:
                text_parts.append(text)
        
        return '\n'.join(text_parts)

    def extract_with_retry(self, url: str, max_retries: int = 1) -> str:
        """Ekstrakcja treści z URL z obsługą rozwijania t.co linków."""
        
        # Krok 1: Rozwiń t.co linki do prawdziwych URL-ów
        if 't.co' in url.lower():
            self.logger.info(f"[t.co] Rozwijam skrócony link: {url}")
            expanded_url = self._expand_tco_link(url)
            if expanded_url and expanded_url != url:
                self.logger.info(f"[t.co] Rozwinięto do: {expanded_url}")
                url = expanded_url
            else:
                self.logger.warning(f"[t.co] Nie udało się rozwinąć: {url}")
                return ""
        
        # Krok 2: Sprawdź czy to nadal Twitter/X po rozwinięciu
        if any(domain in url.lower() for domain in ['twitter.com', 'x.com']):
            self.logger.info(f"[Twitter] Pomijam ekstrakcję dla Twitter URL: {url}")
            return ""
        
        # Krok 3: Prosta ekstrakcja dla innych URL
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                # Usuń niepotrzebne elementy
                for element in soup(["script", "style", "nav", "footer"]):
                    element.decompose()
                # Zwróć tekst
                text = soup.get_text(separator=' ', strip=True)
                self.logger.info(f"[Extractor] Pobrano {len(text)} znaków z {url}")
                return text[:3000]  # Ogranicz długość
        except Exception as e:
            self.logger.warning(f"Błąd pobierania {url}: {e}")
        
        return ""
    
    def _expand_tco_link(self, tco_url: str) -> str:
        """Rozwijanie t.co linków do prawdziwych URL-ów."""
        try:
            # Strategia 1: Użyj GET request z allow_redirects
            response = self.session.get(tco_url, allow_redirects=True, timeout=10)
            final_url = response.url
            
            if final_url != tco_url and 't.co' not in final_url:
                self.logger.info(f"[t.co] Rozwinięto: {tco_url} -> {final_url}")
                return final_url
            
            # Strategia 2: Sprawdź nagłówki Location
            response_head = self.session.head(tco_url, allow_redirects=False, timeout=10)
            if 'Location' in response_head.headers:
                location = response_head.headers['Location']
                if location != tco_url and 't.co' not in location:
                    self.logger.info(f"[t.co] Rozwinięto przez Location: {tco_url} -> {location}")
                    return location
            
            # Strategia 3: Jeśli nadal t.co, może to być link do obrazu/wideo Twitter
            if 't.co' in final_url:
                self.logger.info(f"[t.co] Link prowadzi do Twitter media: {final_url}")
                return ""  # Nie próbuj ekstraktować treści z mediów Twitter
            
            self.logger.warning(f"[t.co] Nie udało się rozwinąć: {tco_url}")
            return ""
                
        except Exception as e:
            self.logger.error(f"[t.co] Błąd rozwijania {tco_url}: {e}")
            return ""

    def close(self):
        """Bezpiecznie zamyka sterownik Selenium."""
        if self.driver:
            self.logger.info("[Selenium] Zamykanie sterownika Chrome...")
            try:
                self.driver.quit()
                self.logger.info("[Selenium] Sterownik zamknięty pomyślnie.")
            except Exception as e:
                self.logger.error(f"[Selenium] Błąd zamykania (może być ignorowany): {e}")

# Test funkcjonalności
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    extractor = ContentExtractor()
    
    test_urls = [
        "https://t.co/FCUsmol5XR",  # Trudny - Twitter
        "https://github.com/langchain-ai/langchain",  # Łatwy
        "https://openai.com/blog",  # Średni
    ]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testowanie: {url}")
        print('='*60)
        
        content = extractor.extract_with_retry(url)
        
        if content:
            print(f"✅ Pobrano {len(content)} znaków")
            print(f"📝 Fragment treści:\n{content[:300]}...")
        else:
            print("❌ Nie udało się pobrać treści")
    
    extractor.close() 