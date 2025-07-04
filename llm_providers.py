"""
LLM Providers Module - obsługa różnych dostawców API LLM
Wspiera: Claude (Anthropic), Gemini (Google), oraz lokalny serwer
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import requests
from dotenv import load_dotenv

# Importy dla konkretnych API
try:
    import anthropic
except ImportError:
    anthropic = None
    
try:
    import google.generativeai as genai
except ImportError:
    genai = None

load_dotenv()
logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstrakcyjna klasa bazowa dla dostawców LLM"""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Generuje odpowiedź na podstawie promptu"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Sprawdza czy provider jest dostępny"""
        pass


class ClaudeProvider(LLMProvider):
    """Provider dla Claude API (Anthropic)"""
    
    def __init__(self):
        if not anthropic:
            raise ImportError("Zainstaluj bibliotekę anthropic: pip install anthropic")
            
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Ustaw ANTHROPIC_API_KEY w pliku .env")
            
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Generuje odpowiedź używając Claude API"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
                
            response = self.client.messages.create(**kwargs)
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Błąd Claude API: {e}")
            raise
            
    def is_available(self) -> bool:
        """Sprawdza dostępność Claude API"""
        try:
            # Testowa wiadomość
            self.generate("test", max_tokens=10)
            return True
        except:
            return False


class GeminiProvider(LLMProvider):
    """Provider dla Gemini API (Google)"""
    
    def __init__(self):
        if not genai:
            raise ImportError("Zainstaluj bibliotekę google-generativeai: pip install google-generativeai")
            
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Ustaw GOOGLE_API_KEY w pliku .env")
            
        genai.configure(api_key=self.api_key)
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-pro")
        self.model = genai.GenerativeModel(self.model_name)
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Generuje odpowiedź używając Gemini API"""
        try:
            # Łącz system prompt z user prompt jeśli podany
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
                
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Błąd Gemini API: {e}")
            raise
            
    def is_available(self) -> bool:
        """Sprawdza dostępność Gemini API"""
        try:
            self.generate("test", max_tokens=10)
            return True
        except:
            return False


class LocalProvider(LLMProvider):
    """Provider dla lokalnego serwera LLM (np. LM Studio)"""
    
    def __init__(self, api_url: str = "http://localhost:1234/v1/chat/completions",
                 model_name: str = "local-model"):
        self.api_url = api_url
        self.model_name = model_name
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Generuje odpowiedź używając lokalnego API"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Błąd lokalnego API: {e}")
            raise
            
    def is_available(self) -> bool:
        """Sprawdza dostępność lokalnego API"""
        try:
            models_url = self.api_url.replace("/chat/completions", "/models")
            response = requests.get(models_url, timeout=5)
            return response.status_code == 200
        except:
            return False


class LLMManager:
    """Manager do zarządzania różnymi providerami LLM"""
    
    def __init__(self, preferred_provider: str = "claude"):
        self.providers = {}
        self.preferred_provider = preferred_provider
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Inicjalizuje dostępnych providerów"""
        # Claude
        try:
            self.providers["claude"] = ClaudeProvider()
            logger.info("Zainicjalizowano Claude provider")
        except Exception as e:
            logger.warning(f"Nie można zainicjalizować Claude: {e}")
            
        # Gemini
        try:
            self.providers["gemini"] = GeminiProvider()
            logger.info("Zainicjalizowano Gemini provider")
        except Exception as e:
            logger.warning(f"Nie można zainicjalizować Gemini: {e}")
            
        # Lokalny
        try:
            from config import LLM_CONFIG
            self.providers["local"] = LocalProvider(
                api_url=LLM_CONFIG.get("api_url", "http://localhost:1234/v1/chat/completions"),
                model_name=LLM_CONFIG.get("model_name", "local-model")
            )
            logger.info("Zainicjalizowano lokalny provider")
        except Exception as e:
            logger.warning(f"Nie można zainicjalizować lokalnego providera: {e}")
            
    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        """Zwraca providera o podanej nazwie lub preferowanego"""
        if name is None:
            name = self.preferred_provider
            
        if name in self.providers and self.providers[name].is_available():
            return self.providers[name]
            
        # Fallback do pierwszego dostępnego
        for provider_name, provider in self.providers.items():
            if provider.is_available():
                logger.warning(f"Używam {provider_name} zamiast {name}")
                return provider
                
        raise RuntimeError("Brak dostępnych providerów LLM")
        
    def list_available_providers(self) -> List[str]:
        """Zwraca listę dostępnych providerów"""
        available = []
        for name, provider in self.providers.items():
            if provider.is_available():
                available.append(name)
        return available