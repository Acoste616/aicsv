import pandas as pd
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
from tqdm.asyncio import tqdm
import asyncio_throttle

from llm_router import CloudLLMRouter, LLMProvider

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CloudContentProcessor:
    """Enhanced content processor using cloud LLM providers"""
    
    def __init__(self, 
                 gemini_api_key: Optional[str] = None,
                 anthropic_api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 monthly_budget: float = 10.0,
                 max_concurrent: int = 10):
        """Initialize processor with cloud LLM router"""
        self.router = CloudLLMRouter(
            gemini_api_key=gemini_api_key or os.getenv("GEMINI_API_KEY"),
            anthropic_api_key=anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=openai_api_key or os.getenv("OPENAI_API_KEY"),
            monthly_budget=monthly_budget
        )
        self.max_concurrent = max_concurrent
        self.throttler = asyncio_throttle.Throttler(rate_limit=10, period=1.0)  # 10 requests per second
    
    async def process_single_content(self, 
                                   content: str, 
                                   task_type: str = "analyze",
                                   force_provider: Optional[LLMProvider] = None) -> Dict[str, Any]:
        """Process single content item with rate limiting"""
        async with self.throttler:
            try:
                result = await self.router.process(
                    text=content,
                    task_type=task_type,
                    force_provider=force_provider,
                    output_format="json"
                )
                return result
            except Exception as e:
                logger.error(f"Error processing content: {str(e)}")
                return {
                    "result": {"error": str(e)},
                    "provider": "none",
                    "complexity": "unknown",
                    "cost": 0.0,
                    "tokens": 0
                }
    
    async def process_batch(self, 
                          items: List[Dict[str, Any]], 
                          task_type: str = "analyze",
                          force_provider: Optional[LLMProvider] = None,
                          progress_callback=None) -> List[Dict[str, Any]]:
        """Process batch of items with concurrency control"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(item: Dict[str, Any], index: int):
            async with semaphore:
                content = item.get('text', '') or item.get('content', '')
                result = await self.process_single_content(content, task_type, force_provider)
                
                # Merge results with original item
                processed_item = {**item}
                processed_item.update(result['result'])
                processed_item['provider_used'] = result['provider']
                processed_item['processing_cost'] = result['cost']
                processed_item['token_count'] = result['tokens']
                processed_item['complexity'] = result['complexity']
                
                if progress_callback:
                    progress_callback(index + 1, len(items))
                
                return processed_item
        
        # Process all items concurrently
        tasks = [process_with_semaphore(item, i) for i, item in enumerate(items)]
        
        # Use tqdm for progress bar if available
        if progress_callback is None:
            results = []
            for coro in tqdm.as_completed(tasks, desc="Processing items"):
                result = await coro
                results.append(result)
            return results
        else:
            return await asyncio.gather(*tasks)
    
    async def process_csv(self, 
                        csv_path: str, 
                        output_path: str,
                        task_type: str = "analyze",
                        force_provider: Optional[LLMProvider] = None,
                        text_column: str = "text",
                        batch_size: int = 100) -> Dict[str, Any]:
        """Process CSV file with batching for large files"""
        logger.info(f"Loading CSV from {csv_path}")
        df = pd.read_csv(csv_path)
        
        if text_column not in df.columns:
            raise ValueError(f"Column '{text_column}' not found in CSV")
        
        total_rows = len(df)
        all_results = []
        
        # Process in batches
        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            batch_df = df.iloc[start_idx:end_idx]
            
            logger.info(f"Processing batch {start_idx//batch_size + 1}/{(total_rows-1)//batch_size + 1}")
            
            # Convert to list of dicts
            items = batch_df.to_dict('records')
            
            # Process batch
            batch_results = await self.process_batch(items, task_type, force_provider)
            all_results.extend(batch_results)
            
            # Save intermediate results
            if len(all_results) % (batch_size * 5) == 0:
                temp_df = pd.DataFrame(all_results)
                temp_df.to_csv(output_path.replace('.csv', '_temp.csv'), index=False)
                logger.info(f"Saved intermediate results ({len(all_results)} rows)")
        
        # Create final dataframe
        result_df = pd.DataFrame(all_results)
        
        # Save results
        result_df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(result_df)} processed rows to {output_path}")
        
        # Generate summary
        summary = self.generate_summary(result_df)
        
        # Save summary
        summary_path = output_path.replace('.csv', '_summary.json')
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics from processed data"""
        summary = {
            "total_processed": len(df),
            "processing_date": datetime.now().isoformat(),
            "total_cost": df['processing_cost'].sum() if 'processing_cost' in df.columns else 0,
            "total_tokens": df['token_count'].sum() if 'token_count' in df.columns else 0,
            "cost_summary": self.router.get_cost_summary()
        }
        
        # Provider distribution
        if 'provider_used' in df.columns:
            summary['provider_distribution'] = df['provider_used'].value_counts().to_dict()
        
        # Category distribution
        if 'category' in df.columns:
            summary['category_distribution'] = df['category'].value_counts().to_dict()
        
        # Sentiment distribution
        if 'sentiment' in df.columns:
            summary['sentiment_distribution'] = df['sentiment'].value_counts().to_dict()
        
        # Complexity distribution
        if 'complexity' in df.columns:
            summary['complexity_distribution'] = df['complexity'].value_counts().to_dict()
        
        # Top tags
        if 'tags' in df.columns:
            all_tags = []
            for tags in df['tags'].dropna():
                if isinstance(tags, list):
                    all_tags.extend(tags)
                elif isinstance(tags, str):
                    try:
                        # Try to parse as JSON
                        parsed_tags = json.loads(tags)
                        if isinstance(parsed_tags, list):
                            all_tags.extend(parsed_tags)
                    except:
                        # Fallback to comma-separated
                        all_tags.extend(tags.split(','))
            
            if all_tags:
                from collections import Counter
                tag_counts = Counter(all_tags)
                summary['top_tags'] = dict(tag_counts.most_common(20))
        
        # Error summary
        if 'error' in df.columns:
            error_count = df['error'].notna().sum()
            summary['error_count'] = error_count
            summary['error_rate'] = error_count / len(df) if len(df) > 0 else 0
        
        return summary
    
    async def process_tweets_smart(self, 
                                 csv_path: str,
                                 output_path: str,
                                 force_provider: Optional[LLMProvider] = None):
        """Smart processing for tweets with automatic task detection"""
        df = pd.read_csv(csv_path)
        
        # Prepare items for processing
        items = []
        for _, row in df.iterrows():
            tweet_text = row.get('text', '')
            
            # Detect task type based on content
            if len(tweet_text) > 1000:  # Long thread
                task_type = "thread"
            elif len(tweet_text) < 100:  # Short tweet
                task_type = "categorize"
            else:
                task_type = "analyze"
            
            items.append({
                **row.to_dict(),
                'task_type': task_type
            })
        
        # Group by task type for efficient processing
        from itertools import groupby
        items.sort(key=lambda x: x['task_type'])
        
        all_results = []
        
        for task_type, group_items in groupby(items, key=lambda x: x['task_type']):
            group_list = list(group_items)
            logger.info(f"Processing {len(group_list)} items with task type: {task_type}")
            
            # Process group
            results = await self.process_batch(
                group_list, 
                task_type=task_type,
                force_provider=force_provider
            )
            all_results.extend(results)
        
        # Save results
        result_df = pd.DataFrame(all_results)
        result_df.to_csv(output_path, index=False)
        
        return self.generate_summary(result_df)


async def main():
    """Example usage"""
    # Initialize processor
    processor = CloudContentProcessor(
        monthly_budget=10.0,
        max_concurrent=20
    )
    
    # Check available providers
    available = processor.router.get_available_providers()
    print(f"Available providers: {[p.value for p in available]}")
    
    # Process a CSV file
    summary = await processor.process_csv(
        csv_path="tweets.csv",
        output_path="processed_tweets_cloud.csv",
        task_type="analyze",
        text_column="text",
        batch_size=50
    )
    
    print("\nProcessing Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())