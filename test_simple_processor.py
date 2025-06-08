#!/usr/bin/env python3
"""
Prosty test naprawionego bookmark processor
"""

import json
from bookmark_processor_fixed import OptimizedBookmarkProcessor

def test_single_tweet():
    """Test pojedynczego tweeta"""
    print("🧪 TEST POJEDYNCZEGO TWEETA")
    print("=" * 50)
    
    processor = OptimizedBookmarkProcessor()
    
    # Test tweet z linkiem
    test_tweet = {
        'id': '1234567890',
        'full_text': 'Test tweet z linkiem https://t.co/testlink',
        'created_at': '2024-01-01'
    }
    
    print(f"📝 Testuję tweet: {test_tweet['full_text']}")
    
    try:
        result = processor.analyze_tweet_optimized(test_tweet)
        
        if result:
            print("✅ SUKCES!")
            print(f"📊 Wynik: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print("❌ NIEPOWODZENIE - brak wyniku")
            
    except Exception as e:
        print(f"💥 BŁĄD: {e}")
    
    finally:
        processor.extractor.close()

if __name__ == "__main__":
    test_single_tweet() 