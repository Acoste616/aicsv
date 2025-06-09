#!/usr/bin/env python3
"""
Sprawdza URL-e w pierwszych 5 tweetach i rozwijania t.co linki
"""

import pandas as pd
import re
import requests

def expand_tco_link(tco_url):
    """Rozwijanie t.co linków"""
    try:
        response = requests.get(tco_url, allow_redirects=True, timeout=10)
        final_url = response.url
        
        if final_url != tco_url and 't.co' not in final_url:
            return final_url, response.status_code
        else:
            return tco_url, response.status_code
    except Exception as e:
        return tco_url, f"Error: {e}"

def main():
    df = pd.read_csv('bookmarks_cleaned.csv')
    
    print("🔍 SPRAWDZANIE I ROZWIJANIE URL-ów:")
    print("=" * 60)
    
    for i in range(5):
        tweet = df.iloc[i]['tweet_text']
        urls = re.findall(r'https?://[^\s]+', tweet)
        
        print(f"\n📝 Tweet {i+1}:")
        print(f"Tekst: {tweet[:80]}...")
        print(f"URL-e: {urls}")
        
        for url in urls:
            if 't.co' in url:
                print(f"  🔄 Rozwijam: {url}")
                expanded, status = expand_tco_link(url)
                print(f"  ➡️ Rozwinięto do: {expanded} (Status: {status})")
                
                # Sprawdź czy to artykuł czy media
                if any(domain in expanded.lower() for domain in ['github.com', 'medium.com', 'dev.to', 'blog', 'article']):
                    print(f"  ✅ To może być artykuł!")
                elif any(domain in expanded.lower() for domain in ['x.com', 'twitter.com']):
                    if '/video/' in expanded or '/photo/' in expanded:
                        print(f"  📹 To media Twitter/X")
                    else:
                        print(f"  🐦 To tweet Twitter/X")
                else:
                    print(f"  ❓ Nieznany typ treści")
            else:
                print(f"  ➡️ Bezpośredni link: {url}")

if __name__ == "__main__":
    main() 