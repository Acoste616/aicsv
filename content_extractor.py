# content_extractor.py
import requests
from bs4 import BeautifulSoup
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

class ContentExtractor:
    """
    Klasa odpowiedzialna za ekstrakcję treści z różnych źródeł.
    Używa jednej, trwałej instancji Selenium do wydajnego rozwiązywania przekierowań.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.driver = self._init_selenium_driver()

    def _init_selenium_driver(self):
        """Inicjalizuje i zwraca jedną, trwałą instancję sterownika."""
        try:
            self.logger.info("[Selenium] Inicjalizacja sterownika Chrome...")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            # Użyj WDM do automatycznego zarządzania sterownikiem
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            self.logger.info("[Selenium] Sterownik Chrome zainicjalizowany pomyślnie.")
            return driver
        except Exception as e:
            self.logger.error(f"[Selenium] KRYTYCZNY BŁĄD: Nie udało się zainicjalizować sterownika Selenium: {e}")
            return None

    def _get_final_url(self, url: str) -> str:
        """Używa trwałej instancji Selenium do znalezienia ostatecznego URL."""
        if not self.driver:
            self.logger.error("[Selenium] Sterownik niedostępny, zwracam oryginalny URL.")
            return url
        try:
            self.driver.get(url)
            # Dajemy krótki, ale wystarczający czas na ewentualne przekierowania JS
            time.sleep(2) 
            final_url = self.driver.current_url
            if url != final_url:
                self.logger.info(f"[Extractor] Rozwinięto URL: {url} -> {final_url}")
            return final_url
        except Exception as e:
            self.logger.error(f"[Extractor] Błąd Selenium przy rozwijaniu {url}: {e}")
            return url

    def get_webpage_content(self, url: str) -> str:
        """Pobiera główną treść tekstową z podanego URL."""
        final_url = ""
        try:
            final_url = self._get_final_url(url)
            
            response = self.session.get(final_url, timeout=20)
            response.raise_for_status()

            if 'text/html' not in response.headers.get('Content-Type', ''):
                self.logger.warning(f"[Extractor] Zawartość pod {final_url} nie jest HTML-em.")
                return ""

            soup = BeautifulSoup(response.text, 'lxml')
            # Usuń niepotrzebne tagi
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "button"]):
                element.decompose()
            text = soup.get_text(separator='\n', strip=True)

            # Ograniczamy długość, aby nie przeciążyć LLM
            max_length = 4000
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            self.logger.info(f"[Extractor] Wyodrębniono ~{len(text)} znaków z {final_url}")
            return text
        except Exception as e:
            self.logger.error(f"[Extractor] Błąd parsowania {final_url or url}: {e}")
            return ""

    def close(self):
        """Bezpiecznie zamyka sterownik Selenium."""
        if self.driver:
            self.logger.info("[Selenium] Zamykanie sterownika Chrome...")
            try:
                self.driver.quit()
                self.logger.info("[Selenium] Sterownik zamknięty pomyślnie.")
            except Exception as e:
                # Ignoruj błędy, jeśli sterownik już jest zamknięty lub nie odpowiada
                self.logger.error(f"[Selenium] Wystąpił błąd podczas zamykania sterownika (może być ignorowany): {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    extractor = ContentExtractor()
    if extractor.driver:
        test_url = "https://t.co/lWgXOSrLAp" 
        print(f"Testuję ekstrakcję z: {test_url}")
        content = extractor.get_webpage_content(test_url)
        print("\n--- Wyodrębniona treść: ---")
        print(content)
        extractor.close() 