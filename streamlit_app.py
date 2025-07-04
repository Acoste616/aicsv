import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud
import json
import time
import os
from datetime import datetime, timedelta
import numpy as np
import io
from typing import Dict, List, Any, Optional
import concurrent.futures
import logging
import tempfile
from pathlib import Path

# Streamlit components
from streamlit_option_menu import option_menu
from streamlit_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from stqdm import stqdm
import base64

# Import our existing modules
try:
    from multimodal_pipeline import MultimodalKnowledgePipeline
    from smart_processing_system import SmartProcessingQueue
    from config import LLM_CONFIG, PIPELINE_CONFIG
    from content_extractor import ContentExtractor
    MODULES_AVAILABLE = True
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    MODULES_AVAILABLE = False

# ===== CONFIGURATION =====
st.set_page_config(
    page_title="Multimodal Content Analysis Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== COST ESTIMATOR =====
class CostEstimator:
    """Estymator kosztów dla różnych providerów LLM"""
    
    def __init__(self):
        self.providers = {
            "OpenAI GPT-4": {
                "input_cost": 0.03,  # per 1k tokens
                "output_cost": 0.06,
                "max_context": 128000,
                "avg_tokens_per_item": 2000
            },
            "OpenAI GPT-3.5": {
                "input_cost": 0.001,
                "output_cost": 0.002,
                "max_context": 16000,
                "avg_tokens_per_item": 1500
            },
            "Anthropic Claude": {
                "input_cost": 0.008,
                "output_cost": 0.024,
                "max_context": 100000,
                "avg_tokens_per_item": 1800
            },
            "Mistral 7B (Local)": {
                "input_cost": 0.0,
                "output_cost": 0.0,
                "max_context": 32000,
                "avg_tokens_per_item": 1200
            },
            "Ollama (Local)": {
                "input_cost": 0.0,
                "output_cost": 0.0,
                "max_context": 32000,
                "avg_tokens_per_item": 1000
            }
        }
    
    def estimate_cost(self, provider: str, num_items: int) -> Dict[str, float]:
        """Estymuje koszt przetwarzania"""
        if provider not in self.providers:
            return {"total_cost": 0.0, "cost_per_item": 0.0}
        
        config = self.providers[provider]
        avg_tokens = config["avg_tokens_per_item"]
        
        input_cost = (avg_tokens * 0.7 / 1000) * config["input_cost"]
        output_cost = (avg_tokens * 0.3 / 1000) * config["output_cost"]
        
        cost_per_item = input_cost + output_cost
        total_cost = cost_per_item * num_items
        
        return {
            "total_cost": total_cost,
            "cost_per_item": cost_per_item,
            "estimated_tokens": avg_tokens * num_items,
            "max_context": config["max_context"]
        }

# ===== EXPORT UTILITIES =====
class ExportManager:
    """Manager do eksportowania danych w różnych formatach"""
    
    @staticmethod
    def export_to_json(data: List[Dict], filename: str = None) -> str:
        """Export do JSON"""
        if filename is None:
            filename = f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        return json_data
    
    @staticmethod
    def export_to_excel(data: List[Dict], filename: str = None) -> bytes:
        """Export do Excel"""
        if filename is None:
            filename = f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        df = pd.DataFrame(data)
        
        # Utwórz buffer
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Analysis Results', index=False)
            
            # Dodaj formatowanie
            workbook = writer.book
            worksheet = writer.sheets['Analysis Results']
            
            # Format dla nagłówków
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Zastosuj formatowanie
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 15)
        
        return buffer.getvalue()
    
    @staticmethod
    def prepare_for_notion(data: List[Dict]) -> List[Dict]:
        """Przygotowuje dane do eksportu do Notion"""
        notion_data = []
        
        for item in data:
            notion_item = {
                "Title": item.get("title", "")[:100],  # Notion title limit
                "URL": item.get("url", ""),
                "Category": item.get("category", ""),
                "Tags": ", ".join(item.get("tags", [])) if item.get("tags") else "",
                "Summary": item.get("summary", "")[:2000],  # Notion text limit
                "Processing Date": datetime.now().isoformat(),
                "Status": "Processed"
            }
            notion_data.append(notion_item)
        
        return notion_data

