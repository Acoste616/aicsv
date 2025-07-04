"""
Centralna konfiguracja systemu analizy zakładek - Optimized for Cloud LLM
"""

# Model LLM - Optimized for Cloud LLM
LLM_CONFIG = {
    "api_url": "http://localhost:1234/v1/chat/completions",
    "model_name": "gpt-4",  # Zoptymalizowane dla GPT-4 z JSON mode
    "temperature": 0.1,     # Bardzo niska dla konsystencji JSON (OPTIMIZED)
    "max_tokens": 1500,     # Zoptymalizowane dla krótszych promptów
    "timeout": 30,          # Zmniejszone dla szybszych odpowiedzi
    "retry_attempts": 3,    # Zwiększone dla większej niezawodności
    "response_format": {"type": "json_object"},  # JSON mode dla GPT-4
    "use_fallback_prompts": True,  # Włącz fallback prompts
    "prompt_optimization": {
        "use_few_shot": True,
        "max_examples": 2,
        "compress_input": True,
        "max_input_length": 500
    }
}

# Cloud LLM Alternatives
CLOUD_LLM_CONFIGS = {
    "gpt-4": {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "supports_json_mode": True,
        "temperature": 0.1,
        "max_tokens": 1500
    },
    "gpt-3.5-turbo": {
        "api_url": "https://api.openai.com/v1/chat/completions", 
        "supports_json_mode": True,
        "temperature": 0.1,
        "max_tokens": 1200
    },
    "claude-3-sonnet": {
        "api_url": "https://api.anthropic.com/v1/messages",
        "supports_json_mode": False,
        "temperature": 0.1,
        "max_tokens": 1500
    }
}

# Pipeline - Optimized for faster processing
PIPELINE_CONFIG = {
    "batch_size": 1,  # Przetwarzaj po jednym dla stabilności
    "checkpoint_frequency": 3,  # Częstsze zapisywanie (zmniejszone z 5 do 3)
    "quality_threshold": 0.3,  # Zwiększony próg jakości
    "enable_duplicates_check": True,   # Włącz dla lepszej jakości
    "enable_quality_validation": True,  # Włącz dla lepszej jakości
    "max_retries_per_item": 3,  # Maksymalna liczba prób na element
    "use_optimized_prompts": True  # Użyj zoptymalizowanych promptów
}

# Content Extraction - Optimized
EXTRACTION_CONFIG = {
    "timeout": 8,                # Zmniejszone dla szybszego przetwarzania
    "max_retries": 2,           # Zwiększone dla niezawodności
    "twitter_fallback": True,   # Używaj tylko tekstu tweeta dla Twitter/X
    "min_content_length": 30,   # Zwiększone minimum dla lepszej jakości
    "max_content_length": 1000, # Ograniczenie dla krótszych promptów
    "smart_truncation": True    # Inteligentne obcinanie treści
}

# Output
OUTPUT_CONFIG = {
    "output_dir": "output",
    "knowledge_base_file": "knowledge_base.json",
    "failed_tweets_file": "failed_tweets.json",
    "optimization_stats_file": "optimization_stats.json",  # Nowy plik ze statystykami
}

# Multimodal Processing - Optimized
MULTIMODAL_CONFIG = {
    "enable_ocr": True,
    "enable_thread_collection": True,
    "enable_video_metadata": True,
    "ocr_languages": ["en", "pl"],
    "max_thread_length": 30,    # Zmniejszone z 50 do 30 dla szybszego przetwarzania
    "image_timeout": 10,        # Zmniejszone z 15 do 10 sekund
    "concurrent_workers": 6,    # Zmniejszone z 8 do 6 dla stabilności
    "cache_extracted_media": True,
    "cache_dir": "media_cache",
    "smart_content_selection": True,  # Inteligentny wybór najważniejszych treści
    "max_images_per_tweet": 3,       # Ograniczenie liczby obrazów
    "max_video_duration": 300        # Maksymalny czas wideo (5 min)
}

# OCR Configuration - Optimized
OCR_CONFIG = {
    "tesseract_path": None,  # Auto-detect
    "preprocessing": True,
    "image_formats": [".jpg", ".png", ".webp"],
    "max_image_size_mb": 5,  # Zmniejszone z 10 do 5 MB
    "quality_threshold": 0.7,  # Próg jakości OCR
    "fast_mode": True  # Szybki tryb OCR
}

# Prompt Optimization Settings
PROMPT_CONFIG = {
    "optimization_level": "aggressive",  # "conservative", "moderate", "aggressive"
    "max_prompt_length": 800,  # Maksymalna długość promptu
    "min_prompt_length": 200,  # Minimalna długość promptu
    "use_compression": True,   # Używaj kompresji treści
    "fallback_strategy": "hierarchical",  # "simple", "hierarchical"
    "few_shot_examples": 2,    # Liczba przykładów w few-shot
    "include_context": True,   # Dołącz kontekst do przykładów
    "optimize_for_json": True, # Optymalizuj dla JSON output
    "enable_smart_truncation": True,  # Inteligentne obcinanie
    "priority_fields": ["title", "category", "tags", "description"]  # Priorytetowe pola
} 