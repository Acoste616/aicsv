# adaptive_prompts.py
"""
System adaptacyjnych promptów dla LLM dostosowujących się do jakości danych
"""

import logging
from typing import Dict, Optional, Any
from urllib.parse import urlparse

class AdaptivePromptGenerator:
    """Generator promptów dostosowujących się do jakości dostępnych danych"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Szablony promptów dla różnych jakości danych
        self.prompt_templates = {
            'high_quality': self._create_full_analysis_template(),
            'medium_quality': self._create_metadata_analysis_template(), 
            'low_quality': self._create_tweet_analysis_template(),
            'thread_analysis': self._create_thread_analysis_template(),
            'github_analysis': self._create_github_analysis_template(),
            'youtube_analysis': self._create_youtube_analysis_template()
        }

    def generate_prompt(self, content_data: Dict, analysis_type: str = 'general') -> str:
        """
        Generuje prompt dostosowany do jakości i typu danych
        
        Args:
            content_data: Dane z enhanced content strategy
            analysis_type: Typ analizy ('general', 'technical', 'research')
            
        Returns:
            Dostosowany prompt dla LLM
        """
        quality = content_data.get('quality', 'low')
        source = content_data.get('source', 'unknown')
        url = content_data.get('url', '')
        content = content_data.get('content', '')
        
        self.logger.info(f"[Prompts] Generuję prompt dla: quality={quality}, source={source}")
        
        # Wybierz odpowiedni szablon
        if source == 'thread':
            template_key = 'thread_analysis'
        elif 'github' in url.lower():
            template_key = 'github_analysis'
        elif 'youtube' in url.lower():
            template_key = 'youtube_analysis'
        elif quality == 'high':
            template_key = 'high_quality'
        elif quality == 'medium':
            template_key = 'medium_quality'
        else:
            template_key = 'low_quality'
        
        # Pobierz szablon i wypełnij danymi
        template = self.prompt_templates[template_key]
        prompt = template.format(
            url=url,
            content=content[:3000],  # Ogranicz długość
            domain=urlparse(url).netloc if url else 'unknown',
            source=source,
            quality=quality,
            confidence=content_data.get('confidence', 0.0),
            analysis_type=analysis_type
        )
        
        # Dodaj instrukcje specjalne w zależności od jakości
        prompt += self._get_quality_specific_instructions(quality, source)
        
        # Dodaj końcowe instrukcje JSON
        prompt += self._get_json_instructions(quality)
        
        return prompt

    def _create_full_analysis_template(self) -> str:
        """Szablon dla pełnej analizy treści"""
        return """
Przeanalizuj następującą treść artykułu:

URL: {url}
Źródło: {source}
Jakość danych: {quality}
Pewność: {confidence}

TREŚĆ ARTYKUŁU:
{content}

Przeprowadź pełną analizę i wyodrębnij:
1. Główny temat i kluczowe punkty
2. Wartość edukacyjną i praktyczną
3. Docelową grupę odbiorców
4. Konkretne wnioski i takeaways
5. Powiązane technologie/tematy
6. Ocenę przydatności dla różnych celów

"""

    def _create_metadata_analysis_template(self) -> str:
        """Szablon dla analizy na podstawie metadanych"""
        return """
Przeanalizuj dostępne metadane i opis artykułu:

URL: {url}
Domena: {domain}
Źródło: {source}
Jakość danych: {quality}

DOSTĘPNE INFORMACJE:
{content}

Na podstawie tych informacji określ:
1. Prawdopodobny główny temat
2. Kategoria treści (technical/news/blog/research/other)
3. Szacunkową wartość edukacyjną (1-10)
4. Dla kogo może być przydatne
5. Czy warto wrócić do tego linku później
6. Poziom pewności Twojej oceny

UWAGA: To analiza na podstawie ograniczonych danych (metadane/opis).
"""

    def _create_tweet_analysis_template(self) -> str:
        """Szablon dla analizy tylko na podstawie tweeta"""
        return """
Przeanalizuj tweet i wywnioskuj informacje o linkowanym artykule:

URL: {url}
Domena: {domain}
Źródło: {source}

TREŚĆ TWEETA:
{content}

Na podstawie samego tweeta wywnioskuj:
1. O czym prawdopodobnie jest artykuł/link
2. Dlaczego autor udostępnił ten link
3. Jaka może być wartość tego linku
4. Dla kogo może być interessujący
5. Kategoria prawdopodobnej treści
6. Czy to wymaga dalszego badania

UWAGA: To analiza tylko na podstawie tweeta - artykuł niedostępny.
"""

    def _create_thread_analysis_template(self) -> str:
        """Szablon dla analizy wątku Twitter"""
        return """
Przeanalizuj pełny wątek z Twittera:

URL: {url}
Źródło: {source}
Jakość: {quality}

PEŁNY WĄTEK:
{content}

Przeprowadź analizę całego wątku:
1. Główna teza i argumenty
2. Struktura i logika wywodu
3. Kluczowe insights i wnioski
4. Wartość edukacyjna całego wątku
5. Praktyczne zastosowania
6. Czy wątek jest kompletny i spójny
7. Docelowa grupa odbiorców

UWAGA: To analiza pełnego wątku Twitter - może zawierać szczegółowe informacje.
"""

    def _create_github_analysis_template(self) -> str:
        """Szablon dla analizy repozytoriów GitHub"""
        return """
Przeanalizuj repozytorium GitHub:

URL: {url}
Źródło: {source}

INFORMACJE O REPO:
{content}

Przeanalizuj repozytorium pod kątem:
1. Główne funkcje i cel projektu
2. Używane technologie i języki
3. Poziom zaawansowania (beginner/intermediate/advanced)
4. Praktyczne zastosowania
5. Aktywność i dojrzałość projektu
6. Wartość dla różnych grup (developers/learners/researchers)
7. Dokumentacja i przykłady użycia

UWAGA: To analiza repozytorium kodu - skupia się na aspektach technicznych.
"""

    def _create_youtube_analysis_template(self) -> str:
        """Szablon dla analizy filmów YouTube"""
        return """
Przeanalizuj film YouTube:

URL: {url}
Źródło: {source}

INFORMACJE O FILMIE:
{content}

Na podstawie tytułu i opisu określ:
1. Główny temat i zawartość filmu
2. Format (tutorial/prezentacja/dyskusja/demo)
3. Poziom zaawansowania
4. Szacowany czas potrzebny na obejrzenie
5. Kluczowe umiejętności/wiedza do wyniesienia
6. Docelowa grupa odbiorców
7. Czy warto obejrzeć w kontekście nauki/pracy

UWAGA: To analiza na podstawie metadanych YouTube - bez treści wideo.
"""

    def _get_quality_specific_instructions(self, quality: str, source: str) -> str:
        """Dodatkowe instrukcje specyficzne dla jakości danych"""
        if quality == 'high':
            return """
DODATKOWE INSTRUKCJE:
- Masz dostęp do pełnej treści - wykorzystaj wszystkie szczegóły
- Przypisz wysoką wagę do konkretnych faktów i przykładów
- Oceń dokładność i aktualność informacji
- Zidentyfikuj najważniejsze cytaty i fragmenty
"""
        
        elif quality == 'medium':
            return """
DODATKOWE INSTRUKCJE:
- Pracujesz z ograniczonymi danymi (metadane, opisy)
- Wyraźnie wskaż poziom pewności swoich wniosków
- Sugeruj co warto zbadać głębiej
- Nie spekuluj zbyt szeroko - trzymaj się faktów
"""
        
        else:  # low quality
            return """
DODATKOWE INSTRUKCJE:
- Masz tylko podstawowe informacje (tweet, URL)
- Wszystkie wnioski oznacz jako przypuszczenia
- Skup się na kategoryzacji i priorytetyzacji
- Wskaż co wymaga dalszego badania
- Bądź ostrożny w ocenach
"""

    def _get_json_instructions(self, quality: str) -> str:
        """Instrukcje dla formatu JSON w zależności od jakości"""
        if quality == 'high':
            return """