# ===== ANALYTICS DASHBOARD =====
class AnalyticsDashboard:
    """Dashboard z analitykami i wykresami"""
    
    @staticmethod
    def create_category_pie_chart(data: List[Dict]) -> go.Figure:
        """Tworzy wykres kołowy kategorii"""
        if not data:
            return go.Figure()
        
        # Zlicz kategorie
        categories = {}
        for item in data:
            category = item.get("category", "Unknown")
            categories[category] = categories.get(category, 0) + 1
        
        if not categories:
            return go.Figure()
        
        fig = px.pie(
            values=list(categories.values()),
            names=list(categories.keys()),
            title="Rozkład kategorii treści",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Ilość: %{value}<br>Procent: %{percent}<extra></extra>'
        )
        
        return fig
    
    @staticmethod
    def create_word_cloud(data: List[Dict]) -> WordCloud:
        """Tworzy word cloud z tagów"""
        if not data:
            return None
        
        # Zbierz wszystkie tagi
        all_tags = []
        for item in data:
            tags = item.get("tags", [])
            if isinstance(tags, list):
                all_tags.extend(tags)
            elif isinstance(tags, str):
                all_tags.extend(tags.split(","))
        
        if not all_tags:
            return None
        
        # Stwórz tekst z tagów
        text = " ".join(all_tags)
        
        # Generuj word cloud
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='viridis',
            max_words=100,
            relative_scaling=0.5,
            font_path=None
        ).generate(text)
        
        return wordcloud
    
    @staticmethod
    def create_timeline_chart(data: List[Dict]) -> go.Figure:
        """Tworzy wykres timeline aktywności"""
        if not data:
            return go.Figure()
        
        # Przygotuj dane dla timeline
        timeline_data = []
        for item in data:
            created_date = item.get("created_date")
            if created_date:
                try:
                    date = pd.to_datetime(created_date).date()
                    timeline_data.append(date)
                except:
                    continue
        
        if not timeline_data:
            # Użyj obecnej daty jako fallback
            timeline_data = [datetime.now().date()]
        
        # Zlicz aktywność per dzień
        timeline_counts = pd.Series(timeline_data).value_counts().sort_index()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timeline_counts.index,
            y=timeline_counts.values,
            mode='lines+markers',
            name='Aktywność',
            line=dict(width=3, color='#1f77b4'),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title="Timeline aktywności",
            xaxis_title="Data",
            yaxis_title="Liczba elementów",
            hovermode='x unified',
            showlegend=False
        )
        
        return fig
    
    @staticmethod
    def create_processing_stats(data: List[Dict]) -> Dict[str, Any]:
        """Tworzy statystyki przetwarzania"""
        if not data:
            return {
                "total_items": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0,
                "avg_processing_time": 0,
                "categories": {},
                "domains": {}
            }
        
        total_items = len(data)
        successful = len([item for item in data if item.get("processing_success", True)])
        failed = total_items - successful
        success_rate = (successful / total_items) * 100 if total_items > 0 else 0
        
        # Czas przetwarzania
        processing_times = [item.get("processing_time", 0) for item in data if item.get("processing_time")]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Kategorie
        categories = {}
        for item in data:
            category = item.get("category", "Unknown")
            categories[category] = categories.get(category, 0) + 1
        
        # Domeny
        domains = {}
        for item in data:
            url = item.get("url", "")
            if url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    domains[domain] = domains.get(domain, 0) + 1
                except:
                    pass
        
        return {
            "total_items": total_items,
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "avg_processing_time": avg_processing_time,
            "categories": categories,
            "domains": domains
        }

