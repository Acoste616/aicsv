"""
Centralna konfiguracja systemu analizy zakładek
"""

# Model LLM
LLM_CONFIG = {
    "api_url": "http://localhost:1234/v1/chat/completions",
    "model_name": "mistralai/mistral-7b-instruct-v0.3",  # Najlepszy dla RTX 4050
    "temperature": 0.1,  # Bardzo niska dla konsystentności JSON
    "max_tokens": 600,   # Wystarczające dla struktury JSON
    "timeout": 30,
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
    "timeout": 15,
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