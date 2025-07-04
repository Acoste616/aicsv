"""
Example usage of the Cloud Content Processor
This script demonstrates various ways to use the system
"""

import asyncio
import pandas as pd
from fixed_content_processor_cloud import CloudContentProcessor
from llm_router import LLMProvider

# Example 1: Basic CSV Processing
async def example_basic_csv():
    """Process a CSV file with default settings"""
    print("Example 1: Basic CSV Processing")
    print("-" * 50)
    
    # Create sample data
    sample_data = pd.DataFrame({
        'text': [
            "Just launched our new AI-powered analytics platform! It uses advanced ML algorithms to predict market trends with 92% accuracy. Check it out at example.com #AI #MachineLearning",
            "Reading this fascinating article about quantum computing breakthroughs. The future of technology is mind-blowing! 🚀",
            "Hot take: No-code platforms are democratizing software development. What used to require years of coding experience can now be done in hours.",
            "Thread: Why I think remote work is here to stay 🧵 1/5 First, productivity has actually increased for most knowledge workers...",
            "New research shows that meditation can literally change your brain structure. Just 8 weeks of practice can increase gray matter density. #Mindfulness #Health"
        ],
        'created_at': pd.date_range('2024-01-01', periods=5, freq='D').astype(str)
    })
    
    # Save sample data
    sample_data.to_csv('sample_tweets.csv', index=False)
    
    # Initialize processor
    processor = CloudContentProcessor(
        monthly_budget=10.0,
        max_concurrent=5
    )
    
    # Process CSV
    summary = await processor.process_csv(
        csv_path='sample_tweets.csv',
        output_path='sample_processed.csv',
        task_type='analyze',
        batch_size=10
    )
    
    print(f"Processed {summary['total_processed']} items")
    print(f"Total cost: ${summary['total_cost']:.4f}")
    print(f"Providers used: {summary.get('provider_distribution', {})}")
    print()


# Example 2: Smart Tweet Processing
async def example_smart_processing():
    """Demonstrate smart processing with automatic task detection"""
    print("\nExample 2: Smart Tweet Processing")
    print("-" * 50)
    
    processor = CloudContentProcessor()
    
    # Process with automatic task type detection
    summary = await processor.process_tweets_smart(
        csv_path='sample_tweets.csv',
        output_path='sample_smart_processed.csv'
    )
    
    print(f"Smart processing complete!")
    print(f"Task complexity distribution: {summary.get('complexity_distribution', {})}")
    print()


# Example 3: Force Specific Provider
async def example_force_provider():
    """Process using a specific LLM provider"""
    print("\nExample 3: Force Specific Provider")
    print("-" * 50)
    
    processor = CloudContentProcessor()
    
    # Check available providers
    available = processor.router.get_available_providers()
    print(f"Available providers: {[p.value for p in available]}")
    
    # Force using Gemini (free tier)
    if LLMProvider.GEMINI_FLASH in available:
        summary = await processor.process_csv(
            csv_path='sample_tweets.csv',
            output_path='sample_gemini_processed.csv',
            task_type='categorize',  # Simple task for free tier
            force_provider=LLMProvider.GEMINI_FLASH,
            batch_size=5
        )
        print(f"Processed with Gemini Flash (free tier)")
        print(f"Cost: ${summary['total_cost']:.4f}")
    print()


# Example 4: Custom Task Processing
async def example_custom_processing():
    """Process individual items with custom logic"""
    print("\nExample 4: Custom Processing")
    print("-" * 50)
    
    processor = CloudContentProcessor()
    
    # Process individual items
    items = [
        {"text": "Breaking: Major tech company announces layoffs", "id": 1},
        {"text": "New study reveals benefits of intermittent fasting", "id": 2},
        {"text": "Thread about building a startup from scratch", "id": 3}
    ]
    
    results = await processor.process_batch(
        items=items,
        task_type='analyze'
    )
    
    # Display results
    for result in results:
        print(f"\nItem {result['id']}:")
        print(f"  Category: {result.get('category', 'N/A')}")
        print(f"  Sentiment: {result.get('sentiment', 'N/A')}")
        print(f"  Provider: {result.get('provider_used', 'N/A')}")
        print(f"  Cost: ${result.get('processing_cost', 0):.6f}")
    print()


# Example 5: Cost Estimation
async def example_cost_estimation():
    """Estimate costs before processing"""
    print("\nExample 5: Cost Estimation")
    print("-" * 50)
    
    processor = CloudContentProcessor()
    
    # Create test data
    test_df = pd.DataFrame({
        'text': ['Sample text'] * 100  # 100 items
    })
    
    # Estimate costs for different providers
    for provider in [LLMProvider.GEMINI_FLASH, LLMProvider.CLAUDE_HAIKU, LLMProvider.GPT_4O_MINI]:
        if provider in processor.router.get_available_providers():
            # Estimate cost
            total_chars = test_df['text'].str.len().sum()
            cost = processor.router.estimate_cost("x" * total_chars, provider)
            print(f"{provider.value}: ${cost:.4f} for {len(test_df)} items")
    print()


# Example 6: Error Handling
async def example_error_handling():
    """Demonstrate error handling and recovery"""
    print("\nExample 6: Error Handling")
    print("-" * 50)
    
    processor = CloudContentProcessor(
        monthly_budget=0.001  # Very low budget to trigger budget exceeded
    )
    
    # Try to process with exceeded budget
    items = [{"text": "Test item " * 100}] * 10  # Large items
    
    results = await processor.process_batch(items, task_type='analyze')
    
    # Check for errors
    errors = [r for r in results if 'error' in r]
    print(f"Processed: {len(results) - len(errors)}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print(f"Error example: {errors[0].get('error', 'Unknown error')}")
    print()


# Main execution
async def main():
    """Run all examples"""
    print("🤖 Cloud Content Processor Examples")
    print("=" * 50)
    
    # Run examples in sequence
    await example_basic_csv()
    await example_smart_processing()
    await example_force_provider()
    await example_custom_processing()
    await example_cost_estimation()
    await example_error_handling()
    
    print("\n✅ All examples completed!")
    print("\nNext steps:")
    print("1. Run 'streamlit run streamlit_app.py' for the web interface")
    print("2. Check the generated CSV files for results")
    print("3. Modify the examples for your use case")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())