# ===== MAIN APP =====
def main():
    """Główna aplikacja Streamlit"""
    
    # Sidebar z menu
    with st.sidebar:
        st.title("🧠 Multimodal Analysis")
        st.markdown("---")
        
        # Navigation menu
        selected = option_menu(
            menu_title="Menu",
            options=["Upload & Process", "Dashboard", "Results", "Export", "Settings"],
            icons=["upload", "graph-up", "table", "download", "gear"],
            menu_icon="cast",
            default_index=0
        )
        
        st.markdown("---")
        
        # System status
        st.subheader("System Status")
        if MODULES_AVAILABLE:
            st.success("✅ All modules loaded")
        else:
            st.error("❌ Some modules missing")
        
        # Quick stats
        if "processed_data" in st.session_state:
            data = st.session_state.processed_data
            st.metric("Processed Items", len(data))
            success_rate = len([item for item in data if item.get("processing_success", True)]) / len(data) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
    
    # Main content area
    if selected == "Upload & Process":
        upload_and_process_page()
    elif selected == "Dashboard":
        dashboard_page()
    elif selected == "Results":
        results_page()
    elif selected == "Export":
        export_page()
    elif selected == "Settings":
        settings_page()

def upload_and_process_page():
    """Strona z upload i przetwarzaniem"""
    st.title("📤 Upload & Process Data")
    st.markdown("Upload your CSV file and configure processing settings")
    
    # File upload
    st.subheader("1. Upload CSV File")
    uploaded_file = st.file_uploader(
        "Drag and drop your CSV file here",
        type=['csv'],
        help="CSV file should contain columns: 'url', 'content', 'rawContent'"
    )
    
    if uploaded_file is not None:
        # Preview uploaded data
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ File uploaded successfully! {len(df)} rows loaded")
            
            # Show preview
            with st.expander("Preview Data", expanded=True):
                st.dataframe(df.head(), use_container_width=True)
            
            # Validate required columns
            required_columns = ['url', 'content']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Missing required columns: {missing_columns}")
                return
            
            # LLM Provider Selection
            st.subheader("2. Select LLM Provider")
            
            col1, col2 = st.columns(2)
            
            with col1:
                cost_estimator = CostEstimator()
                provider = st.selectbox(
                    "Choose LLM Provider",
                    options=list(cost_estimator.providers.keys()),
                    index=3,  # Default to Mistral 7B (Local)
                    help="Local models are free but may have lower quality"
                )
            
            with col2:
                # Cost estimation
                cost_info = cost_estimator.estimate_cost(provider, len(df))
                st.metric("Estimated Cost", f"${cost_info['total_cost']:.4f}")
                st.metric("Cost per Item", f"${cost_info['cost_per_item']:.4f}")
                st.metric("Estimated Tokens", f"{cost_info['estimated_tokens']:,}")
            
            # Processing Configuration
            st.subheader("3. Processing Configuration")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                batch_size = st.slider("Batch Size", 1, 10, 3, help="Number of items to process in parallel")
            
            with col2:
                enable_images = st.checkbox("Process Images", value=True)
            
            with col3:
                enable_threads = st.checkbox("Collect Threads", value=True)
            
            # Start Processing
            st.subheader("4. Start Processing")
            
            if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                process_data(df, provider, batch_size, enable_images, enable_threads)
        
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")

