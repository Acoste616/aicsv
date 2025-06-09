# integrated_adaptive_prompts.py
"""
Ulepszona wersja funkcji create_adaptive_prompt zintegrowana z Enhanced Content Strategy
"""

import logging
from typing import Dict, Optional
from enhanced_content_strategy import EnhancedContentStrategy

class IntegratedAdaptivePrompts:
    """
    Klasa łącząca Enhanced Content Strategy z adaptacyjnymi promptami
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.content_strategy = EnhancedContentStrategy()
    
    def create_adaptive_prompt(self, url: str, tweet_text: str, content_quality: str = None, 
                              content_data: Optional[Dict] = None) -> str:
        """
        Dostosuj prompt do jakości dostępnej treści
        
        Args:
            url: URL artykułu
            tweet_text: Tekst tweeta
            content_quality: Opcjonalne - jakość treści ('high', 'medium', 'low')
            content_data: Opcjonalne - dane z Enhanced Content Strategy
            
        Returns:
            Dostosowany prompt dla LLM
        """
        
        # Jeśli nie mamy content_data, pobierz używając Enhanced Content Strategy
        if content_data is None:
            self.logger.info(f"[Prompts] Pobieranie treści dla: {url}")
            content_data = self.content_strategy.get_content(url, tweet_text)
        
        # Ustal jakość jeśli nie podana
        if content_quality is None:
            content_quality = content_data.get('quality', 'low')
        
        # Pobierz treść
        content = content_data.get('content', '')
        source = content_data.get('source', 'unknown')
        confidence = content_data.get('confidence', 0.0)
        
        self.logger.info(f"[Prompts] Generuję prompt - jakość: {content_quality}, źródło: {source}")
        
        if content_quality == 'high':
            # Pełna analiza
            return self._full_analysis_prompt(url, tweet_text, content, content_data)
        
        elif content_quality == 'medium':
            # Analiza na podstawie metadanych/częściowej treści
            return self._medium_analysis_prompt(url, tweet_text, content, content_data)
        
        else:
            # Analiza tylko tweeta
            return self._low_analysis_prompt(url, tweet_text, content_data)

    def _full_analysis_prompt(self, url: str, tweet_text: str, content: str, content_data: Dict) -> str:
        """Prompt dla pełnej analizy treści"""
        source = content_data.get('source', 'unknown')
        
        prompt = f"""
Masz dostęp do pełnej treści artykułu. Przeprowadź szczegółową analizę:

DANE WEJŚCIOWE:
- Tweet: {tweet_text}
- URL: {url}
- Źródło danych: {source}
- Pewność danych: {content_data.get('confidence', 0):.2f}

PEŁNA TREŚĆ ARTYKUŁU:
{content[:2000]}{"..." if len(content) > 2000 else ""}

ZADANIE - Przeanalizuj treść i zwróć JSON z polami:
{{
    "title": "Dokładny tytuł artykułu",
    "category": "technical/news/blog/research/tutorial/other",
    "main_topic": "Główny temat w 2-3 słowach",
    "key_points": ["Najważniejszy punkt 1", "Punkt 2", "Punkt 3"],
    "educational_value": 8,
    "practical_value": 7,
    "target_audience": "developers/students/researchers/general",
    "difficulty_level": "beginner/intermediate/advanced",
    "technologies": ["technologia1", "technologia2"],
    "takeaways": ["Konkretny wniosek 1", "Wniosek 2"],
    "worth_revisiting": true,
    "confidence_level": 0.9,
    "summary": "Zwięzłe podsumowanie w 2-3 zdaniach",
    "time_to_read": "5 min/15 min/30 min/1 hour"
}}

UWAGA: Masz dostęp do pełnej treści - wykorzystaj wszystkie szczegóły!
"""
        return prompt

    def _medium_analysis_prompt(self, url: str, tweet_text: str, content: str, content_data: Dict) -> str:
        """Prompt dla analizy na podstawie metadanych/częściowej treści"""
        source = content_data.get('source', 'unknown')
        
        # Sprawdź czy to metadane czy częściowa treść
        data_type = "metadane" if source in ['metadata', 'preview_api'] else "częściowa treść"
        
        prompt = f"""
Przeanalizuj tweet i dostępne {data_type}:

DANE WEJŚCIOWE:
- Tweet: {tweet_text}
- URL: {url}
- Typ danych: {data_type} (źródło: {source})
- Pewność: {content_data.get('confidence', 0):.2f}

DOSTĘPNE INFORMACJE:
{content[:1000]}{"..." if len(content) > 1000 else ""}

ZADANIE - Na podstawie dostępnych informacji określ:
1. Prawdopodobny temat główny
2. Kategorię treści (technical/news/blog/research/other)
3. Szacunkową wartość edukacyjną (1-10)
4. Dla kogo może być przydatne
5. Czy warto wrócić do tego linku później
6. Poziom pewności Twojej oceny

