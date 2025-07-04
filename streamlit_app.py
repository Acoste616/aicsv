"""
Streamlit Web Interface dla analizy zakładek i treści
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import json
import io
import base64
from datetime import datetime
import time
from typing import Dict, List, Any, Optional
import requests
from collections import Counter
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

# Import lokalnych modułów
from config import LLM_CONFIG
from tweet_content_analyzer import TweetContentAnalyzer
from content_extractor import ContentExtractor

# Konfiguracja strony
st.set_page_config(
    page_title="Analiza Zakładek - Web UI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .upload-box {
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        background-color: #f9f9f9;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .progress-bar {
        background-color: #4CAF50;
        height: 20px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Definicje providerów LLM
LLM_PROVIDERS = {
    "Local (Mistral 7B)": {
        "api_url": "http://localhost:1234/v1/chat/completions",
        "cost_per_1k_tokens": 0.0,
        "description": "Darmowy lokalny model",
        "requirements": "Wymaga lokalnego serwera LLM"
    },
    "OpenAI GPT-3.5": {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "cost_per_1k_tokens": 0.002,
        "description": "Szybki i ekonomiczny",
        "requirements": "Wymaga klucza API OpenAI"
    },
    "OpenAI GPT-4": {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "cost_per_1k_tokens": 0.03,
        "description": "Najwyższa jakość analizy",
        "requirements": "Wymaga klucza API OpenAI"
    },
    "Anthropic Claude": {
        "api_url": "https://api.anthropic.com/v1/messages",
        "cost_per_1k_tokens": 0.008,
        "description": "Dobra jakość i bezpieczeństwo",
        "requirements": "Wymaga klucza API Anthropic"
    }
}

# Kategorie i tagi
CATEGORIES = [
    "Technologia", "AI/ML", "Programowanie", "DevOps", 
    "Security", "Cloud", "Web Development", "Mobile",
    "Data Science", "Blockchain", "IoT", "Inne"
]

# Funkcje pomocnicze
def estimate_cost(num_items: int, provider: str) -> float:
    """Estymacja kosztów analizy"""
    avg_tokens_per_item = 500  # Średnia liczba tokenów na element
    total_tokens = num_items * avg_tokens_per_item
    cost_per_1k = LLM_PROVIDERS[provider]["cost_per_1k_tokens"]
    return (total_tokens / 1000) * cost_per_1k

def export_to_json(data: List[Dict]) -> str:
    """Export danych do JSON"""
    return json.dumps(data, ensure_ascii=False, indent=2)

def export_to_excel(df: pd.DataFrame) -> bytes:
    """Export danych do Excel z formatowaniem"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Analiza', index=False)
        
        # Formatowanie
        workbook = writer.book
        worksheet = writer.sheets['Analiza']
        
        # Nagłówki
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
        
        # Auto-szerokość kolumn
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return output.getvalue()

def export_to_notion(data: List[Dict], notion_token: str, database_id: str) -> bool:
    """Export danych do Notion (placeholder)"""
    # W prawdziwej implementacji użyj notion-client
    st.info("Export do Notion wymaga konfiguracji API")
    return False

def generate_wordcloud(texts: List[str]) -> go.Figure:
    """Generowanie word cloud"""
    text = ' '.join(texts)
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        colormap='viridis',
        max_words=100
    ).generate(text)
    
    fig = go.Figure()
    fig.add_trace(go.Image(z=wordcloud.to_array()))
    fig.update_layout(
        title="Word Cloud tagów",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        height=400
    )
    return fig