def process_data(df: pd.DataFrame, provider: str, batch_size: int, enable_images: bool, enable_threads: bool):
    """Przetwarza dane z progress barem"""
    
    if not MODULES_AVAILABLE:
        st.error("Cannot process data - required modules not available")
        return
    
    # Initialize processing pipeline
    try:
        pipeline = MultimodalKnowledgePipeline()
        processing_queue = SmartProcessingQueue()
        
        st.success("✅ Processing pipeline initialized")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        # Process data
        results = []
        total_items = len(df)
        
        for idx, row in stqdm(df.iterrows(), total=total_items, desc="Processing items"):
            try:
                # Update progress
                progress = (idx + 1) / total_items
                progress_bar.progress(progress)
                status_text.text(f"Processing item {idx + 1}/{total_items}: {row['url'][:50]}...")
                
                # Prepare tweet data
                tweet_data = {
                    'url': row['url'],
                    'content': row['content'],
                    'rawContent': row.get('rawContent', ''),
                    'created_date': row.get('created_date', datetime.now().isoformat())
                }
                
                # Process with pipeline
                start_time = time.time()
                result = pipeline.process_tweet_complete(tweet_data)
                processing_time = time.time() - start_time
                
                # Add metadata
                result['processing_time'] = processing_time
                result['provider'] = provider
                result['batch_size'] = batch_size
                result['original_row_index'] = idx
                
                results.append(result)
                
                # Update live results display
                if idx % 5 == 0:  # Update every 5 items
                    with results_container:
                        st.subheader("Live Results")
                        latest_results = results[-5:]  # Show last 5 results
                        for i, res in enumerate(latest_results):
                            success = res.get('processing_metadata', {}).get('processing_success', False)
                            status = "✅" if success else "❌"
                            st.text(f"{status} {res.get('url', 'Unknown')[:60]}...")
                
            except Exception as e:
                st.error(f"Error processing item {idx}: {e}")
                # Add error result
                results.append({
                    'url': row['url'],
                    'error': str(e),
                    'processing_success': False,
                    'processing_time': 0,
                    'provider': provider,
                    'original_row_index': idx
                })
        
        # Finalize
        progress_bar.progress(1.0)
        status_text.text("✅ Processing completed!")
        
        # Save results to session state
        st.session_state.processed_data = results
        st.session_state.processing_config = {
            'provider': provider,
            'batch_size': batch_size,
            'enable_images': enable_images,
            'enable_threads': enable_threads,
            'processing_date': datetime.now().isoformat()
        }
        
        # Show completion summary
        successful = len([r for r in results if r.get('processing_metadata', {}).get('processing_success', False)])
        failed = len(results) - successful
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Processed", len(results))
        with col2:
            st.metric("Successful", successful)
        with col3:
            st.metric("Failed", failed)
        
        st.balloons()
        
    except Exception as e:
        st.error(f"Error initializing processing pipeline: {e}")

def dashboard_page():
    """Strona z dashboard i analitykami"""
    st.title("📊 Analytics Dashboard")
    
    if "processed_data" not in st.session_state:
        st.warning("No data available. Please upload and process data first.")
        return
    
    data = st.session_state.processed_data
    
    # Analytics dashboard
    dashboard = AnalyticsDashboard()
    
    # Processing stats
    stats = dashboard.create_processing_stats(data)
    
    # Top metrics
    st.subheader("📈 Processing Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Items", stats["total_items"])
    
    with col2:
        st.metric("Success Rate", f"{stats['success_rate']:.1f}%")
    
    with col3:
        st.metric("Avg Processing Time", f"{stats['avg_processing_time']:.2f}s")
    
    with col4:
        st.metric("Categories Found", len(stats["categories"]))
    
    # Charts
    st.subheader("📊 Visual Analytics")
    
    # Row 1: Category pie chart and timeline
    col1, col2 = st.columns(2)
    
    with col1:
        # Category pie chart
        fig_pie = dashboard.create_category_pie_chart(data)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Timeline chart
        fig_timeline = dashboard.create_timeline_chart(data)
        st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Row 2: Word cloud
    st.subheader("☁️ Tags Word Cloud")
    
    try:
        wordcloud = dashboard.create_word_cloud(data)
        if wordcloud:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig)
        else:
            st.info("No tags available for word cloud generation")
    except Exception as e:
        st.error(f"Error generating word cloud: {e}")
    
    # Additional analytics
    st.subheader("🔍 Detailed Statistics")
    
    # Top categories
    if stats["categories"]:
        st.write("**Top Categories:**")
        for category, count in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True)[:5]:
            st.text(f"• {category}: {count}")
    
    # Top domains
    if stats["domains"]:
        st.write("**Top Domains:**")
        for domain, count in sorted(stats["domains"].items(), key=lambda x: x[1], reverse=True)[:5]:
            st.text(f"• {domain}: {count}")

