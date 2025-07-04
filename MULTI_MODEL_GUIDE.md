# Multi-Model Content Processing System Guide

## Overview

This system implements the architecture you specified:
- **CSV Upload** → **Smart Queue** → **Content Routing** → **AI Processing** → **Results Cache** → **Knowledge Base** → **Streamlit Dashboard**

## Architecture Components

### 1. Content Classification
Content is automatically classified into three complexity levels:
- **Simple**: Short, non-technical content (< 500 chars) → Routed to Gemini Flash
- **Medium**: Moderate length with some technical content → Routed to Claude Haiku  
- **Complex**: Long, technical content with code/data → Routed to GPT-4o

### 2. Smart Queue System
- Prioritizes content based on complexity and metadata
- Handles concurrent processing with configurable batch sizes
- Implements retry logic for failed requests

### 3. Results Caching
- SQLite-based cache prevents reprocessing identical content
- Indexed by content hash for fast lookups
- Tracks processing times and model usage

### 4. Knowledge Base
- JSON-based storage for processed results
- Full-text search capabilities
- Preserves analysis results and metadata

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_multimodel.txt
```

### 2. Configure API Keys
Create a `.env` file with your API keys:
```env
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
```

### 3. Run the Dashboard
```bash
streamlit run streamlit_dashboard.py
```

### 4. Process Content
1. Upload a CSV file (see `example_content.csv` for format)
2. Map columns (content + optional metadata)
3. Click "Start Processing"
4. View results in real-time

## Dashboard Features

### Upload & Process Tab
- CSV file upload with preview
- Column mapping for content and metadata
- Batch processing with progress tracking
- Export results as CSV

### Analytics Tab
- Cache performance metrics
- Model usage distribution
- Processing time analysis
- Visual charts and graphs

### Knowledge Base Tab
- Search processed content
- View detailed analysis results
- Export knowledge base as JSON

### Performance Tab
- Processing timeline visualization
- Model performance comparison
- Complexity distribution charts

### Logs Tab
- Real-time processing logs
- Filter by status, time, and model
- Detailed error tracking

## API Usage (Without Dashboard)

```python
import asyncio
from multi_model_processor import MultiModelProcessor

# Initialize processor
api_keys = {
    'GEMINI_API_KEY': 'your_key',
    'ANTHROPIC_API_KEY': 'your_key', 
    'OPENAI_API_KEY': 'your_key'
}

processor = MultiModelProcessor(api_keys)

# Process single content
async def process_example():
    result = await processor.process_content(
        "Your content here",
        metadata={'source': 'example'}
    )
    print(f"Processed with {result.model_type.value}: {result.result}")

# Process CSV batch
async def process_csv():
    csv_data = [
        {'content': 'Simple text', 'source': 'test'},
        {'content': 'Complex technical content...', 'category': 'tech'}
    ]
    results = await processor.process_csv_batch(csv_data)
    for r in results:
        print(f"{r.id}: {r.complexity.value} -> {r.model_type.value}")

# Run processing
asyncio.run(process_example())
```

## Configuration Options

### Content Complexity Thresholds
Edit in `multi_model_processor.py`:
```python
self.simple_threshold = 500   # characters
self.medium_threshold = 2000  # characters
```

### Model Routing
Customize model selection in `AIModelRouter.__init__`:
```python
self.model_mapping = {
    ContentComplexity.SIMPLE: ModelType.GEMINI_FLASH,
    ContentComplexity.MEDIUM: ModelType.CLAUDE_HAIKU,
    ContentComplexity.COMPLEX: ModelType.GPT_4O
}
```

### Processing Prompts
Modify the analysis prompt in `process_content`:
```python
prompt = """Analyze the following content and provide a structured analysis including:
1. Main topic and summary
2. Key points and insights
3. Technical details (if any)
4. Actionable takeaways
5. Related topics and keywords

Provide the response in JSON format."""
```

## Troubleshooting

### Missing API Keys
- Ensure all required API keys are configured
- The system will only use models with valid keys

### Processing Errors
- Check the Logs tab for detailed error messages
- Common issues: rate limits, network timeouts, invalid API keys

### Cache Issues
- Delete `cache/results_cache.db` to clear cache
- Cache automatically handles duplicates

### Knowledge Base
- Stored in `knowledge_base.json`
- Backup regularly if processing large volumes

## Performance Tips

1. **Batch Processing**: Process multiple items together for efficiency
2. **Concurrent Requests**: Adjust based on API rate limits
3. **Caching**: Leverage cache for repeated content
4. **Model Selection**: Use simpler models for basic content to save costs

## Cost Optimization

- **Gemini Flash**: Free tier available, best for simple content
- **Claude Haiku**: Cost-effective for medium complexity
- **GPT-4o**: Premium model for complex analysis

Monitor usage in the Analytics tab to optimize model selection.

## Next Steps

1. Customize complexity classification logic
2. Add more AI models (e.g., Mistral, Llama)
3. Implement batch upload from multiple sources
4. Set up automated processing pipelines
5. Create custom analysis templates