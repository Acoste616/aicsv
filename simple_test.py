#!/usr/bin/env python3
"""
Prosty test systemu na 3 przykładowych tweetach
"""

import pandas as pd
import json
from pathlib import Path
from fixed_master_pipeline import FixedMasterPipeline

def create_test_data():
    """Tworzy mały plik CSV do testów"""
    test_data = {
        'url': [
            'https://github.com/langchain-ai/langchain',
            'https://x.com/test/status/123456',  
            'https://openai.com/blog/chatgpt'
        ],
        'tweet_text': [
            'Amazing LangChain tutorial for building RAG systems! Must read for AI developers',
            'Just launched our new AI product! Check it out',
            'ChatGPT updates are incredible, the new features are game changing'
        ]
    }
    
    df = pd.DataFrame(test_data)
    df.to_csv('test_data_3.csv', index=False)
    print("✅ Utworzono test_data_3.csv")
    return 'test_data_3.csv'

def main():
    print("🧪 PROSTY TEST SYSTEMU")
    print("=" * 50)
    
    # Stwórz dane testowe
    test_file = create_test_data()
    
    # Uruchom pipeline
    pipeline = FixedMasterPipeline()
    result = pipeline.process_csv(test_file)
    
    # Sprawdź wyniki
    print("\n📊 WYNIKI:")
    print(f"Przetworzono: {result['total_processed']}")
    print(f"Sukces: {result['successful']}")
    print(f"Błędy: {result['failed']}")
    
    # Sprawdź output
    if result['successful'] > 0:
        with open(result['output_file'], 'r') as f:
            output = json.load(f)
            
        print("\n✅ PRZYKŁADOWE WYNIKI:")
        for i, entry in enumerate(output['entries'][:3]):
            print(f"\n📌 Wpis {i+1}:")
            print(f"  Tytuł: {entry.get('title', 'BRAK')}")
            print(f"  Kategoria: {entry.get('category', 'BRAK')}")
            print(f"  Tagi: {entry.get('tags', [])}")

if __name__ == "__main__":
    main() 