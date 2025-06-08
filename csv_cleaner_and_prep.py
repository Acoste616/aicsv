#!/usr/bin/env python3
"""
CSV Cleaner and Prep System
Uniwersalny system do czyszczenia i przygotowania CSV z zakładkami/tweetami
Obsługuje różne formaty: prosty (bookmarks.csv) i pełny Twitter API (bookmarks1.csv)
"""

import pandas as pd
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys
import os
from datetime import datetime

class CSVCleanerAndPrep:
    """
    Uniwersalny cleaner dla różnych formatów CSV z tweetami/zakładkami.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Konfiguracja kolumn dla różnych formatów
        self.format_configs = {
            "simple": {
                "required_cols": ["full_text", "tweet_url"],
                "optional_cols": ["screen_name", "name", "tweeted_at", "note_tweet_text"],
                "url_col": "tweet_url",
                "text_col": "full_text",
                "author_col": "screen_name",
                "date_col": "tweeted_at"
            },
            "twitter_api": {
                "required_cols": ["full_text", "url"],
                "optional_cols": ["screen_name", "name", "created_at", "media", "favorite_count", "retweet_count"],
                "url_col": "url", 
                "text_col": "full_text",
                "author_col": "screen_name",
                "date_col": "created_at"
            }
        }

    def detect_csv_format(self, csv_file: str) -> str:
        """Automatycznie wykrywa format CSV."""
        try:
            # Czytaj tylko pierwszy wiersz żeby sprawdzić kolumny
            sample = pd.read_csv(csv_file, nrows=1)
            columns = list(sample.columns)
            
            self.logger.info(f"Wykryte kolumny: {columns}")
            
            # Sprawdź który format pasuje
            for format_name, config in self.format_configs.items():
                required = config["required_cols"]
                if all(col in columns for col in required):
                    self.logger.info(f"Wykryto format: {format_name}")
                    return format_name
                    
            self.logger.warning("Nieznany format CSV - użyję domyślnego")
            return "simple"
            
        except Exception as e:
            self.logger.error(f"Błąd wykrywania formatu: {e}")
            return "simple"

    def load_and_analyze_csv(self, csv_file: str) -> Tuple[pd.DataFrame, Dict]:
        """Wczytuje CSV i analizuje jego jakość."""
        try:
            self.logger.info(f"Ładowanie CSV: {csv_file}")
            
            # Wykryj format
            csv_format = self.detect_csv_format(csv_file)
            config = self.format_configs[csv_format]
            
            # Wczytaj całość
            df = pd.read_csv(csv_file)
            
            # Analiza jakości
            analysis = {
                "format": csv_format,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "empty_rows": df.isnull().all(axis=1).sum(),
                "duplicate_urls": 0,
                "missing_text": 0,
                "missing_urls": 0,
                "data_quality": "unknown"
            }
            
            # Sprawdź kluczowe kolumny
            text_col = config["text_col"]
            url_col = config["url_col"]
            
            if text_col in df.columns:
                analysis["missing_text"] = df[text_col].isnull().sum()
            if url_col in df.columns:
                analysis["missing_urls"] = df[url_col].isnull().sum()
                analysis["duplicate_urls"] = df[url_col].duplicated().sum()
            
            # Oceń jakość
            empty_ratio = analysis["empty_rows"] / analysis["total_rows"]
            missing_ratio = (analysis["missing_text"] + analysis["missing_urls"]) / (2 * analysis["total_rows"])
            
            if empty_ratio < 0.05 and missing_ratio < 0.1:
                analysis["data_quality"] = "excellent"
            elif empty_ratio < 0.15 and missing_ratio < 0.25:
                analysis["data_quality"] = "good"
            elif empty_ratio < 0.3 and missing_ratio < 0.5:
                analysis["data_quality"] = "moderate"
            else:
                analysis["data_quality"] = "poor"
                
            self.logger.info(f"Analiza: {analysis['total_rows']} wierszy, jakość: {analysis['data_quality']}")
            
            return df, analysis
            
        except Exception as e:
            self.logger.error(f"Błąd ładowania CSV: {e}")
            return None, None

    def clean_dataframe(self, df: pd.DataFrame, analysis: Dict) -> pd.DataFrame:
        """Czyści DataFrame usuwając zbędne dane i normalizując format."""
        
        config = self.format_configs[analysis["format"]]
        text_col = config["text_col"] 
        url_col = config["url_col"]
        author_col = config["author_col"]
        date_col = config["date_col"]
        
        self.logger.info("Rozpoczynam czyszczenie danych...")
        
        # 1. Usuń puste wiersze
        initial_count = len(df)
        df = df.dropna(how='all')
        self.logger.info(f"Usunięto {initial_count - len(df)} pustych wierszy")
        
        # 2. Usuń wiersze bez tekstu lub URL
        df = df.dropna(subset=[col for col in [text_col, url_col] if col in df.columns])
        self.logger.info(f"Pozostało {len(df)} wierszy po usunięciu brakujących danych")
        
        # 3. Usuń duplikaty URL
        if url_col in df.columns:
            before_dedup = len(df)
            df = df.drop_duplicates(subset=[url_col], keep='first')
            self.logger.info(f"Usunięto {before_dedup - len(df)} duplikatów URL")
        
        # 4. Oczyść tekst
        if text_col in df.columns:
            df[text_col] = df[text_col].apply(self._clean_text)
        
        # 5. Normalizuj URL
        if url_col in df.columns:
            df[url_col] = df[url_col].apply(self._normalize_url)
        
        # 6. Parsuj media jeśli są (dla formatu Twitter API)
        if "media" in df.columns and analysis["format"] == "twitter_api":
            df["has_video"] = df["media"].apply(self._extract_video_info)
            df["has_images"] = df["media"].apply(self._extract_image_info)
        
        # 7. Filtruj nieciekawe treści
        df = self._filter_content(df, text_col)
        
        self.logger.info(f"Czyszczenie zakończone. Finalne: {len(df)} wierszy")
        
        return df

    def _clean_text(self, text: str) -> str:
        """Czyści tekst tweeta."""
        if pd.isna(text) or not isinstance(text, str):
            return ""
            
        # Usuń nadmiar białych znaków
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Usuń dziwne znaki kontrolne
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
        
        return text

    def _normalize_url(self, url: str) -> str:
        """Normalizuje URL."""
        if pd.isna(url) or not isinstance(url, str):
            return ""
            
        # Konwertuj twitter.com na x.com dla spójności
        url = url.replace("twitter.com", "x.com")
        
        # Usuń query parameters które nie są potrzebne
        url = re.sub(r'[?&]ref_src=.*?(?=&|$)', '', url)
        url = re.sub(r'[?&]s=\d+', '', url)
        
        return url.strip()

    def _extract_video_info(self, media_json: str) -> bool:
        """Sprawdza czy tweet zawiera video."""
        if pd.isna(media_json) or not isinstance(media_json, str) or media_json == "[]":
            return False
            
        try:
            media_list = json.loads(media_json)
            return any(item.get("type") == "video" for item in media_list)
        except:
            return False

    def _extract_image_info(self, media_json: str) -> bool:
        """Sprawdza czy tweet zawiera obrazy."""
        if pd.isna(media_json) or not isinstance(media_json, str) or media_json == "[]":
            return False
            
        try:
            media_list = json.loads(media_json)
            return any(item.get("type") in ["photo", "image"] for item in media_list)
        except:
            return False

    def _filter_content(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        """Filtruje nieciekawe lub niskiej jakości treści."""
        
        initial_count = len(df)
        
        # Usuń bardzo krótkie tweety (prawdopodobnie spam)
        df = df[df[text_col].str.len() >= 10]
        
        # Usuń tweety tylko z emoji (mało wartościowe)
        emoji_pattern = r'^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\s]+$'
        df = df[~df[text_col].str.match(emoji_pattern, na=False)]
        
        # Usuń tweety które są tylko retweetami bez dodatkowego komentarza
        rt_pattern = r'^RT @\w+:'
        df = df[~df[text_col].str.match(rt_pattern, na=False)]
        
        # Usuń tweety tylko z linkami (prawdopodobnie spam)
        link_only_pattern = r'^https?://\S+\s*$'
        df = df[~df[text_col].str.match(link_only_pattern, na=False)]
        
        filtered_count = initial_count - len(df)
        self.logger.info(f"Odfiltrowano {filtered_count} niskiej jakości tweetów")
        
        return df

    def prepare_for_processing(self, df: pd.DataFrame, analysis: Dict) -> pd.DataFrame:
        """Przygotowuje DataFrame do przetwarzania przez EnhancedContentProcessor."""
        
        config = self.format_configs[analysis["format"]]
        
        # Stwórz zunifikowane kolumny
        processed_df = pd.DataFrame()
        
        # ID (unikalne dla każdego wiersza)
        processed_df['id'] = range(1, len(df) + 1)
        
        # URL
        processed_df['url'] = df[config["url_col"]]
        
        # Tekst tweeta
        processed_df['tweet_text'] = df[config["text_col"]]
        
        # Autor
        if config["author_col"] in df.columns:
            processed_df['author'] = df[config["author_col"]]
        else:
            processed_df['author'] = "unknown"
        
        # Data
        if config["date_col"] in df.columns:
            processed_df['date'] = df[config["date_col"]]
        else:
            processed_df['date'] = datetime.now().isoformat()
        
        # Dodatkowe metadata jeśli dostępne
        if "has_video" in df.columns:
            processed_df['has_video'] = df['has_video']
        if "has_images" in df.columns:
            processed_df['has_images'] = df['has_images']
        if "favorite_count" in df.columns:
            processed_df['favorites'] = df['favorite_count'].fillna(0)
        if "retweet_count" in df.columns:
            processed_df['retweets'] = df['retweet_count'].fillna(0)
        
        # Oceń priorytet przetwarzania (najpierw te z najwięcej interakcji)
        if "favorites" in processed_df.columns and "retweets" in processed_df.columns:
            processed_df['engagement_score'] = processed_df['favorites'] + processed_df['retweets'] * 2
            processed_df = processed_df.sort_values('engagement_score', ascending=False)
        
        # Dodaj status przetwarzania
        processed_df['processing_status'] = 'pending'
        processed_df['processing_priority'] = range(1, len(processed_df) + 1)
        
        self.logger.info(f"Przygotowano {len(processed_df)} wierszy do przetwarzania")
        
        return processed_df

    def save_cleaned_data(self, df: pd.DataFrame, output_file: str) -> bool:
        """Zapisuje oczyszczone dane."""
        try:
            df.to_csv(output_file, index=False, encoding='utf-8')
            self.logger.info(f"Zapisano oczyszczone dane do: {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd zapisu: {e}")
            return False

    def create_processing_report(self, analysis: Dict, cleaned_count: int) -> Dict:
        """Tworzy raport z czyszczenia."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "input_analysis": analysis,
            "cleaned_count": cleaned_count,
            "reduction_ratio": (analysis["total_rows"] - cleaned_count) / analysis["total_rows"],
            "quality_improvement": "significant" if analysis["data_quality"] in ["poor", "moderate"] else "minor"
        }
        return report

    def process_csv_file(self, input_file: str, output_file: str = None) -> Tuple[pd.DataFrame, Dict]:
        """Główna funkcja - przetwarza plik CSV od początku do końca."""
        
        if not output_file:
            base_name = Path(input_file).stem
            output_file = f"{base_name}_cleaned.csv"
        
        self.logger.info(f"=== CZYSZCZENIE CSV: {input_file} ===")
        
        # 1. Załaduj i przeanalizuj
        df, analysis = self.load_and_analyze_csv(input_file)
        if df is None:
            return None, None
        
        # 2. Wyczyść dane
        cleaned_df = self.clean_dataframe(df, analysis)
        
        # 3. Przygotuj do przetwarzania
        processed_df = self.prepare_for_processing(cleaned_df, analysis)
        
        # 4. Zapisz wyniki
        if self.save_cleaned_data(processed_df, output_file):
            # 5. Stwórz raport
            report = self.create_processing_report(analysis, len(processed_df))
            
            self.logger.info(f"✅ SUKCES! {analysis['total_rows']} → {len(processed_df)} wierszy")
            self.logger.info(f"📁 Wynik: {output_file}")
            
            return processed_df, report
        else:
            return None, None


def main():
    """Test i demo systemu."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    cleaner = CSVCleanerAndPrep()
    
    # Sprawdź dostępne pliki CSV
    csv_files = ["bookmarks.csv", "bookmarks1.csv"]
    available_files = [f for f in csv_files if Path(f).exists()]
    
    if not available_files:
        print("❌ Brak plików CSV do przetworzenia!")
        return
    
    print(f"📁 Znalezione pliki: {available_files}")
    
    for csv_file in available_files:
        print(f"\n🔄 Przetwarzanie: {csv_file}")
        
        output_file = f"{Path(csv_file).stem}_cleaned.csv"
        result_df, report = cleaner.process_csv_file(csv_file, output_file)
        
        if result_df is not None:
            print(f"✅ Gotowe! Zapisano: {output_file}")
            print(f"📊 Redukcja: {report['reduction_ratio']:.1%}")
            print(f"🎯 Jakość: {report['quality_improvement']}")
        else:
            print(f"❌ Błąd przetwarzania {csv_file}")

if __name__ == "__main__":
    main() 