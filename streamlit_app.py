import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import io
from collections import Counter
import base64

from llm_router import CloudLLMRouter, LLMProvider, TaskComplexity

# Configure page
st.set_page_config(
    page_title="AI Content Processor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
    <style>
    .stApp {
        background-color: #f0f2f6;
    }
    .upload-box {
        border: 2px dashed #4e8cff;
        border-radius: 10px;
        padding: 30px;
        text-align: center;
        background-color: #f8f9ff;
        margin: 20px 0;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .provider-badge {
        padding: 5px 15px;
        border-radius: 20px;
        color: white;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'router' not in st.session_state:
    st.session_state.router = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = []
if 'cost_summary' not in st.session_state:
    st.session_state.cost_summary = {}
if 'processing' not in st.session_state:
    st.session_state.processing = False


def init_router():
    """Initialize LLM router with API keys from environment or sidebar"""
    gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    anthropic_key = st.sidebar.text_input("Anthropic API Key", type="password", value=os.getenv("ANTHROPIC_API_KEY", ""))
    openai_key = st.sidebar.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    budget = st.sidebar.number_input("Monthly Budget ($)", min_value=0.0, value=10.0, step=1.0)
    
    if st.sidebar.button("Initialize Router"):
        try:
            st.session_state.router = CloudLLMRouter(
                gemini_api_key=gemini_key if gemini_key else None,
                anthropic_api_key=anthropic_key if anthropic_key else None,
                openai_api_key=openai_key if openai_key else None,
                monthly_budget=budget
            )
            st.success("Router initialized successfully!")
            return True
        except Exception as e:
            st.error(f"Error initializing router: {str(e)}")
            return False
    return False


def estimate_batch_cost(df: pd.DataFrame, task_type: str, provider: Optional[LLMProvider] = None) -> Dict[str, float]:
    """Estimate cost for processing entire batch"""
    if not st.session_state.router:
        return {}
    
    total_chars = df['text'].astype(str).str.len().sum()
    estimates = {}
    
    if provider:
        cost = st.session_state.router.estimate_cost("x" * int(total_chars), provider)
        estimates[provider.value] = cost
    else:
        # Estimate for all providers
        for prov in LLMProvider:
            if prov != LLMProvider.LOCAL:
                try:
                    cost = st.session_state.router.estimate_cost("x" * int(total_chars), prov)
                    estimates[prov.value] = cost
                except:
                    pass
    
    return estimates


async def process_batch_async(df: pd.DataFrame, task_type: str, force_provider: Optional[LLMProvider] = None):
    """Process batch of content asynchronously"""
    results = []
    total = len(df)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, row in df.iterrows():
        status_text.text(f"Processing {idx + 1}/{total}: {row.get('text', '')[:50]}...")
        
        try:
            result = await st.session_state.router.process(
                text=str(row.get('text', '')),
                task_type=task_type,
                force_provider=force_provider
            )
            
            # Merge with original row data
            result_data = {**row.to_dict(), **result['result'], 
                         'provider_used': result['provider'],
                         'processing_cost': result['cost']}
            results.append(result_data)
            
        except Exception as e:
            result_data = {**row.to_dict(), 'error': str(e)}
            results.append(result_data)
        
        progress_bar.progress((idx + 1) / total)
    
    status_text.text("Processing complete!")
    return results


def create_dashboard(df: pd.DataFrame):
    """Create dashboard with visualizations"""
    st.header("📊 Analytics Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Metrics
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Processed", len(df))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        total_cost = df['processing_cost'].sum() if 'processing_cost' in df.columns else 0
        st.metric("Total Cost", f"${total_cost:.4f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if 'category' in df.columns:
            unique_categories = df['category'].nunique()
            st.metric("Categories", unique_categories)
        else:
            st.metric("Categories", "N/A")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if st.session_state.router:
            budget_info = st.session_state.router.get_cost_summary()
            st.metric("Budget Used", f"{budget_info['budget_used_percent']:.1f}%")
        else:
            st.metric("Budget Used", "N/A")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        if 'category' in df.columns:
            st.subheader("Category Distribution")
            category_counts = df['category'].value_counts()
            fig = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                title="Content Categories",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'provider_used' in df.columns:
            st.subheader("Provider Usage")
            provider_counts = df['provider_used'].value_counts()
            fig = px.bar(
                x=provider_counts.index,
                y=provider_counts.values,
                title="LLM Provider Distribution",
                labels={'x': 'Provider', 'y': 'Count'},
                color=provider_counts.index,
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Word Cloud
    if 'tags' in df.columns:
        st.subheader("Tag Cloud")
        all_tags = []
        for tags in df['tags'].dropna():
            if isinstance(tags, list):
                all_tags.extend(tags)
            elif isinstance(tags, str):
                all_tags.extend(tags.split(','))
        
        if all_tags:
            tag_freq = Counter(all_tags)
            wordcloud = WordCloud(
                width=800, 
                height=400,
                background_color='white',
                colormap='viridis'
            ).generate_from_frequencies(tag_freq)
            
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig)
    
    # Timeline
    if 'created_at' in df.columns:
        st.subheader("Activity Timeline")
        df['date'] = pd.to_datetime(df['created_at']).dt.date
        timeline_data = df.groupby('date').size().reset_index(name='count')
        fig = px.line(
            timeline_data,
            x='date',
            y='count',
            title="Content Activity Over Time",
            labels={'count': 'Number of Items', 'date': 'Date'}
        )
        fig.update_xaxis(rangeslider_visible=True)
        st.plotly_chart(fig, use_container_width=True)


def export_data(df: pd.DataFrame, format: str):
    """Export processed data in various formats"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == "CSV":
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="processed_data_{timestamp}.csv">Download CSV</a>'
        st.markdown(href, unsafe_allow_html=True)
    
    elif format == "Excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Processed Data', index=False)
            
            # Add summary sheet
            summary_df = pd.DataFrame([
                {'Metric': 'Total Records', 'Value': len(df)},
                {'Metric': 'Total Cost', 'Value': df['processing_cost'].sum() if 'processing_cost' in df.columns else 0},
                {'Metric': 'Processing Date', 'Value': datetime.now().strftime("%Y-%m-%d %H:%M")}
            ])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="processed_data_{timestamp}.xlsx">Download Excel</a>'
        st.markdown(href, unsafe_allow_html=True)
    
    elif format == "JSON":
        json_str = df.to_json(orient='records', indent=2)
        b64 = base64.b64encode(json_str.encode()).decode()
        href = f'<a href="data:file/json;base64,{b64}" download="processed_data_{timestamp}.json">Download JSON</a>'
        st.markdown(href, unsafe_allow_html=True)
    
    elif format == "Notion CSV":
        # Format for Notion import
        notion_df = df.copy()
        if 'tags' in notion_df.columns:
            notion_df['tags'] = notion_df['tags'].apply(
                lambda x: ', '.join(x) if isinstance(x, list) else str(x)
            )
        csv = notion_df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="notion_import_{timestamp}.csv">Download Notion CSV</a>'
        st.markdown(href, unsafe_allow_html=True)


def main():
    st.title("🤖 AI Content Processor")
    st.markdown("Process your content with intelligent LLM routing and cost optimization")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Initialize router
        if not st.session_state.router:
            st.info("Please configure API keys to start")
            init_router()
        else:
            st.success("Router initialized")
            available_providers = st.session_state.router.get_available_providers()
            st.write("Available providers:", [p.value for p in available_providers])
            
            # Show cost summary
            if st.button("Refresh Cost Summary"):
                st.session_state.cost_summary = st.session_state.router.get_cost_summary()
            
            if st.session_state.cost_summary:
                st.json(st.session_state.cost_summary)
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "📊 Results", "📈 Dashboard"])
    
    with tab1:
        st.header("Upload CSV File")
        
        # File upload with drag & drop
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=['csv'],
            help="Upload a CSV file with a 'text' column containing the content to process"
        )
        
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.success(f"Uploaded {len(df)} rows")
            
            # Preview data
            with st.expander("Preview Data"):
                st.dataframe(df.head(10))
            
            # Processing options
            col1, col2 = st.columns(2)
            
            with col1:
                task_type = st.selectbox(
                    "Task Type",
                    ["analyze", "categorize", "summarize", "thread"],
                    help="Select the type of processing to perform"
                )
            
            with col2:
                provider_options = ["Auto (Cheapest)"] + [p.value for p in st.session_state.router.get_available_providers() if st.session_state.router]
                selected_provider = st.selectbox("LLM Provider", provider_options)
                
                force_provider = None
                if selected_provider != "Auto (Cheapest)":
                    force_provider = LLMProvider(selected_provider)
            
            # Cost estimation
            if st.session_state.router and 'text' in df.columns:
                st.subheader("💰 Cost Estimation")
                estimates = estimate_batch_cost(df, task_type, force_provider)
                
                est_cols = st.columns(len(estimates))
                for idx, (provider, cost) in enumerate(estimates.items()):
                    with est_cols[idx]:
                        st.metric(provider, f"${cost:.4f}")
            
            # Process button
            if st.button("🚀 Start Processing", type="primary", disabled=st.session_state.processing):
                if not st.session_state.router:
                    st.error("Please initialize the router first")
                elif 'text' not in df.columns:
                    st.error("CSV must contain a 'text' column")
                else:
                    st.session_state.processing = True
                    
                    # Run async processing
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(
                        process_batch_async(df, task_type, force_provider)
                    )
                    
                    st.session_state.processed_data = results
                    st.session_state.processing = False
                    st.success("Processing complete!")
                    st.balloons()
    
    with tab2:
        st.header("📊 Results")
        
        if st.session_state.processed_data:
            results_df = pd.DataFrame(st.session_state.processed_data)
            
            # Filters
            st.subheader("Filters")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'category' in results_df.columns:
                    categories = ["All"] + list(results_df['category'].unique())
                    selected_category = st.selectbox("Category", categories)
                    if selected_category != "All":
                        results_df = results_df[results_df['category'] == selected_category]
            
            with col2:
                if 'provider_used' in results_df.columns:
                    providers = ["All"] + list(results_df['provider_used'].unique())
                    selected_provider = st.selectbox("Provider Used", providers)
                    if selected_provider != "All":
                        results_df = results_df[results_df['provider_used'] == selected_provider]
            
            with col3:
                if 'sentiment' in results_df.columns:
                    sentiments = ["All"] + list(results_df['sentiment'].unique())
                    selected_sentiment = st.selectbox("Sentiment", sentiments)
                    if selected_sentiment != "All":
                        results_df = results_df[results_df['sentiment'] == selected_sentiment]
            
            # Display results
            st.subheader(f"Showing {len(results_df)} results")
            st.dataframe(results_df, use_container_width=True)
            
            # Export options
            st.subheader("📥 Export Data")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("Export as CSV"):
                    export_data(results_df, "CSV")
            
            with col2:
                if st.button("Export as Excel"):
                    export_data(results_df, "Excel")
            
            with col3:
                if st.button("Export as JSON"):
                    export_data(results_df, "JSON")
            
            with col4:
                if st.button("Export for Notion"):
                    export_data(results_df, "Notion CSV")
        else:
            st.info("No results to display. Please process some data first.")
    
    with tab3:
        if st.session_state.processed_data:
            results_df = pd.DataFrame(st.session_state.processed_data)
            create_dashboard(results_df)
        else:
            st.info("No data available for dashboard. Please process some data first.")


if __name__ == "__main__":
    main()