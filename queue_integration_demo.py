# queue_integration_demo.py
"""
Demo integracji Enhanced Smart Queue z istniejącym kodem
"""

import logging
from typing import Dict, List
from enhanced_smart_queue import EnhancedSmartProcessingQueue, PrioritizedTweet

logging.basicConfig(level=logging.INFO)

class ExistingQueue:
    """Symulacja istniejącej implementacji"""
    
    def prioritize_tweets(self, tweets: List[Dict]) -> List[Dict]:
        """Oryginalna funkcja użytkownika"""
        
        for tweet in tweets:
            score = 0
            
            # Wysoki priorytet dla:
            # - Tweetów z threadami
            if self._is_thread(tweet['text']):
                score += 10
            
            # - Tweetów z wysokim engagement
            score += (tweet.get('likes', 0) + tweet.get('retweets', 0) * 2) / 100
            
            # - Tweetów z konkretnymi domenami
            if any(domain in tweet['url'] for domain in ['github.com', 'arxiv.org', 'docs.']):
                score += 5
            
            # - Tweetów z obrazami (mogą zawierać dodatkowe info)
            if tweet.get('has_images'):
                score += 3
            
            tweet['priority_score'] = score
        
        return sorted(tweets, key=lambda x: x['priority_score'], reverse=True)
    
    def _is_thread(self, text: str) -> bool:
        """Podstawowa detekcja threadów"""
        import re
        return bool(re.search(r'(\d+/\d+|🧵|thread)', text, re.IGNORECASE))


def demo_comparison():
    """Demo porównujące stary i nowy system priorytetyzacji"""
    
    print("🔄 PORÓWNANIE SYSTEMÓW PRIORYTETYZACJI")
    print("=" * 70)
    
    # Test data
    sample_tweets = [
        {
            'text': '🧵 Amazing AI safety thread 1/7 with breakthrough research',
            'url': 'https://github.com/anthropic/safety',
            'likes': 1250,
            'retweets': 340,
            'has_images': True,
            'author': 'ai_researcher_phd'
        },
        {
            'text': 'Interesting web dev article',
            'url': 'https://medium.com/some-article',
            'likes': 45,
            'retweets': 12,
            'has_images': False,
            'author': 'webdev_guy'
        },
        {
            'text': 'Breaking: New Python 3.12 release with awesome features!',
            'url': 'https://docs.python.org/3.12/',
            'likes': 2340,
            'retweets': 890,
            'has_images': False,
            'author': 'python_core_dev'
        },
        {
            'text': 'Check out this paywall article about tech',
            'url': 'https://nytimes.com/some-paywall-article',
            'likes': 23,
            'retweets': 5,
            'has_images': False,
            'author': 'news_aggregator'
        },
        {
            'text': 'Tutorial: How to master Docker in 2024',
            'url': 'https://dev.to/docker-tutorial',
            'likes': 567,
            'retweets': 123,
            'has_images': True,
            'author': 'docker_expert'
        }
    ]
    
    # Test starego systemu
    print("📊 STARY SYSTEM:")
    old_queue = ExistingQueue()
    old_results = old_queue.prioritize_tweets(sample_tweets.copy())
    
    print(f"{'Pozycja':<8} {'Score':<8} {'URL':<40} {'Powód'}")
    print("-" * 70)
    
    for i, tweet in enumerate(old_results, 1):
        score = tweet.get('priority_score', 0)
        url_short = tweet['url'][:37] + '...' if len(tweet['url']) > 40 else tweet['url']
        
        # Analiza powodów (uproszczona)
        reasons = []
        if old_queue._is_thread(tweet['text']):
            reasons.append("Thread")
        if tweet.get('has_images'):
            reasons.append("Images")
        if any(d in tweet['url'] for d in ['github.com', 'docs.']):
            reasons.append("Priority domain")
        
        print(f"{i:<8} {score:<8.1f} {url_short:<40} {', '.join(reasons)}")
    
    print("\n" + "=" * 70)
    
    # Test nowego systemu
    print("🚀 NOWY ENHANCED SYSTEM:")
    new_queue = EnhancedSmartProcessingQueue()
    new_results = new_queue.prioritize_tweets(sample_tweets.copy())
    
    print(f"{'Pos':<4} {'Score':<8} {'Urgency':<9} {'Type':<12} {'Time':<6} {'URL':<25} {'Główne powody'}")
    print("-" * 100)
    
    for i, tweet in enumerate(new_results, 1):
        score = tweet.priority_score
        urgency = tweet.urgency_level.name
        content_type = tweet.content_type.value
        time_est = f"{tweet.estimated_processing_time}s"
        url_short = tweet.original_data['url'][:22] + '...' if len(tweet.original_data['url']) > 25 else tweet.original_data['url']
        
        # Top 2 powody
        top_reasons = ', '.join(tweet.reasons[:2])
        if len(top_reasons) > 35:
            top_reasons = top_reasons[:32] + '...'
        
        print(f"{i:<4} {score:<8.1f} {urgency:<9} {content_type:<12} {time_est:<6} {url_short:<25} {top_reasons}")
    
    # Analytics nowego systemu
    analytics = new_queue.get_priority_analytics(new_results)
    
    print(f"\n📈 ANALYTICS NOWEGO SYSTEMU:")
    print(f"   Łączny szacowany czas: {analytics['estimated_total_time_minutes']:.1f} minut")
    print(f"   Rozkład urgency: {analytics['urgency_distribution']}")
    print(f"   Rozkład typów treści: {analytics['content_type_distribution']}")
    
    # Porównanie wyników
    print(f"\n🔍 ANALIZA RÓŻNIC:")
    
    # Sprawdź czy kolejność się zmieniła
    old_urls = [t['url'] for t in old_results]
    new_urls = [t.original_data['url'] for t in new_results]
    
    if old_urls != new_urls:
        print("   ✅ Kolejność priorytetów się zmieniła!")
        
        # Znajdź największe zmiany
        for i, old_url in enumerate(old_urls):
            try:
                new_pos = new_urls.index(old_url)
                if abs(i - new_pos) >= 2:  # Znacząca zmiana pozycji
                    direction = "↑" if new_pos < i else "↓"
                    print(f"   {direction} {old_url[:50]}... przesunął się z pozycji {i+1} na {new_pos+1}")
            except ValueError:
                continue
    else:
        print("   ℹ️ Kolejność pozostała taka sama")
    
    # Korzyści nowego systemu
    print(f"\n💡 KORZYŚCI NOWEGO SYSTEMU:")
    print("   🎯 Więcej kryteriów priorytetyzacji (słowa kluczowe, autor, czas)")
    print("   📊 Szczegółowe powody każdego priorytetu")
    print("   🏷️ Kategoryzacja typów treści")
    print("   ⏱️ Szacowanie czasu przetwarzania")
    print("   📈 Bogate analytics i metryki")
    print("   🔧 Łatwa konfiguracja priorytetów")
    print("   🚫 Identyfikacja problematycznych domen")