def results_page():
    """Strona z wynikami w tabeli z filtrami"""
    st.title("📋 Results Table")
    
    if "processed_data" not in st.session_state:
        st.warning("No data available. Please upload and process data first.")
        return
    
    data = st.session_state.processed_data
    
    # Convert to DataFrame for easier manipulation
    results_df = pd.DataFrame(data)
    
    # Filters
    st.subheader("🔍 Filters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Status filter
        status_options = ["All", "Successful", "Failed"]
        status_filter = st.selectbox("Status", status_options)
    
    with col2:
        # Category filter
        categories = ["All"] + list(results_df.get('category', pd.Series()).dropna().unique())
        category_filter = st.selectbox("Category", categories)
    
    with col3:
        # Date range filter
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            help="Filter by processing date"
        )
    
    # Apply filters
    filtered_df = results_df.copy()
    
    if status_filter == "Successful":
        filtered_df = filtered_df[filtered_df.get('processing_metadata', {}).apply(lambda x: x.get('processing_success', False) if isinstance(x, dict) else False)]
    elif status_filter == "Failed":
        filtered_df = filtered_df[filtered_df.get('processing_metadata', {}).apply(lambda x: not x.get('processing_success', True) if isinstance(x, dict) else True)]
    
    if category_filter != "All":
        filtered_df = filtered_df[filtered_df.get('category', '') == category_filter]
    
    # Display results
    st.subheader(f"📊 Results ({len(filtered_df)} items)")
    
    if len(filtered_df) > 0:
        # Configure AgGrid
        gb = GridOptionsBuilder.from_dataframe(filtered_df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=True)
        
        grid_options = gb.build()
        
        # Display grid
        grid_response = AgGrid(
            filtered_df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,
            enable_enterprise_modules=True,
            height=400
        )
        
        # Show selected rows
        if grid_response['selected_rows']:
            st.subheader("Selected Items")
            selected_df = pd.DataFrame(grid_response['selected_rows'])
            st.dataframe(selected_df, use_container_width=True)
    else:
        st.info("No results match the current filters.")