# Główna aplikacja
def main():
    st.title("🚀 Analiza Zakładek - Web Interface")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Konfiguracja")
        
        # Wybór providera LLM
        provider = st.selectbox(
            "Provider LLM",
            list(LLM_PROVIDERS.keys()),
            help="Wybierz dostawcę modelu językowego"
        )
        
        # Informacje o providerze
        provider_info = LLM_PROVIDERS[provider]
        st.info(f"**{provider}**\n\n"
                f"{provider_info['description']}\n\n"
                f"💰 Koszt: ${provider_info['cost_per_1k_tokens']}/1k tokenów\n\n"
                f"⚡ {provider_info['requirements']}")
        
        # API Key (jeśli potrzebny)
        if provider != "Local (Mistral 7B)":
            api_key = st.text_input("API Key", type="password")
        
        st.divider()
        
        # Ustawienia analizy
        st.subheader("📊 Ustawienia analizy")
        batch_size = st.slider("Rozmiar batch", 1, 50, 10)
        enable_ocr = st.checkbox("Włącz OCR dla obrazów", value=True)
        enable_threads = st.checkbox("Zbieraj wątki Twitter", value=True)
        
    # Główna zawartość
    tabs = st.tabs(["📤 Upload", "🔄 Analiza", "📊 Dashboard", "💾 Export"])
    
    # Tab Upload
    with tabs[0]:
        st.header("Upload pliku CSV")
        
        # Drag & Drop area
        uploaded_file = st.file_uploader(
            "Przeciągnij i upuść plik CSV lub kliknij, aby wybrać",
            type=['csv'],
            accept_multiple_files=False,
            help="Plik CSV powinien zawierać kolumny: url, title, created_at"
        )
        
        if uploaded_file is not None:
            # Wczytaj dane
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ Wczytano {len(df)} rekordów")
            
            # Podgląd danych
            with st.expander("👀 Podgląd danych"):
                st.dataframe(df.head(10))
            
            # Statystyki
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Liczba rekordów", len(df))
            with col2:
                st.metric("Unikalne domeny", df['url'].apply(lambda x: x.split('/')[2]).nunique())
            with col3:
                estimated_cost = estimate_cost(len(df), provider)
                st.metric("Szacowany koszt", f"${estimated_cost:.2f}")
            with col4:
                estimated_time = len(df) * 2  # 2 sekundy na rekord
                st.metric("Szacowany czas", f"{estimated_time//60}m {estimated_time%60}s")
            
            # Zapisz dane w sesji
            st.session_state['data'] = df
            st.session_state['provider'] = provider
            
            # Przycisk start analizy
            if st.button("🚀 Rozpocznij analizę", type="primary"):
                st.session_state['start_analysis'] = True
                st.switch_page("pages/analysis.py")  # Przejdź do analizy

    # Tab Analiza
    with tabs[1]:
        st.header("Analiza w czasie rzeczywistym")
        
        if 'data' in st.session_state and st.session_state.get('start_analysis', False):
            df = st.session_state['data']
            total_items = len(df)
            
            # Progress containers
            progress_bar = st.progress(0)
            status_text = st.empty()
            current_item = st.empty()
            results_container = st.container()
            
            # Analiza
            analyzer = TweetContentAnalyzer()
            results = []
            errors = []
            
            for idx, row in df.iterrows():
                # Update progress
                progress = (idx + 1) / total_items
                progress_bar.progress(progress)
                status_text.text(f"Analizuję {idx + 1}/{total_items} ({progress*100:.1f}%)")
                
                # Pokaż aktualny element
                with current_item.container():
                    st.info(f"🔍 Analizuję: {row['title'][:100]}...")
                
                try:
                    # Symulacja analizy (w prawdziwej implementacji użyj prawdziwego API)
                    time.sleep(0.5)  # Symulacja
                    
                    result = {
                        'url': row['url'],
                        'title': row['title'],
                        'category': np.random.choice(CATEGORIES),
                        'tags': np.random.choice(['AI', 'Python', 'Cloud', 'DevOps', 'Security'], 
                                               size=np.random.randint(2, 5), replace=False).tolist(),
                        'educational_value': np.random.randint(1, 11),
                        'summary': f"Analiza treści: {row['title'][:50]}...",
                        'analyzed_at': datetime.now().isoformat(),
                        'confidence': np.random.uniform(0.7, 1.0)
                    }
                    results.append(result)
                    
                except Exception as e:
                    errors.append({
                        'url': row['url'],
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Pokaż ostatnie wyniki
                if len(results) > 0:
                    with results_container:
                        st.subheader("Ostatnie wyniki")
                        recent_df = pd.DataFrame(results[-5:])
                        st.dataframe(recent_df[['title', 'category', 'educational_value']])
            
            # Zapisz wyniki
            st.session_state['results'] = results
            st.session_state['errors'] = errors
            
            # Podsumowanie
            st.success(f"✅ Analiza zakończona! Przeanalizowano {len(results)} z {total_items} elementów")
            
            if errors:
                with st.expander(f"⚠️ Błędy ({len(errors)})"):
                    st.dataframe(pd.DataFrame(errors))
        
        else:
            st.info("👆 Najpierw wgraj plik CSV w zakładce Upload")

    # Tab Dashboard
    with tabs[2]:
        st.header("Dashboard analityczny")
        
        if 'results' in st.session_state and st.session_state['results']:
            results_df = pd.DataFrame(st.session_state['results'])
            
            # Metryki główne
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Przeanalizowane", len(results_df))
            with col2:
                avg_edu = results_df['educational_value'].mean()
                st.metric("Śr. wartość edukacyjna", f"{avg_edu:.1f}/10")
            with col3:
                high_value = len(results_df[results_df['educational_value'] >= 7])
                st.metric("Wysokiej jakości", high_value)
            with col4:
                avg_conf = results_df['confidence'].mean()
                st.metric("Śr. pewność", f"{avg_conf*100:.1f}%")
            
            st.divider()
            
            # Wykresy
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart kategorii
                category_counts = results_df['category'].value_counts()
                fig_pie = px.pie(
                    values=category_counts.values,
                    names=category_counts.index,
                    title="Rozkład kategorii",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Histogram wartości edukacyjnej
                fig_hist = px.histogram(
                    results_df,
                    x='educational_value',
                    nbins=10,
                    title="Rozkład wartości edukacyjnej",
                    labels={'educational_value': 'Wartość edukacyjna', 'count': 'Liczba'}
                )
                fig_hist.update_layout(bargap=0.1)
                st.plotly_chart(fig_hist, use_container_width=True)
            
            # Word Cloud tagów
            all_tags = []
            for tags in results_df['tags']:
                all_tags.extend(tags)
            
            if all_tags:
                fig_wordcloud = generate_wordcloud(all_tags)
                st.plotly_chart(fig_wordcloud, use_container_width=True)
            
            # Timeline aktywności (jeśli mamy daty)
            if 'created_at' in results_df.columns:
                results_df['created_at'] = pd.to_datetime(results_df['created_at'])
                daily_counts = results_df.resample('D', on='created_at').size()
                
                fig_timeline = px.line(
                    x=daily_counts.index,
                    y=daily_counts.values,
                    title="Timeline aktywności",
                    labels={'x': 'Data', 'y': 'Liczba zakładek'}
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
            
            # Tabela z filtrami
            st.subheader("🔍 Przeglądaj wyniki")
            
            # Filtry
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_categories = st.multiselect(
                    "Kategorie",
                    options=results_df['category'].unique(),
                    default=results_df['category'].unique()
                )
            with col2:
                min_edu_value = st.slider(
                    "Min. wartość edukacyjna",
                    min_value=1,
                    max_value=10,
                    value=1
                )
            with col3:
                search_term = st.text_input("Szukaj w tytułach")
            
            # Filtrowanie
            filtered_df = results_df[results_df['category'].isin(selected_categories)]
            filtered_df = filtered_df[filtered_df['educational_value'] >= min_edu_value]
            if search_term:
                filtered_df = filtered_df[filtered_df['title'].str.contains(search_term, case=False, na=False)]
            
            # Wyświetl tabelę
            st.dataframe(
                filtered_df[['title', 'category', 'tags', 'educational_value', 'summary']],
                use_container_width=True,
                height=400
            )
            
        else:
            st.info("📊 Brak danych do wyświetlenia. Najpierw przeprowadź analizę.")

    # Tab Export
    with tabs[3]:
        st.header("Export wyników")
        
        if 'results' in st.session_state and st.session_state['results']:
            results_df = pd.DataFrame(st.session_state['results'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("📄 JSON")
                json_data = export_to_json(st.session_state['results'])
                st.download_button(
                    label="Pobierz JSON",
                    data=json_data,
                    file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col2:
                st.subheader("📊 Excel")
                excel_data = export_to_excel(results_df)
                st.download_button(
                    label="Pobierz Excel",
                    data=excel_data,
                    file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col3:
                st.subheader("📝 Notion")
                with st.form("notion_export"):
                    notion_token = st.text_input("Notion Integration Token", type="password")
                    database_id = st.text_input("Database ID")
                    if st.form_submit_button("Export do Notion"):
                        if notion_token and database_id:
                            success = export_to_notion(
                                st.session_state['results'],
                                notion_token,
                                database_id
                            )
                            if success:
                                st.success("✅ Wyeksportowano do Notion!")
                            else:
                                st.error("❌ Błąd eksportu do Notion")
                        else:
                            st.warning("Wypełnij wszystkie pola")
            
            # Podgląd danych do eksportu
            with st.expander("👀 Podgląd danych do eksportu"):
                st.json(st.session_state['results'][:5])
        
        else:
            st.info("💾 Brak danych do eksportu. Najpierw przeprowadź analizę.")

if __name__ == "__main__":
    main()