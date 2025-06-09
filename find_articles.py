#!/usr/bin/env python3
"""
Szuka tweetów z prawdziwymi artykułami
"""

import pandas as pd
import re
import requests

def main():
    df = pd.read_csv('bookmarks_cleaned.csv')
    
    print("🔍 Szukam tweetów z prawdziwymi artykułami...")
    print("=" * 50)
    
    found_articles = 0
    
    for i in range(min(30, len(df))):  # Sprawdź pierwsze 30
        tweet = df.iloc[i]['tweet_text']
        urls = re.findall(r'https?://[^\s]+', tweet)
        
        for url in urls:
            if 't.co' in url:
                try:
                    response = requests.get(url, allow_redirects=True, timeout=5)
                    final = response.url
                    
                    # Sprawdź czy to artykuł
                    article_indicators = [
                        'github.com', 'medium.com', 'dev.to', 'blog', 
                        'article', 'docs', 'documentation', 'tutorial',
                        'substack.com', 'notion.so', 'hackernoon.com'
                    ]
                    
                    if any(indicator in final.lower() for indicator in article_indicators):
                        print(f"\n✅ Tweet {i+1}: {tweet[:60]}...")
                        print(f"   🔗 Link: {final}")
                        found_articles += 1
                        break
                        
                except Exception as e:
                    continue
    
    print(f"\n📊 Znaleziono {found_articles} tweetów z artykułami w pierwszych 30")
    
    if found_articles > 0:
        print("\n💡 Uruchom analizę na tych tweetach!")
    else:
        print("\n⚠️ Brak artykułów w pierwszych 30 tweetach")
        print("   System będzie analizował głównie tweety z obrazami/wideo")

if __name__ == "__main__":
    main() 