Zwróć JSON z polami:
{{
    "title": "Prawdopodobny tytuł na podstawie {data_type}",
    "category": "technical/news/blog/research/other",
    "inferred_topic": "Wywnioskowany główny temat",
    "estimated_value": 6,
    "likely_audience": "Prawdopodobni odbiorcy",
    "domain_category": "Kategoria domeny",
    "worth_investigating": true,
    "confidence_level": 0.6,
    "reasoning": "Dlaczego tak oceniłem na podstawie {data_type}",
    "follow_up_needed": "Co sprawdzić dodatkowo",
    "data_limitations": "Czego nie wiem z powodu ograniczonych danych"
}}

UWAGA: Pracujesz z ograniczonymi danymi ({data_type}) - wskaż poziom pewności!
"""
        return prompt

    def _low_analysis_prompt(self, url: str, tweet_text: str, content_data: Dict) -> str:
        """Prompt dla analizy tylko na podstawie tweeta"""
        domain = url.split('/')[2] if '/' in url else url
        
        prompt = f"""
Przeanalizuj sam tweet (artykuł niedostępny):

DANE WEJŚCIOWE:
- Tweet: {tweet_text}
- URL: {url}
- Domena: {domain}
- Dlaczego brak treści: {content_data.get('error', 'nieznany powód')}

ZADANIE - Na podstawie TYLKO treści tweeta wywnioskuj:
1. O czym prawdopodobnie jest artykuł/link
2. Dlaczego autor udostępnił ten link
3. Jaka może być wartość tego linku
4. Dla kogo może być interessujący
5. Kategoria prawdopodobnej treści
6. Czy to wymaga dalszego badania

Zwróć JSON z polami:
{{
    "inferred_topic": "Domniemany temat na podstawie tweeta",
    "sharing_reason": "Dlaczego autor prawdopodobnie udostępnił",
    "category_guess": "Przypuszczalna kategoria treści",
    "potential_value": 4,
    "target_audience_guess": "Domniemani odbiorcy",
    "investigation_priority": "low/medium/high",
    "confidence_level": 0.3,
    "next_steps": "Co zrobić żeby dowiedzieć się więcej",
    "red_flags": "Ewentualne ostrzeżenia",
    "domain_reputation": "Co wiesz o tej domenie"
}}

UWAGA: 
- Masz tylko podstawowe informacje (tweet + URL)
- Wszystkie wnioski oznacz jako przypuszczenia
- Bądź ostrożny w ocenach - niski confidence_level!
"""
        return prompt

    def create_specialized_prompt(self, url: str, tweet_text: str, content_data: Dict, 
                                 analysis_type: str = 'general') -> str:
        """
        Tworzy wyspecjalizowany prompt dla konkretnego typu analizy
        
        Args:
            analysis_type: 'technical', 'research', 'news', 'tutorial', 'thread'
        """
        
        source = content_data.get('source', 'unknown')
        quality = content_data.get('quality', 'low')
        
        # Specjalne prompty dla threadów
        if analysis_type == 'thread' or source == 'thread':
            return self._create_thread_analysis_prompt(url, tweet_text, content_data)
        
        # Specjalne prompty dla GitHub
        elif 'github.com' in url.lower():
            return self._create_github_analysis_prompt(url, tweet_text, content_data)
        
        # Specjalne prompty dla YouTube
        elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
            return self._create_youtube_analysis_prompt(url, tweet_text, content_data)
        
        # Standardowy prompt z fokusem na typ analizy
        else:
            base_prompt = self.create_adaptive_prompt(url, tweet_text, quality, content_data)
            
            # Dodaj specjalizację
            specialization = self._get_analysis_specialization(analysis_type)
            return base_prompt + "\n\n" + specialization

    def _create_thread_analysis_prompt(self, url: str, tweet_text: str, content_data: Dict) -> str:
        """Specjalny prompt dla analizy wątków Twitter"""
        content = content_data.get('content', '')
        
        return f"""
Przeanalizuj pełny wątek z Twittera:

WĄTEK TWITTER:
{content[:2500]}

ZADANIE - Przeprowadź analizę całego wątku:
1. Główna teza i struktura argumentacji
2. Kluczowe insights i wnioski  
3. Czy wątek jest kompletny i logiczny
4. Wartość edukacyjna całego wątku
5. Praktyczne zastosowania

