"""
Centralna konfiguracja systemu analizy zakładek
"""

# Model LLM
LLM_CONFIG = {
    "api_url": "http://localhost:1234/v1/chat/completions",
    "model_name": "mistralai/mistral-7b-instruct-v0.3",  # Najlepszy dla RTX 4050
    "temperature": 0.1,  # Bardzo niska dla konsystentności JSON
    "max_tokens": 2000,   # Zwiększone z 600 do 2000 dla pełnych JSON-ów
    "timeout": 45,        # Zwiększone z 30 do 45 sekund
    "retry_attempts": 2
}

# Pipeline
PIPELINE_CONFIG = {
    "batch_size": 1,  # Przetwarzaj po jednym dla stabilności
    "checkpoint_frequency": 5,  # Zapisuj co 5 wpisów
    "quality_threshold": 0.2,  # Bardzo niski próg
    "enable_duplicates_check": False,  # Wyłącz na razie
    "enable_quality_validation": False,  # Wyłącz na razie
}

# Content Extraction
EXTRACTION_CONFIG = {
    "timeout": 10,               # Zmniejszone z 15 do 10 sekund
    "max_retries": 1,
    "twitter_fallback": True,  # Używaj tylko tekstu tweeta dla Twitter/X
    "min_content_length": 20,  # Bardzo niskie minimum
}

# Output
OUTPUT_CONFIG = {
    "output_dir": "output",
    "knowledge_base_file": "knowledge_base.json",
    "failed_tweets_file": "failed_tweets.json",
}

# Multimodal Processing
MULTIMODAL_CONFIG = {
    "enable_ocr": True,
    "enable_thread_collection": True,
    "enable_video_metadata": True,
    "ocr_languages": ["en", "pl"],
    "max_thread_length": 50,
    "image_timeout": 15,         # Zmniejszone z 30 do 15 sekund
    "concurrent_workers": 8,     # Zwiększone z 4 do 8 
    "cache_extracted_media": True,
    "cache_dir": "media_cache"
}

# OCR Configuration
OCR_CONFIG = {
    "tesseract_path": None,  # Auto-detect
    "preprocessing": True,
    "image_formats": [".jpg", ".png", ".webp"],
    "max_image_size_mb": 10
} 