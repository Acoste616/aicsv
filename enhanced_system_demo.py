# enhanced_system_demo.py
"""
Demo pokazujące użycie ulepszonego systemu z Enhanced Content Strategy
"""

import logging
import json
import time
from typing import Dict, List, Optional
from enhanced_content_strategy import EnhancedContentStrategy
from adaptive_prompts import AdaptivePromptGenerator
from smart_queue import SmartProcessingQueue, ProcessingPriority

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class EnhancedAnalysisSystem:
    """
    Zintegrowany system analizy z ulepszonymi strategiami
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Główne komponenty
        self.content_strategy = EnhancedContentStrategy()
        self.prompt_generator = AdaptivePromptGenerator()
        self.processing_queue = SmartProcessingQueue()
        
        # Statistyki
        self.stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'by_quality': {'high': 0, 'medium': 0, 'low': 0},
            'by_source': {},
            'processing_times': []
        }
        
        self.logger.info("[System] Enhanced Analysis System zainicjalizowany")

    def analyze_tweet_batch(self, tweets: List[Dict], focus_area: Optional[str] = None) -> Dict:
        """
        Analizuje batch tweetów z inteligentną priorytetyzacją
        
        Args:
            tweets: Lista tweetów z polami: url, text, (opcjonalnie) author, likes, retweets
            focus_area: Obszar zainteresowania (technical, research, news)
            
        Returns:
            Szczegółowy raport z analizą
        """
        self.logger.info(f"[System] Rozpoczynam analizę {len(tweets)} tweetów")
        
        # 1. Dodaj wszystkie tweety do kolejki z priorytetyzacją
        for tweet in tweets:
            self.processing_queue.add_item(
                url=tweet.get('url', ''),
                tweet_text=tweet.get('text', ''),
                tweet_data=tweet
            )
        
        # 2. Przetwarzaj kolejkę
        results = []
        failed_items = []
        
        while True:
            item = self.processing_queue.get_next_item()
            if not item:
                break
            
            self.logger.info(f"[System] Przetwarzam: {item.id} (priorytet: {item.priority.name})")
            
            try:
                # Pobierz treść używając Enhanced Content Strategy
                start_time = time.time()
                content_data = self.content_strategy.get_content(
                    item.url, 
                    item.tweet_text
                )
                processing_time = time.time() - start_time
                
                # Wygeneruj adaptacyjny prompt
                prompt = self.prompt_generator.generate_prompt(
                    content_data, 
                    analysis_type=focus_area or 'general'
                )
                
                # Tu byłoby wywołanie LLM z promptem
                # llm_result = call_llm(prompt)
                # Na razie symulujemy
                llm_result = self._simulate_llm_analysis(content_data, item.category)
                
                result = {
                    'item_id': item.id,
                    'url': item.url,
                    'tweet_text': item.tweet_text,
                    'priority': item.priority.name,
                    'priority_score': item.priority_score,
                    'category': item.category,
                    'content_quality': content_data['quality'],
                    'content_source': content_data['source'],
                    'confidence': content_data.get('confidence', 0.0),
                    'processing_time': processing_time,
                    'analysis': llm_result,
                    'content_length': len(content_data.get('content', '')),
                    'prompt_used': prompt[:200] + '...'  # Pierwsze 200 znaków
                }
                
                results.append(result)
                self.processing_queue.mark_completed(item.id, True)
                self._update_stats(result, True)
                
                self.logger.info(f"[System] ✓ Sukces: {item.id} ({content_data['quality']} quality)")
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"[System] ✗ Błąd {item.id}: {error_msg}")
                
                failed_items.append({
                    'item_id': item.id,
                    'url': item.url,
                    'error': error_msg,
                    'category': item.category
                })
                
                self.processing_queue.mark_completed(item.id, False, error_msg)
                self._update_stats(None, False)
        
        # 3. Generuj raport
        report = self._generate_comprehensive_report(results, failed_items, focus_area)
        
        self.logger.info(f"[System] Analiza zakończona: {len(results)} sukces, {len(failed_items)} błędów")
        return report

    def _simulate_llm_analysis(self, content_data: Dict, category: str) -> Dict:
        """Symuluje analizę LLM (placeholder)"""
        quality = content_data['quality']
        source = content_data['source']
        
        # Symuluj różne odpowiedzi w zależności od jakości
        if quality == 'high':
            return {
                'title': 'Szczegółowy artykuł techniczny',
                'category': 'technical',
                'educational_value': 8,
                'key_points': ['Punkt 1', 'Punkt 2', 'Punkt 3'],
                'confidence_level': 0.9
            }
        elif quality == 'medium':
            return {
                'title': 'Artykuł na podstawie metadanych',
                'category': category,
                'estimated_value': 6,
                'confidence_level': 0.6,
                'worth_investigating': True
            }
        else:
            return {
                'inferred_topic': 'Temat na podstawie tweeta',
                'category_guess': category,
                'potential_value': 4,
                'confidence_level': 0.3,
                'investigation_priority': 'medium'
            }

    def _update_stats(self, result: Optional[Dict], success: bool):
        """Aktualizuje statystyki"""
        self.stats['processed'] += 1
        
        if success:
            self.stats['successful'] += 1
            if result:
                # Statystyki jakości
                quality = result['content_quality']
                self.stats['by_quality'][quality] += 1
                
                # Statystyki źródeł
                source = result['content_source']
                if source not in self.stats['by_source']:
                    self.stats['by_source'][source] = 0
                self.stats['by_source'][source] += 1
                
                # Czasy przetwarzania
                self.stats['processing_times'].append(result['processing_time'])
        else:
            self.stats['failed'] += 1

    def _generate_comprehensive_report(self, results: List[Dict], failed_items: List[Dict], focus_area: Optional[str]) -> Dict:
        """Generuje kompleksowy raport"""
        
        # Sortuj wyniki według priorytetu i jakości
        results.sort(key=lambda x: (
            ProcessingPriority[x['priority']].value,
            {'high': 3, 'medium': 2, 'low': 1}[x['content_quality']],
            x['confidence']
        ), reverse=True)
        
        # Analizy
        quality_distribution = self._analyze_quality_distribution(results)
        source_analysis = self._analyze_sources(results)
        priority_effectiveness = self._analyze_priority_effectiveness(results)
        content_categories = self._analyze_content_categories(results)
        
        # Rekomendacje
        recommendations = self._generate_recommendations(results, failed_items)
        
        report = {
            'summary': {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'focus_area': focus_area,
                'total_items': len(results) + len(failed_items),
                'successful': len(results),
                'failed': len(failed_items),
                'success_rate': len(results) / (len(results) + len(failed_items)) if results or failed_items else 0,
                'avg_processing_time': sum(self.stats['processing_times']) / len(self.stats['processing_times']) if self.stats['processing_times'] else 0
            },
            
            'quality_analysis': quality_distribution,
            'source_analysis': source_analysis,
            'priority_analysis': priority_effectiveness,
            'content_categories': content_categories,
            
            'top_results': results[:10],  # Top 10 wyników
            'failed_analysis': self._analyze_failures(failed_items),
            
            'recommendations': recommendations,
            'queue_status': self.processing_queue.get_status(),
            
            'detailed_results': results,
            'failed_items': failed_items
        }
        
        return report

    def _analyze_quality_distribution(self, results: List[Dict]) -> Dict:
        """Analizuje rozkład jakości treści"""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        confidence_by_quality = {'high': [], 'medium': [], 'low': []}
        
        for result in results:
            quality = result['content_quality']
            distribution[quality] += 1
            confidence_by_quality[quality].append(result['confidence'])
        
        return {
            'distribution': distribution,
            'avg_confidence_by_quality': {
                q: sum(conf) / len(conf) if conf else 0 
                for q, conf in confidence_by_quality.items()
            }
        }

    def _analyze_sources(self, results: List[Dict]) -> Dict:
        """Analizuje źródła treści"""
        sources = {}
        for result in results:
            source = result['content_source']
            if source not in sources:
                sources[source] = {
                    'count': 0,
                    'avg_confidence': 0,
                    'qualities': {'high': 0, 'medium': 0, 'low': 0}
                }
            
            sources[source]['count'] += 1
            sources[source]['qualities'][result['content_quality']] += 1
        
        return sources

    def _analyze_priority_effectiveness(self, results: List[Dict]) -> Dict:
        """Analizuje skuteczność priorytetyzacji"""
        by_priority = {}
        
        for result in results:
            priority = result['priority']
            if priority not in by_priority:
                by_priority[priority] = {
                    'count': 0,
                    'avg_quality_score': 0,
                    'avg_confidence': 0,
                    'avg_processing_time': 0
                }
            
            item = by_priority[priority]
            item['count'] += 1
            
            # Konwertuj jakość na score
            quality_scores = {'high': 3, 'medium': 2, 'low': 1}
            item['avg_quality_score'] += quality_scores[result['content_quality']]
            item['avg_confidence'] += result['confidence']
            item['avg_processing_time'] += result['processing_time']
        
        # Oblicz średnie
        for priority, data in by_priority.items():
            count = data['count']
            data['avg_quality_score'] /= count
            data['avg_confidence'] /= count
            data['avg_processing_time'] /= count
        
        return by_priority

    def _analyze_content_categories(self, results: List[Dict]) -> Dict:
        """Analizuje kategorie treści"""
        categories = {}
        
        for result in results:
            category = result['category']
            if category not in categories:
                categories[category] = {
                    'count': 0,
                    'quality_distribution': {'high': 0, 'medium': 0, 'low': 0},
                    'avg_confidence': 0
                }
            
            categories[category]['count'] += 1
            categories[category]['quality_distribution'][result['content_quality']] += 1
            categories[category]['avg_confidence'] += result['confidence']
        
        # Oblicz średnie
        for category, data in categories.items():
            data['avg_confidence'] /= data['count']
        
        return categories

    def _analyze_failures(self, failed_items: List[Dict]) -> Dict:
        """Analizuje niepowodzenia"""
        error_types = {}
        categories_affected = {}
        
        for item in failed_items:
            # Kategoryzuj błąd
            error = item['error'].lower()
            if 'paywall' in error:
                error_type = 'paywall'
            elif 'timeout' in error:
                error_type = 'timeout'
            elif '403' in error or 'forbidden' in error:
                error_type = 'forbidden'
            else:
                error_type = 'other'
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            category = item['category']
            categories_affected[category] = categories_affected.get(category, 0) + 1
        
        return {
            'error_types': error_types,
            'categories_affected': categories_affected,
            'total_failed': len(failed_items)
        }

    def _generate_recommendations(self, results: List[Dict], failed_items: List[Dict]) -> List[str]:
        """Generuje rekomendacje"""
        recommendations = []
        
        if not results and not failed_items:
            return ["Brak danych do analizy"]
        
        total = len(results) + len(failed_items)
        success_rate = len(results) / total if total > 0 else 0
        
        # Analiza success rate
        if success_rate < 0.5:
            recommendations.append("Niski success rate - rozważ rewizję strategii pozyskiwania treści")
        
        # Analiza jakości
        high_quality = len([r for r in results if r['content_quality'] == 'high'])
        if high_quality / len(results) < 0.3 if results else True:
            recommendations.append("Mało treści wysokiej jakości - sprawdź domeny i źródła")
        
        # Analiza błędów
        paywall_errors = len([f for f in failed_items if 'paywall' in f['error'].lower()])
        if paywall_errors > len(failed_items) * 0.3:
            recommendations.append("Dużo błędów paywall - implementuj alternatywne strategie")
        
        # Analiza priorytetów
        urgent_items = [r for r in results if r['priority'] == 'URGENT']
        if urgent_items and all(r['content_quality'] == 'low' for r in urgent_items):
            recommendations.append("Elementy URGENT dają niską jakość - sprawdź algorytm priorytetyzacji")
        
        return recommendations

    def export_report(self, report: Dict, filename: str = None):
        """Eksportuje raport do pliku"""
        if not filename:
            filename = f"enhanced_analysis_report_{int(time.time())}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"[System] Raport wyeksportowany: {filename}")
        return filename

    def get_system_status(self) -> Dict:
        """Zwraca status systemu"""
        return {
            'content_strategy_cache_size': len(self.content_strategy.cache),
            'queue_status': self.processing_queue.get_status(),
            'processing_stats': self.stats,
            'recommendations': self.processing_queue.get_recommendations() if hasattr(self.processing_queue, 'get_recommendations') else []
        }


def demo_enhanced_system():
    """Demo użycia ulepszonego systemu"""
    
    # Przykładowe dane
    sample_tweets = [
        {
            'url': 'https://github.com/microsoft/vscode',
            'text': 'Świetny edytor kodu! 🔥 #programming #vscode',
            'author': 'dev_user',
            'likes': 150,
            'retweets': 45
        },
        {
            'url': 'https://arxiv.org/abs/2023.12345',
            'text': 'Interesting paper on AI safety 1/3 🧵',
            'author': 'researcher',
            'likes': 89,
            'retweets': 23
        },
        {
            'url': 'https://blog.openai.com/some-article',
            'text': 'New developments in language models...',
            'author': 'ai_news',
            'likes': 234,
            'retweets': 67
        },
        {
            'url': 'https://nytimes.com/paywall-article',
            'text': 'Breaking news about tech industry',
            'author': 'news_bot',
            'likes': 45,
            'retweets': 12
        }
    ]
    
    # Inicjalizuj system
    system = EnhancedAnalysisSystem()
    
    # Analizuj tweety
    print("🚀 Rozpoczynam analizę z Enhanced System...")
    report = system.analyze_tweet_batch(sample_tweets, focus_area='technical')
    
    # Wyświetl podsumowanie
    print("\n📊 PODSUMOWANIE ANALIZY:")
    print(f"✅ Sukces: {report['summary']['successful']}")
    print(f"❌ Błędy: {report['summary']['failed']}")
    print(f"⚡ Success rate: {report['summary']['success_rate']:.1%}")
    print(f"⏱️ Średni czas: {report['summary']['avg_processing_time']:.2f}s")
    
    print("\n🎯 JAKOŚĆ TREŚCI:")
    for quality, count in report['quality_analysis']['distribution'].items():
        print(f"  {quality}: {count}")
    
    print("\n🔍 ŹRÓDŁA TREŚCI:")
    for source, data in report['source_analysis'].items():
        print(f"  {source}: {data['count']} elementów")
    
    print("\n💡 REKOMENDACJE:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    # Eksportuj raport
    filename = system.export_report(report)
    print(f"\n📁 Raport zapisany: {filename}")
    
    return report


if __name__ == "__main__":
    # Uruchom demo
    demo_enhanced_system()