def simple_migration_example():
    """Prosty przykład migracji kodu"""
    
    print("\n📋 PRZYKŁAD MIGRACJI KODU:")
    print("=" * 50)
    
    print("❌ PRZED (oryginalny kod):")
    print("""
class SmartProcessingQueue:
    def prioritize_tweets(self, tweets: List[Dict]) -> List[Dict]:
        for tweet in tweets:
            score = 0
            if self._is_thread(tweet['text']):
                score += 10
            # ... więcej kryteriów
            tweet['priority_score'] = score
        return sorted(tweets, key=lambda x: x['priority_score'], reverse=True)
""")
    
    print("✅ PO (z Enhanced system):")
    print("""
from enhanced_smart_queue import EnhancedSmartProcessingQueue

class SmartProcessingQueue:
    def __init__(self):
        self.enhanced_queue = EnhancedSmartProcessingQueue()
    
    def prioritize_tweets(self, tweets: List[Dict]) -> List[Dict]:
        # Opcja 1: Kompatybilność z oryginalnym API
        return self.enhanced_queue.get_processing_order(tweets)
        
        # Opcja 2: Wykorzystaj pełne możliwości
        prioritized = self.enhanced_queue.prioritize_tweets(tweets)
        return [pt.original_data for pt in prioritized]
""")
    
    print("🚀 DODATKOWE MOŻLIWOŚCI:")
    print("""
# Szczegółowa analiza priorytetów
prioritized = queue.prioritize_tweets(tweets)
for tweet in prioritized:
    print(f"Score: {tweet.priority_score}")
    print(f"Urgency: {tweet.urgency_level.name}")
    print(f"Type: {tweet.content_type.value}")
    print(f"Reasons: {tweet.reasons}")

# Analytics
analytics = queue.get_priority_analytics(prioritized)
print(f"Total time: {analytics['estimated_total_time_minutes']:.1f} min")
""")


def performance_comparison():
    """Porównanie wydajności"""
    
    print("\n⚡ PORÓWNANIE WYDAJNOŚCI:")
    print("=" * 40)
    
    import time
    
    # Większy zestaw testowy
    large_tweets = []
    for i in range(100):
        large_tweets.append({
            'text': f'Test tweet {i} with various content',
            'url': f'https://example{i % 10}.com/article',
            'likes': i * 10,
            'retweets': i * 2,
            'has_images': i % 3 == 0,
            'author': f'user_{i}'
        })
    
    # Test starego systemu
    old_queue = ExistingQueue()
    start_time = time.time()
    old_results = old_queue.prioritize_tweets(large_tweets.copy())
    old_time = time.time() - start_time
    
    # Test nowego systemu
    new_queue = EnhancedSmartProcessingQueue()
    start_time = time.time()
    new_results = new_queue.prioritize_tweets(large_tweets.copy())
    new_time = time.time() - start_time
    
    print(f"📊 WYNIKI dla {len(large_tweets)} tweetów:")
    print(f"   Stary system: {old_time:.3f}s")
    print(f"   Nowy system: {new_time:.3f}s")
    print(f"   Różnica: {((new_time - old_time) / old_time * 100):+.1f}%")
    
    if new_time > old_time:
        print("   💡 Nowy system jest wolniejszy, ale oferuje znacznie więcej funkcji")
    else:
        print("   🚀 Nowy system jest szybszy i ma więcej funkcji!")


if __name__ == "__main__":
    demo_comparison()
    simple_migration_example()
    performance_comparison()