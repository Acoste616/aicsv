# 🧠 Streamlit Multimodal Content Analysis Platform

A comprehensive web interface for analyzing multimodal content using various LLM providers. This platform provides an intuitive interface for processing CSV data with real-time analytics, cost estimation, and multiple export formats.

## ✨ Features

### 📤 Upload & Process
- **Drag & Drop CSV Upload** - Easy file upload with preview
- **LLM Provider Selection** - Choose from OpenAI, Anthropic, Mistral, Ollama
- **Real-time Cost Estimation** - See costs before processing
- **Live Progress Tracking** - Monitor processing in real-time
- **Batch Processing** - Configure parallel processing settings

### 📊 Analytics Dashboard
- **Category Pie Charts** - Visual breakdown of content categories
- **Word Cloud** - Tag visualization from processed content
- **Timeline Charts** - Activity timeline visualization
- **Processing Statistics** - Success rates, timing, and performance metrics
- **Domain Analysis** - Top domains and their processing statistics

### 📋 Results Table
- **Interactive Data Grid** - Sortable, filterable results table
- **Advanced Filters** - Filter by status, category, date range
- **Multi-select** - Select multiple rows for batch operations
- **Live Search** - Real-time search across all results

### 📥 Export Options
- **JSON Export** - Structured data export
- **Excel Export** - Formatted spreadsheet with styling
- **CSV Export** - Universal format for data analysis
- **Notion Export** - Prepared format for Notion import
- **Custom Metadata** - Include/exclude processing metadata

### ⚙️ Settings
- **LLM Configuration** - API settings, model selection, parameters
- **Pipeline Settings** - Batch size, timeout, quality thresholds
- **Processing Options** - OCR, thread collection, video analysis
- **System Information** - Resource monitoring and diagnostics

## 🚀 Quick Start

### 1. Setup and Installation

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd <repository-directory>

# Run the setup script
python setup_streamlit.py
```

### 2. Manual Installation (Alternative)

```bash
# Install dependencies
pip install -r requirements.txt

# Create sample data (optional)
python -c "
import pandas as pd
data = {
    'url': ['https://github.com/microsoft/vscode', 'https://docs.python.org/3/'],
    'content': ['Microsoft Visual Studio Code editor', 'Python Documentation'],
    'rawContent': ['Check out this awesome code editor', 'Learn Python programming']
}
pd.DataFrame(data).to_csv('sample_data.csv', index=False)
"
```

### 3. Run the Application

```bash
# Start the Streamlit app
streamlit run streamlit_app.py

