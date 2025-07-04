# 🤖 AI Content Processor with Cloud LLM Router

A powerful system for processing content (tweets, articles, etc.) using multiple cloud LLM providers with intelligent routing, cost optimization, and a beautiful web interface.

## 🌟 Features

### Intelligent LLM Routing
- **Automatic provider selection** based on task complexity
- **Cost optimization** - always uses the cheapest suitable provider
- **Fallback chains** - automatic failover when APIs are down
- **Budget management** - stops processing when monthly budget is exceeded

### Provider Support
- **Google Gemini Flash** (Free tier for simple tasks)
- **Claude Haiku/Sonnet** (Anthropic)
- **GPT-4o-mini/GPT-4o** (OpenAI)
- **Automatic fallback** between providers

### Web Interface (Streamlit)
- 📤 **Drag & drop CSV upload**
- 💰 **Real-time cost estimation**
- 📊 **Live processing progress**
- 🎯 **Advanced filtering** of results
- 📥 **Multi-format export** (CSV, Excel, JSON, Notion)
- 📈 **Beautiful dashboard** with analytics

## 📦 Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd ai-content-processor
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
Create a `.env` file with your API keys:
```env
GEMINI_API_KEY=your-gemini-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
```

## 🚀 Quick Start

### Web Interface (Recommended)
```bash
streamlit run streamlit_app.py
```

Then open http://localhost:8501 in your browser.

### Command Line
```python
import asyncio
from fixed_content_processor_cloud import CloudContentProcessor

async def main():
    processor = CloudContentProcessor(monthly_budget=10.0)
    
    summary = await processor.process_csv(
        csv_path="tweets.csv",
        output_path="processed_tweets.csv",
        task_type="analyze"
    )
    print(summary)

asyncio.run(main())
```

## 📊 Task Types

1. **categorize** - Simple categorization (uses cheapest provider)
2. **analyze** - Full analysis with tags, sentiment, entities
3. **summarize** - Generate concise summaries
4. **thread** - Process Twitter threads with narrative extraction

## 💡 Migration Guide (From Local to Cloud)

### Step 1: Install New Dependencies (5 min)
```bash
pip install -r requirements.txt
```

### Step 2: Add API Keys (5 min)
Get free API keys:
- **Gemini**: https://makersuite.google.com/app/apikey
- **Claude**: https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/api-keys

Add to `.env` file:
```env
GEMINI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
```

### Step 3: Update Your Code (10 min)

**Old code:**
```python
from fixed_content_processor import FixedContentProcessor

processor = FixedContentProcessor()
df = processor.process_csv("tweets.csv")
```

**New code:**
```python
import asyncio
from fixed_content_processor_cloud import CloudContentProcessor

async def main():
    processor = CloudContentProcessor(monthly_budget=10.0)
    summary = await processor.process_csv(
        csv_path="tweets.csv",
        output_path="processed_tweets.csv"
    )

asyncio.run(main())
```

### Step 4: Run Streamlit App (2 min)
```bash
streamlit run streamlit_app.py
```

## 💰 Cost Optimization

### Provider Costs (per 1M tokens)
- **Gemini Flash**: FREE (up to limits)
- **Claude Haiku**: $0.25
- **GPT-4o-mini**: $0.15
- **Claude Sonnet**: $3.00
- **GPT-4o**: $2.50

### Automatic Cost Optimization
The router automatically selects providers based on task complexity:

- **Simple tasks** → Gemini Flash (free)
- **Medium tasks** → Claude Haiku or GPT-4o-mini
- **Complex tasks** → Claude Sonnet or GPT-4o

### Budget Management
Set monthly budget:
```python
processor = CloudContentProcessor(monthly_budget=10.0)
```

## 📈 Advanced Features

### Parallel Processing
```python
processor = CloudContentProcessor(
    monthly_budget=10.0,
    max_concurrent=20  # Process 20 items simultaneously
)
```

### Smart Tweet Processing
Automatically detects task type based on content:
```python
summary = await processor.process_tweets_smart(
    csv_path="tweets.csv",
    output_path="smart_processed.csv"
)
```

### Custom Task Types
```python
# Add custom prompt in llm_router.py
prompts = {
    "custom_task": "Your custom prompt here..."
}
```

## 📊 Output Format

Processed CSV includes:
- All original columns
- `title` - Generated title
- `category` - Main category
- `tags` - List of relevant tags
- `sentiment` - positive/negative/neutral
- `key_points` - Main points extracted
- `provider_used` - Which LLM was used
- `processing_cost` - Cost in USD
- `complexity` - Task complexity detected

## 🔧 Configuration

### Environment Variables
- `GEMINI_API_KEY` - Google Gemini API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `OPENAI_API_KEY` - OpenAI API key

### Processing Options
- `task_type` - Type of analysis to perform
- `force_provider` - Force specific provider (optional)
- `batch_size` - Number of items to process at once
- `max_concurrent` - Maximum concurrent API calls

## 🐛 Troubleshooting

### "No LLM providers available"
- Check that API keys are set correctly
- Verify keys are valid in provider dashboards

### "Budget exceeded"
- Increase monthly budget
- Use cheaper providers
- Process smaller batches

### Rate limiting errors
- Reduce `max_concurrent` parameter
- Add delays between batches

## 🚀 Deployment

### Streamlit Cloud (FREE)
1. Push code to GitHub
2. Go to https://share.streamlit.io/
3. Deploy from your repository
4. Add secrets (API keys) in Streamlit settings

### Local Docker
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "streamlit_app.py"]
```

## 📝 Example Use Cases

### Content Categorization
```python
summary = await processor.process_csv(
    csv_path="articles.csv",
    output_path="categorized.csv",
    task_type="categorize"
)
```

### Sentiment Analysis
```python
summary = await processor.process_csv(
    csv_path="reviews.csv",
    output_path="sentiment_analysis.csv",
    task_type="analyze"
)
```

### Thread Analysis
```python
summary = await processor.process_csv(
    csv_path="twitter_threads.csv",
    output_path="thread_analysis.csv",
    task_type="thread"
)
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

MIT License - feel free to use in your projects!

## 🙋‍♀️ Support

- Create an issue for bugs
- Discussions for feature requests
- Wiki for additional documentation 