Zwróć odpowiedź w formacie JSON z polami:
{
    "title": "Wyodrębniony lub prawdopodobny tytuł",
    "category": "technical/news/blog/research/tutorial/other",
    "main_topic": "Główny temat w 2-3 słowach", 
    "key_points": ["Punkt 1", "Punkt 2", "Punkt 3"],
    "educational_value": 8,
    "practical_value": 7,
    "target_audience": "developers/students/researchers/general",
    "difficulty_level": "beginner/intermediate/advanced",
    "time_investment": "5 min/30 min/1 hour/2+ hours",
    "technologies": ["tech1", "tech2"],
    "takeaways": ["Wniosek 1", "Wniosek 2"],
    "worth_revisiting": true,
    "confidence_level": 0.9,
    "notes": "Dodatkowe uwagi"
}
"""
        
        elif quality == 'medium':
            return """
Zwróć odpowiedź w formacie JSON z polami:
{
    "title": "Prawdopodobny tytuł z metadanych",
    "category": "technical/news/blog/research/other", 
    "inferred_topic": "Wywnioskowany temat",
    "estimated_value": 6,
    "likely_audience": "Prawdopodobni odbiorcy",
    "domain_category": "Kategoria domeny",
    "worth_investigating": true,
    "confidence_level": 0.6,
    "reasoning": "Dlaczego tak oceniłem",
    "follow_up_needed": "Co sprawdzić dodatkowo"
}
"""
        
        else:  # low quality
            return """
Zwróć odpowiedź w formacie JSON z polami:
{
    "inferred_topic": "Domniemany temat na podstawie tweeta",
    "sharing_reason": "Dlaczego autor udostępnił", 
    "category_guess": "Przypuszczalna kategoria",
    "potential_value": 4,
    "target_audience_guess": "Domniemani odbiorcy",
    "investigation_priority": "low/medium/high",
    "confidence_level": 0.3,
    "next_steps": "Co zrobić żeby dowiedzieć się więcej",
    "red_flags": "Ewentualne ostrzeżenia"
}
"""

    def create_comparison_prompt(self, content_items: list) -> str:
        """Tworzy prompt do porównania wielu treści"""
        items_text = ""
        for i, item in enumerate(content_items, 1):
            items_text += f"""
TREŚĆ {i}:
URL: {item.get('url', 'brak')}
Jakość: {item.get('quality', 'unknown')}
Treść: {item.get('content', '')[:500]}...

"""
        
        return f"""
Porównaj następujące treści i uszereguj je według wartości:

{items_text}

Dla każdej treści określ:
1. Wartość edukacyjną (1-10)
2. Unikalność informacji
3. Jakość źródła
4. Aktualność
5. Praktyczne zastosowanie

Następnie uszereguj je od najwartościowszej do najmniej wartościowej i uzasadnij ranking.

Zwróć wynik w formacie JSON:
{{
    "ranking": [
        {{
            "position": 1,
            "url": "...",
            "score": 8.5,
            "reasoning": "Dlaczego na pierwszym miejscu"
        }}
    ],
    "summary": "Ogólne wnioski z porównania"
}}
"""

    def create_batch_analysis_prompt(self, content_batch: list, focus_area: str = None) -> str:
        """Tworzy prompt do analizy batch'a treści"""
        focus_instruction = ""
        if focus_area:
            focus_instruction = f"Szczególnie skup się na aspektach związanych z: {focus_area}"
        
        batch_text = ""
        for i, item in enumerate(content_batch, 1):
            batch_text += f"ITEM {i}: {item.get('content', '')[:200]}...\n\n"
        
        return f"""
Przeanalizuj następujący batch treści i znajdź wspólne wzorce:

{batch_text}

{focus_instruction}

Przeprowadź analizę całej grupy:
1. Wspólne tematy i wzorce
2. Różnice w podejściu/jakości
3. Komplementarność treści
4. Luki w wiedzy
5. Rekomendacje priorytetów

Zwróć JSON z analizą grupy i indywidualnymi ocenami.
"""