Zwróć JSON z polami:
{{
    "thread_title": "Główny temat wątku",
    "main_thesis": "Główna teza autora",
    "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
    "thread_quality": "excellent/good/poor",
    "completeness": "complete/incomplete/unclear",
    "educational_value": 8,
    "target_audience": "Dla kogo przeznaczony",
    "actionable_items": ["Co można zrobić 1", "Akcja 2"],
    "thread_length": "Liczba tweetów w wątku",
    "worth_following_author": true
}}
"""

    def _create_github_analysis_prompt(self, url: str, tweet_text: str, content_data: Dict) -> str:
        """Specjalny prompt dla repozytoriów GitHub"""
        content = content_data.get('content', '')
        
        return f"""
Przeanalizuj repozytorium GitHub:

INFORMACJE O REPO:
{content[:1500]}

Tweet: {tweet_text}
URL: {url}

ZADANIE - Oceń repozytorium pod kątem:
1. Główne funkcje i cel projektu
2. Używane technologie
3. Poziom zaawansowania i dokumentacji
4. Aktywność projektu
5. Wartość dla różnych grup użytkowników

Zwróć JSON:
{{
    "project_name": "Nazwa projektu",
    "main_purpose": "Główny cel projektu", 
    "technologies": ["tech1", "tech2", "tech3"],
    "difficulty_level": "beginner/intermediate/advanced",
    "documentation_quality": "excellent/good/poor",
    "project_maturity": "experimental/stable/mature",
    "use_cases": ["Przypadek użycia 1", "Przypadek 2"],
    "learning_value": 8,
    "worth_starring": true,
    "similar_projects": ["Podobny projekt 1", "Projekt 2"]
}}
"""

    def _create_youtube_analysis_prompt(self, url: str, tweet_text: str, content_data: Dict) -> str:
        """Specjalny prompt dla filmów YouTube"""
        content = content_data.get('content', '')
        
        return f"""
Przeanalizuj film YouTube na podstawie metadanych:

INFORMACJE O FILMIE:
{content[:1000]}

Tweet: {tweet_text}

ZADANIE - Oceń film pod kątem:
1. Główny temat i format (tutorial/prezentacja/dyskusja)
2. Poziom zaawansowania
3. Szacowany czas obejrzenia i wartość
4. Kluczowe umiejętności do wyniesienia

Zwróć JSON:
{{
    "video_title": "Tytuł filmu",
    "video_format": "tutorial/presentation/discussion/demo",
    "main_topic": "Główny temat",
    "difficulty_level": "beginner/intermediate/advanced", 
    "estimated_duration": "Szacowany czas",
    "key_skills": ["Umiejętność 1", "Umiejętność 2"],
    "watch_priority": "high/medium/low",
    "best_for": "Najlepsze dla jakiej grupy",
    "prerequisites": "Wymagana wiedza wstępna"
}}
"""

    def _get_analysis_specialization(self, analysis_type: str) -> str:
        """Dodatkowe instrukcje dla specjalizacji"""
        specializations = {
            'technical': """
DODATKOWY FOKUS TECHNICZNY:
- Zwróć szczególną uwagę na technologie i narzędzia
- Oceń praktyczne zastosowanie w projektach
- Wskaż poziom zaawansowania technicznego
""",
            'research': """
DODATKOWY FOKUS BADAWCZY:
- Oceń metodologię i wiarygodność źródeł
- Wskaż implikacje dla dalszych badań
- Sprawdź aktualność i relevantność
""",
            'news': """
DODATKOWY FOKUS NEWSOWY:
- Oceń aktualność i wpływ na branżę
- Wskaż kluczowe fakty i implikacje
- Sprawdź wiarygodność źródła
"""
        }
        
        return specializations.get(analysis_type, "")


# Przykład użycia - kompatybilność z istniejącym kodem
def create_adaptive_prompt(url: str, tweet_text: str, content_quality: str) -> str:
    """
    Funkcja kompatybilna z istniejącym kodem - wrapper na nową implementację
    """
    integrated_prompts = IntegratedAdaptivePrompts()
    return integrated_prompts.create_adaptive_prompt(url, tweet_text, content_quality)


# Demo funkcjonalności
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    prompts = IntegratedAdaptivePrompts()
    
    # Test różnych przypadków
    test_cases = [
        {
            'url': 'https://github.com/microsoft/vscode',
            'tweet': 'Amazing code editor! Check this out #coding',
            'expected_quality': 'high'
        },
        {
            'url': 'https://nytimes.com/some-paywall-article',
            'tweet': 'Interesting article about tech trends',
            'expected_quality': 'low'
        }
    ]
    
    for test in test_cases:
        print(f"\n🧪 Test: {test['url'][:50]}...")
        prompt = prompts.create_adaptive_prompt(
            test['url'], 
            test['tweet']
        )
        print(f"📝 Długość promptu: {len(prompt)} znaków")
        print(f"🎯 Pierwsza linia: {prompt.split(chr(10))[0][:100]}...")