# Or specify a custom port
streamlit run streamlit_app.py --server.port 8502
```

### 4. Access the Web Interface

Open your browser and navigate to:
- **Local**: http://localhost:8501
- **Custom Port**: http://localhost:8502

## 📋 Data Format

Your CSV file should contain these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `url` | ✅ | URL of the content to analyze |
| `content` | ✅ | Main content text |
| `rawContent` | ❌ | Additional raw content |
| `created_date` | ❌ | Content creation date (ISO format) |

### Example CSV:
```csv
url,content,rawContent,created_date
https://github.com/microsoft/vscode,Microsoft Visual Studio Code editor,Check out this awesome code editor,2024-01-15T10:30:00Z
https://docs.python.org/3/,Python Documentation,Learn Python programming,2024-01-15T11:00:00Z
```

## 🤖 LLM Provider Configuration

### Local Models (Free)
- **Mistral 7B** - Good balance of quality and speed
- **Ollama** - Various local models available
- **Custom Local API** - Configure your own local endpoint

### Cloud Models (Paid)
- **OpenAI GPT-4** - Highest quality, higher cost
- **OpenAI GPT-3.5** - Good quality, lower cost
- **Anthropic Claude** - Excellent reasoning capabilities

### Cost Estimation
The platform provides real-time cost estimates based on:
- Number of items to process
- Average tokens per item
- Provider-specific pricing
- Input/output token ratios

## 🔧 Configuration

### LLM Settings
```python
LLM_CONFIG = {
    "api_url": "http://localhost:1234/v1/chat/completions",
    "model_name": "mistralai/mistral-7b-instruct-v0.3",
    "temperature": 0.1,
    "max_tokens": 2000,
    "timeout": 45
}
```

### Pipeline Settings
```python
PIPELINE_CONFIG = {
    "batch_size": 1,
    "checkpoint_frequency": 5,
    "quality_threshold": 0.2,
    "enable_duplicates_check": False
}
```

## 📊 Analytics Features

### Dashboard Metrics
- **Total Items Processed** - Complete count of processed items
- **Success Rate** - Percentage of successful processing
- **Average Processing Time** - Time per item analysis
- **Categories Found** - Number of unique content categories

### Visualizations
- **Category Distribution** - Pie chart showing content type breakdown
- **Processing Timeline** - Line chart of processing activity over time
- **Word Cloud** - Visual representation of most common tags
- **Domain Statistics** - Bar chart of top domains processed

### Statistics
- **Processing Performance** - Success rates, error categories, retry statistics
- **Content Analysis** - Category distribution, tag frequency, content types
- **Domain Analysis** - Success rates by domain, problematic domains

## 📥 Export Formats

### JSON Export
```json
{
  "url": "https://example.com",
  "category": "technical",
  "tags": ["python", "programming"],
  "summary": "Technical content about Python programming",
  "processing_metadata": {
    "timestamp": "2024-01-15T12:00:00Z",
    "processing_success": true
  }
}
```

### Excel Export
- Formatted headers with styling
- Auto-sized columns
- Multiple sheets for different data types
- Conditional formatting for status indicators

### Notion Export
- Prepared format for Notion database import
- Truncated fields to meet Notion limits
- Structured properties for easy database setup

## 🛠️ Advanced Features

### Real-time Processing
- Live progress bars with item-by-item updates
- Real-time result preview during processing
- Background processing with status updates
- Error handling and retry mechanisms

### Filtering and Search
- Multi-column filtering
- Date range selection
- Status-based filtering (Success/Failed)
- Category-based filtering
- Full-text search across all fields

### Batch Operations
- Select multiple items for bulk operations
- Batch export of selected items
- Bulk reprocessing of failed items
- Batch category assignment

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Install missing dependencies
   pip install -r requirements.txt
   ```

2. **Processing Failures**
   - Check LLM API configuration
   - Verify internet connection for cloud models
   - Ensure local models are running

3. **Performance Issues**
   - Reduce batch size
   - Increase timeout settings
   - Use local models for faster processing

4. **Memory Issues**
   - Process smaller batches
   - Clear session data regularly
   - Use CSV export for large datasets

### Debug Mode
```bash
# Run with debug logging
streamlit run streamlit_app.py --logger.level=debug
```

## 📈 Performance Tips

1. **Batch Size Optimization**
   - Small batches (1-3) for stability
   - Larger batches (5-10) for speed
   - Adjust based on your system resources

2. **Local vs Cloud Models**
   - Local models: Faster, free, lower quality
   - Cloud models: Slower, paid, higher quality

3. **Processing Options**
   - Disable OCR for text-only content
   - Skip thread collection for simple posts
   - Use caching for repeated processing

## 🤝 Contributing

To extend the platform:

1. **Add New LLM Providers**
   - Update `CostEstimator` class
   - Add provider configuration
   - Test cost estimation accuracy

2. **Create New Visualizations**
   - Extend `AnalyticsDashboard` class
   - Add new chart types
   - Implement interactive features

3. **Add Export Formats**
   - Extend `ExportManager` class
   - Add format-specific converters
   - Test with various data sizes

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Streamlit for the excellent web framework
- Plotly for interactive visualizations
- WordCloud for tag visualization
- All the LLM providers for their APIs

---

**Happy Analyzing! 🎉**