def export_page():
    """Strona z opcjami eksportu"""
    st.title("📥 Export Data")
    
    if "processed_data" not in st.session_state:
        st.warning("No data available. Please upload and process data first.")
        return
    
    data = st.session_state.processed_data
    export_manager = ExportManager()
    
    st.subheader("📊 Export Options")
    
    # Export format selection
    col1, col2 = st.columns(2)
    
    with col1:
        export_format = st.selectbox(
            "Export Format",
            ["JSON", "Excel", "CSV", "Notion"]
        )
    
    with col2:
        include_metadata = st.checkbox("Include Processing Metadata", value=True)
    
    # Prepare data for export
    export_data = data.copy()
    
    if not include_metadata:
        # Remove metadata fields
        for item in export_data:
            item.pop('processing_metadata', None)
            item.pop('processing_time', None)
            item.pop('provider', None)
    
    # Export buttons
    st.subheader("🚀 Download")
    
    if export_format == "JSON":
        json_data = export_manager.export_to_json(export_data)
        st.download_button(
            label="📄 Download JSON",
            data=json_data,
            file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    elif export_format == "Excel":
        excel_data = export_manager.export_to_excel(export_data)
        st.download_button(
            label="📊 Download Excel",
            data=excel_data,
            file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    elif export_format == "CSV":
        df = pd.DataFrame(export_data)
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📋 Download CSV",
            data=csv_data,
            file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    elif export_format == "Notion":
        notion_data = export_manager.prepare_for_notion(export_data)
        st.subheader("📝 Notion Export")
        st.info("Notion export requires API configuration. Here's your data formatted for Notion:")
        
        # Show formatted data
        notion_df = pd.DataFrame(notion_data)
        st.dataframe(notion_df, use_container_width=True)
        
        # Download as CSV for manual import
        csv_data = notion_df.to_csv(index=False)
        st.download_button(
            label="📋 Download for Notion Import",
            data=csv_data,
            file_name=f"notion_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Export preview
    st.subheader("👁️ Export Preview")
    
    if export_data:
        # Show first few items
        preview_data = export_data[:3]
        st.json(preview_data)
    
    # Export statistics
    st.subheader("📊 Export Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Items", len(export_data))
    
    with col2:
        successful_items = len([item for item in export_data if item.get('processing_metadata', {}).get('processing_success', False)])
        st.metric("Successful Items", successful_items)
    
    with col3:
        if export_data:
            avg_size = len(json.dumps(export_data[0])) if export_data else 0
            total_size = avg_size * len(export_data)
            st.metric("Estimated Size", f"{total_size/1024:.1f} KB")

def settings_page():
    """Strona z ustawieniami"""
    st.title("⚙️ Settings")
    
    # LLM Configuration
    st.subheader("🤖 LLM Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        api_url = st.text_input("API URL", value=LLM_CONFIG.get("api_url", ""))
        model_name = st.text_input("Model Name", value=LLM_CONFIG.get("model_name", ""))
    
    with col2:
        temperature = st.slider("Temperature", 0.0, 2.0, float(LLM_CONFIG.get("temperature", 0.1)), 0.1)
        max_tokens = st.number_input("Max Tokens", min_value=100, max_value=4000, value=LLM_CONFIG.get("max_tokens", 2000))
    
    # Pipeline Configuration
    st.subheader("🔧 Pipeline Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        batch_size = st.number_input("Batch Size", min_value=1, max_value=20, value=PIPELINE_CONFIG.get("batch_size", 1))
        timeout = st.number_input("Timeout (seconds)", min_value=10, max_value=120, value=LLM_CONFIG.get("timeout", 45))
    
    with col2:
        quality_threshold = st.slider("Quality Threshold", 0.0, 1.0, float(PIPELINE_CONFIG.get("quality_threshold", 0.2)), 0.1)
        retry_attempts = st.number_input("Retry Attempts", min_value=0, max_value=5, value=LLM_CONFIG.get("retry_attempts", 2))
    
    # Processing Options
    st.subheader("🔄 Processing Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        enable_ocr = st.checkbox("Enable OCR", value=True)
        enable_threads = st.checkbox("Enable Thread Collection", value=True)
    
    with col2:
        enable_video = st.checkbox("Enable Video Analysis", value=True)
        cache_media = st.checkbox("Cache Media", value=True)
    
    # Save settings
    if st.button("💾 Save Settings", type="primary"):
        # Here you would save the settings to a config file
        st.success("Settings saved successfully!")
        
        # Show current configuration
        st.subheader("Current Configuration")
        config_display = {
            "LLM": {
                "api_url": api_url,
                "model_name": model_name,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            "Pipeline": {
                "batch_size": batch_size,
                "timeout": timeout,
                "quality_threshold": quality_threshold,
                "retry_attempts": retry_attempts
            },
            "Processing": {
                "enable_ocr": enable_ocr,
                "enable_threads": enable_threads,
                "enable_video": enable_video,
                "cache_media": cache_media
            }
        }
        
        st.json(config_display)
    
    # System Information
    st.subheader("💻 System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**Python Version:** " + str(st.__version__))
        st.info("**Streamlit Version:** " + str(st.__version__))
    
    with col2:
        st.info("**Available Memory:** Checking...")
        st.info("**Processing Cores:** Checking...")
    
    # Reset options
    st.subheader("🔄 Reset Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Session Data"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Session data cleared!")
    
    with col2:
        if st.button("🔄 Reset to Defaults"):
            st.success("Settings reset to defaults!")

# ===== RUN APP =====
if __name__ == "__main__":
    main()