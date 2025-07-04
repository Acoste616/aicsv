"""
Rozszerzona analiza z rzeczywistym przetwarzaniem LLM
"""

import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# Import lokalnych modułów
from config import LLM_CONFIG, MULTIMODAL_CONFIG
from content_extractor import ContentExtractor
from multimodal_pipeline import MultimodalKnowledgePipeline, ImageContentExtractor
from adaptive_prompts import AdaptivePromptGenerator

class RealTimeAnalyzer:
    """Klasa do rzeczywistej analizy w czasie rzeczywistym"""
    
    def __init__(self, provider_config: Dict):
        self.provider_config = provider_config
        self.content_extractor = ContentExtractor()
        self.image_extractor = ImageContentExtractor()
        self.prompt_generator = AdaptivePromptGenerator()
        
    def analyze_single_item(self, item: Dict) -> Dict:
        """Analizuje pojedynczy element"""
        try:
            # 1. Ekstrakcja treści
            content = self.content_extractor.extract_with_retry(item['url'])
            if not content:
                raise Exception("Nie udało się wyekstraktować treści")
            
            # 2. Przetwarzanie multimediów (jeśli są)
            media_content = {}
            if MULTIMODAL_CONFIG['enable_ocr'] and hasattr(self, 'image_extractor'):
                # Symulacja - w prawdziwej implementacji użyj image_extractor
                media_content['ocr_available'] = True
            
            # 3. Przygotowanie promptu
            prompt = self.prompt_generator.generate_analysis_prompt(
                content_type='article',
                title=item['title'],
                text_content=content,
                url=item['url']
            )
            
            # 4. Wywołanie LLM
            response = self._call_llm(prompt)
            
            # 5. Parsowanie wyniku
            result = self._parse_llm_response(response)
            
            # 6. Dodanie metadanych
            result.update({
                'url': item['url'],
                'title': item['title'],
                'analyzed_at': datetime.now().isoformat(),
                'media_analyzed': bool(media_content),
                'content_length': len(content.get('text', ''))
            })
            
            return result
            
        except Exception as e:
            return {
                'url': item['url'],
                'title': item['title'],
                'error': str(e),
                'analyzed_at': datetime.now().isoformat(),
                'status': 'failed'
            }
    
    def _call_llm(self, prompt: str) -> str:
        """Wywołuje LLM API"""
        api_url = self.provider_config['api_url']
        
        if "localhost" in api_url:
            # Lokalny model
            payload = {
                "model": LLM_CONFIG['model_name'],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": LLM_CONFIG['temperature'],
                "max_tokens": LLM_CONFIG['max_tokens']
            }
        elif "openai" in api_url:
            # OpenAI API
            headers = {
                "Authorization": f"Bearer {self.provider_config.get('api_key', '')}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.provider_config.get('model', 'gpt-3.5-turbo'),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 2000
            }
        else:
            # Inne API - placeholder
            raise NotImplementedError(f"Provider {api_url} nie jest obsługiwany")
        
        response = requests.post(
            api_url,
            json=payload,
            headers=headers if 'headers' in locals() else {},
            timeout=45
        )
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parsuje odpowiedź LLM do struktury danych"""
        try:
            # Próba parsowania JSON
            data = json.loads(response)
            
            # Walidacja i uzupełnienie domyślnych wartości
            return {
                'category': data.get('category', 'Inne'),
                'tags': data.get('tags', []),
                'summary': data.get('summary', ''),
                'educational_value': data.get('educational_value', 5),
                'key_points': data.get('key_points', []),
                'technologies': data.get('technologies', []),
                'confidence': data.get('confidence', 0.5),
                'worth_revisiting': data.get('worth_revisiting', False),
                'status': 'success'
            }
        except json.JSONDecodeError:
            # Fallback dla nie-JSON odpowiedzi
            return {
                'category': 'Inne',
                'tags': [],
                'summary': response[:500],
                'educational_value': 5,
                'confidence': 0.3,
                'status': 'partial',
                'parse_error': 'Invalid JSON response'
            }
    
    def analyze_batch(self, items: List[Dict], progress_callback=None) -> List[Dict]:
        """Analizuje batch elementów z callbackiem postępu"""
        results = []
        total = len(items)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_item = {
                executor.submit(self.analyze_single_item, item): item 
                for item in items
            }
            
            for idx, future in enumerate(as_completed(future_to_item)):
                result = future.result()
                results.append(result)
                
                if progress_callback:
                    progress_callback(idx + 1, total, result)
        
        return results

def create_advanced_visualizations(results_df: pd.DataFrame):
    """Tworzy zaawansowane wizualizacje"""
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    # 1. Heatmap kategorii vs wartość edukacyjna
    heatmap_data = results_df.pivot_table(
        values='educational_value',
        index='category',
        aggfunc=['mean', 'count']
    )
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data['mean']['educational_value'].values.reshape(-1, 1),
        x=['Średnia wartość'],
        y=heatmap_data.index,
        colorscale='Viridis',
        text=heatmap_data['count']['educational_value'].values.reshape(-1, 1),
        texttemplate='%{text} items<br>Avg: %{z:.1f}',
        textfont={"size": 10},
        showscale=True
    ))
    
    fig_heatmap.update_layout(
        title="Wartość edukacyjna według kategorii",
        height=400
    )
    
    # 2. Network graph tagów
    from collections import defaultdict
    tag_connections = defaultdict(int)
    
    for tags in results_df['tags']:
        if isinstance(tags, list) and len(tags) > 1:
            for i in range(len(tags)):
                for j in range(i+1, len(tags)):
                    pair = tuple(sorted([tags[i], tags[j]]))
                    tag_connections[pair] += 1
    
    # Tworzenie grafu sieci
    if tag_connections:
        edges = [(k[0], k[1], v) for k, v in tag_connections.items() if v > 1]
        nodes = list(set([n for edge in edges for n in edge[:2]]))
        
        # Placeholder dla network graph (wymaga dodatkowych bibliotek)
        st.info("Network graph tagów dostępny po instalacji networkx")
    
    # 3. Sunburst chart hierarchii
    hierarchy_df = results_df.groupby(['category']).agg({
        'educational_value': 'mean',
        'url': 'count'
    }).reset_index()
    hierarchy_df.columns = ['category', 'avg_value', 'count']
    
    fig_sunburst = px.sunburst(
        hierarchy_df,
        path=['category'],
        values='count',
        color='avg_value',
        color_continuous_scale='RdYlGn',
        title="Hierarchia kategorii"
    )
    
    return fig_heatmap, fig_sunburst

def export_to_notion_api(data: List[Dict], token: str, database_id: str) -> bool:
    """Rzeczywisty export do Notion przez API"""
    try:
        from notion_client import Client
        
        notion = Client(auth=token)
        
        for item in data:
            notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Title": {"title": [{"text": {"content": item['title']}}]},
                    "Category": {"select": {"name": item['category']}},
                    "URL": {"url": item['url']},
                    "Educational Value": {"number": item['educational_value']},
                    "Tags": {"multi_select": [{"name": tag} for tag in item['tags'][:5]]},
                    "Summary": {"rich_text": [{"text": {"content": item['summary'][:500]}}]},
                    "Analyzed": {"date": {"start": item['analyzed_at']}}
                }
            )
        
        return True
    except Exception as e:
        st.error(f"Błąd eksportu do Notion: {str(e)}")
        return False

# Dodatkowe funkcje pomocnicze
def generate_analysis_report(results: List[Dict]) -> str:
    """Generuje raport z analizy"""
    successful = [r for r in results if r.get('status') == 'success']
    failed = [r for r in results if r.get('status') == 'failed']
    
    report = f"""
# Raport z analizy zakładek
**Data analizy:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Podsumowanie
- **Przeanalizowano:** {len(results)} elementów
- **Sukces:** {len(successful)} ({len(successful)/len(results)*100:.1f}%)
- **Błędy:** {len(failed)} ({len(failed)/len(results)*100:.1f}%)

## Statystyki kategorii
"""
    
    if successful:
        df = pd.DataFrame(successful)
        category_stats = df.groupby('category').agg({
            'educational_value': ['mean', 'count'],
            'confidence': 'mean'
        }).round(2)
        
        report += category_stats.to_markdown()
    
    if failed:
        report += "\n\n## Błędy analizy\n"
        for item in failed[:10]:  # Max 10 błędów
            report += f"- {item['title']}: {item.get('error', 'Unknown error')}\n"
    
    return report

def save_checkpoint(results: List[Dict], checkpoint_path: str = "analysis_checkpoint.json"):
    """Zapisuje checkpoint analizy"""
    checkpoint_data = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'version': '1.0'
    }
    
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

def load_checkpoint(checkpoint_path: str = "analysis_checkpoint.json") -> List[Dict]:
    """Wczytuje checkpoint analizy"""
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('results', [])
    return []