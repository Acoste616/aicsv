"""
Streamlit Dashboard for Multi-Model Content Processing System
"""

import streamlit as st
import pandas as pd
import json
import os
import asyncio
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import csv
from io import StringIO
from typing import Dict, List, Any, Optional

# Import our processing system
from multi_model_processor import (
    MultiModelProcessor, 
    ContentComplexity,
    ModelType
)

# Page configuration
st.set_page_config(
    page_title="Multi-Model Content Processor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.stMetric {
    background-color: #f0f2f6;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.success-box {
    background-color: #d4edda;
    border-color: #c3e6cb;
    color: #155724;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
.error-box {
    background-color: #f8d7da;
    border-color: #f5c6cb;
    color: #721c24;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
.info-box {
    background-color: #d1ecf1;
    border-color: #bee5eb;
    color: #0c5460;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processor' not in st.session_state:
    st.session_state.processor = None
    st.session_state.processing_history = []
    st.session_state.api_keys_configured = False

def load_api_keys():
    """Load API keys from environment or config file"""
    api_keys = {}
    
    # Try to load from .env file
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
        
        api_keys['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', '')
        api_keys['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
        api_keys['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')
    
    return api_keys

def initialize_processor():
    """Initialize the multi-model processor"""
    api_keys = load_api_keys()
    
    # Check if we have at least one API key
    if not any(api_keys.values()):
        return None, False
    
    try:
        processor = MultiModelProcessor(api_keys)
        return processor, True
    except Exception as e:
        st.error(f"Failed to initialize processor: {e}")
        return None, False

# Sidebar - Configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # API Keys Section
    with st.expander("🔑 API Keys", expanded=not st.session_state.api_keys_configured):
        st.info("Enter your API keys to enable different models")
        
        gemini_key = st.text_input("Gemini API Key", type="password", key="gemini_key")
        anthropic_key = st.text_input("Anthropic API Key", type="password", key="anthropic_key")
        openai_key = st.text_input("OpenAI API Key", type="password", key="openai_key")
        
        if st.button("Save API Keys"):
            # Save to .env file
            with open('.env', 'w') as f:
                if gemini_key:
                    f.write(f"GEMINI_API_KEY={gemini_key}\n")
                if anthropic_key:
                    f.write(f"ANTHROPIC_API_KEY={anthropic_key}\n")
                if openai_key:
                    f.write(f"OPENAI_API_KEY={openai_key}\n")
            
            st.success("API keys saved!")
            st.session_state.api_keys_configured = True
            st.rerun()
    
    # Processing Settings
    st.subheader("📊 Processing Settings")
    batch_size = st.slider("Batch Size", 1, 50, 10)
    concurrent_requests = st.slider("Concurrent Requests", 1, 10, 3)
    
    # Model Availability
    st.subheader("🤖 Model Status")
    api_keys = load_api_keys()
    
    col1, col2 = st.columns(2)
    with col1:
        if api_keys.get('GEMINI_API_KEY'):
            st.success("✅ Gemini")
        else:
            st.error("❌ Gemini")
    
    with col2:
        if api_keys.get('ANTHROPIC_API_KEY'):
            st.success("✅ Claude")
        else:
            st.error("❌ Claude")
    
    if api_keys.get('OPENAI_API_KEY'):
        st.success("✅ GPT-4o")
    else:
        st.error("❌ GPT-4o")

# Main Content Area
st.title("🚀 Multi-Model Content Processing System")
st.markdown("Process content through different AI models based on complexity")

# Initialize processor if not already done
if st.session_state.processor is None:
    processor, success = initialize_processor()
    if success:
        st.session_state.processor = processor
    else:
        st.warning("Please configure at least one API key in the sidebar to proceed.")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 Upload & Process", "📊 Analytics", "🔍 Knowledge Base", "📈 Performance", "📝 Logs"])

# Tab 1: Upload & Process
with tab1:
    st.header("Upload CSV for Processing")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload a CSV file with content to process"
    )
    
    if uploaded_file is not None:
        # Read CSV
        df = pd.read_csv(uploaded_file)
        
        st.subheader("📋 Data Preview")
        st.dataframe(df.head(), use_container_width=True)
        
        # Column mapping
        st.subheader("🔧 Column Mapping")
        col1, col2 = st.columns(2)
        
        with col1:
            content_column = st.selectbox(
                "Select content column",
                options=df.columns.tolist(),
                help="Choose the column containing the main content to process"
            )
        
        with col2:
            metadata_columns = st.multiselect(
                "Select metadata columns (optional)",
                options=[col for col in df.columns if col != content_column],
                help="Choose additional columns to include as metadata"
            )
        
        # Processing options
        st.subheader("⚡ Processing Options")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            process_sample = st.checkbox("Process sample only", value=True)
            if process_sample:
                sample_size = st.number_input("Sample size", min_value=1, max_value=len(df), value=min(5, len(df)))
        
        with col2:
            show_live_progress = st.checkbox("Show live progress", value=True)
        
        with col3:
            save_to_kb = st.checkbox("Save to Knowledge Base", value=True)
        
        # Process button
        if st.button("🚀 Start Processing", type="primary", disabled=st.session_state.processor is None):
            if st.session_state.processor:
                # Prepare data
                if process_sample:
                    process_df = df.head(sample_size)
                else:
                    process_df = df
                
                # Create progress containers
                progress_bar = st.progress(0)
                status_text = st.empty()
                results_container = st.container()
                
                # Process data
                csv_data = []
                for idx, row in process_df.iterrows():
                    item = {'content': row[content_column]}
                    for col in metadata_columns:
                        item[col] = row[col]
                    csv_data.append(item)
                
                # Run async processing
                async def process_batch():
                    results = []
                    total = len(csv_data)
                    
                    for i, item in enumerate(csv_data):
                        if show_live_progress:
                            status_text.text(f"Processing item {i+1}/{total}...")
                            progress_bar.progress((i + 1) / total)
                        
                        result = await st.session_state.processor.process_content(
                            item['content'], 
                            {k: v for k, v in item.items() if k != 'content'}
                        )
                        results.append(result)
                        
                        # Add to history
                        st.session_state.processing_history.append({
                            'timestamp': datetime.now(),
                            'content_preview': item['content'][:100] + '...',
                            'complexity': result.complexity.value,
                            'model': result.model_type.value,
                            'success': result.result.get('success', False) if result.result else False,
                            'processing_time': result.processing_time
                        })
                    
                    return results
                
                # Execute processing
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(process_batch())
                    
                    # Show results
                    with results_container:
                        st.success(f"✅ Processed {len(results)} items successfully!")
                        
                        # Summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        successful = sum(1 for r in results if r.result and r.result.get('success'))
                        failed = len(results) - successful
                        avg_time = sum(r.processing_time or 0 for r in results) / len(results)
                        
                        with col1:
                            st.metric("Total Processed", len(results))
                        with col2:
                            st.metric("Successful", successful, delta=f"{successful/len(results)*100:.1f}%")
                        with col3:
                            st.metric("Failed", failed)
                        with col4:
                            st.metric("Avg Time", f"{avg_time:.2f}s")
                        
                        # Detailed results
                        st.subheader("📊 Processing Results")
                        
                        results_data = []
                        for r in results:
                            results_data.append({
                                'ID': r.id,
                                'Complexity': r.complexity.value,
                                'Model': r.model_type.value,
                                'Success': '✅' if r.result and r.result.get('success') else '❌',
                                'Processing Time': f"{r.processing_time:.2f}s" if r.processing_time else 'N/A',
                                'Content Preview': r.content[:100] + '...'
                            })
                        
                        results_df = pd.DataFrame(results_data)
                        st.dataframe(results_df, use_container_width=True)
                        
                        # Download results
                        csv_results = results_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Results CSV",
                            data=csv_results,
                            file_name=f"processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                
                except Exception as e:
                    st.error(f"Processing error: {e}")
                    import traceback
                    st.code(traceback.format_exc())

# Tab 2: Analytics
with tab2:
    st.header("📊 Processing Analytics")
    
    if st.session_state.processor:
        # Get system stats
        stats = st.session_state.processor.get_system_stats()
        
        # Cache statistics
        st.subheader("💾 Cache Performance")
        
        cache_stats = stats.get('cache_stats', {}).get('cache_stats', [])
        if cache_stats:
            cache_df = pd.DataFrame(cache_stats)
            
            # Create visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    cache_df, 
                    x='model', 
                    y='count',
                    color='complexity',
                    title='Requests by Model and Complexity',
                    labels={'count': 'Number of Requests', 'model': 'Model'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.scatter(
                    cache_df,
                    x='complexity',
                    y='avg_processing_time',
                    size='count',
                    color='model',
                    title='Processing Time by Complexity',
                    labels={'avg_processing_time': 'Avg Processing Time (s)'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Knowledge Base statistics
        st.subheader("📚 Knowledge Base Statistics")
        
        kb_stats = stats.get('knowledge_base_stats', {})
        if kb_stats.get('total_entries', 0) > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Entries", kb_stats.get('total_entries', 0))
            
            with col2:
                st.metric("Avg Processing Time", f"{kb_stats.get('avg_processing_time', 0):.2f}s")
            
            with col3:
                st.metric("Models Used", len(kb_stats.get('model_distribution', {})))
            
            # Model distribution pie chart
            if kb_stats.get('model_distribution'):
                fig = go.Figure(data=[go.Pie(
                    labels=list(kb_stats['model_distribution'].keys()),
                    values=list(kb_stats['model_distribution'].values()),
                    title='Model Usage Distribution'
                )])
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data in knowledge base yet. Process some content to see analytics.")
    else:
        st.warning("Initialize the processor to view analytics.")

# Tab 3: Knowledge Base
with tab3:
    st.header("🔍 Knowledge Base Search")
    
    if st.session_state.processor:
        # Search interface
        search_query = st.text_input("🔍 Search knowledge base", placeholder="Enter search terms...")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_limit = st.slider("Results limit", 5, 50, 10)
        with col2:
            search_button = st.button("Search", type="primary")
        
        if search_query and search_button:
            # Perform search
            results = st.session_state.processor.knowledge_base.search(search_query, limit=search_limit)
            
            if results:
                st.success(f"Found {len(results)} results")
                
                # Display results
                for i, result in enumerate(results):
                    with st.expander(f"Result {i+1} - {result.get('model_used', 'Unknown')} - {result.get('complexity', 'Unknown')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write("**Content Preview:**")
                            st.write(result.get('content_preview', 'N/A'))
                            
                            if result.get('analysis'):
                                st.write("**Analysis:**")
                                st.json(result.get('analysis'))
                        
                        with col2:
                            st.write("**Metadata:**")
                            st.write(f"- ID: {result.get('id', 'N/A')}")
                            st.write(f"- Timestamp: {result.get('timestamp', 'N/A')}")
                            st.write(f"- Model: {result.get('model_used', 'N/A')}")
                            st.write(f"- Complexity: {result.get('complexity', 'N/A')}")
                            st.write(f"- Processing Time: {result.get('processing_time', 0):.2f}s")
            else:
                st.info("No results found. Try different search terms.")
        
        # Export knowledge base
        st.subheader("📤 Export Knowledge Base")
        
        if st.button("Export as JSON"):
            kb_data = json.dumps(st.session_state.processor.knowledge_base.entries, indent=2)
            st.download_button(
                label="📥 Download Knowledge Base",
                data=kb_data,
                file_name=f"knowledge_base_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.warning("Initialize the processor to access the knowledge base.")

# Tab 4: Performance
with tab4:
    st.header("📈 System Performance")
    
    if st.session_state.processing_history:
        # Convert history to DataFrame
        history_df = pd.DataFrame(st.session_state.processing_history)
        
        # Time series of processing
        st.subheader("Processing Timeline")
        
        fig = px.scatter(
            history_df,
            x='timestamp',
            y='processing_time',
            color='model',
            size='processing_time',
            hover_data=['complexity', 'success'],
            title='Processing Time Over Time'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Performance by model
        st.subheader("Model Performance Comparison")
        
        model_perf = history_df.groupby('model').agg({
            'processing_time': ['mean', 'min', 'max', 'count'],
            'success': lambda x: (x == True).sum() / len(x) * 100
        }).round(2)
        
        st.dataframe(model_perf, use_container_width=True)
        
        # Complexity distribution
        st.subheader("Complexity Distribution")
        
        complexity_counts = history_df['complexity'].value_counts()
        fig = go.Figure(data=[go.Bar(
            x=complexity_counts.index,
            y=complexity_counts.values,
            text=complexity_counts.values,
            textposition='auto',
        )])
        fig.update_layout(
            title='Content Complexity Distribution',
            xaxis_title='Complexity Level',
            yaxis_title='Count'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No processing history yet. Process some content to see performance metrics.")

# Tab 5: Logs
with tab5:
    st.header("📝 Processing Logs")
    
    # Log filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        log_level = st.selectbox("Log Level", ["All", "Success", "Error"])
    
    with col2:
        time_filter = st.selectbox("Time Range", ["Last Hour", "Last 24 Hours", "Last Week", "All Time"])
    
    with col3:
        model_filter = st.multiselect("Models", ["gemini-flash", "claude-haiku", "gpt-4o"])
    
    # Display recent logs
    if st.session_state.processing_history:
        filtered_logs = st.session_state.processing_history.copy()
        
        # Apply filters
        if log_level == "Success":
            filtered_logs = [log for log in filtered_logs if log.get('success')]
        elif log_level == "Error":
            filtered_logs = [log for log in filtered_logs if not log.get('success')]
        
        if model_filter:
            filtered_logs = [log for log in filtered_logs if log.get('model') in model_filter]
        
        # Time filter
        now = datetime.now()
        if time_filter == "Last Hour":
            cutoff = now - timedelta(hours=1)
        elif time_filter == "Last 24 Hours":
            cutoff = now - timedelta(days=1)
        elif time_filter == "Last Week":
            cutoff = now - timedelta(weeks=1)
        else:
            cutoff = datetime.min
        
        filtered_logs = [log for log in filtered_logs if log.get('timestamp', now) > cutoff]
        
        # Display logs
        st.write(f"Showing {len(filtered_logs)} logs")
        
        for log in reversed(filtered_logs[-20:]):  # Show last 20 logs
            timestamp = log.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
            success = "✅" if log.get('success') else "❌"
            
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
                
                with col1:
                    st.write(f"{success} {timestamp}")
                
                with col2:
                    st.write(f"**{log.get('model', 'Unknown')}**")
                
                with col3:
                    st.write(f"{log.get('complexity', 'Unknown')}")
                
                with col4:
                    st.write(log.get('content_preview', 'N/A'))
                
                st.divider()
    else:
        st.info("No logs available yet.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        Multi-Model Content Processing System v1.0 | 
        Powered by Gemini, Claude, and GPT-4
    </div>
    """,
    unsafe_allow_html=True
)