"""
Integration script to use Multi-Model Processing with existing bookmark analysis
"""

import asyncio
import pandas as pd
import json
from pathlib import Path
from multi_model_processor import MultiModelProcessor
from content_extractor import EnhancedContentExtractor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def process_bookmarks_with_multimodel(csv_file: str, output_file: str = "multimodel_results.json"):
    """Process Twitter bookmarks using the multi-model system"""
    
    print("🚀 Starting Multi-Model Bookmark Processing")
    print("="*60)
    
    # Initialize components
    api_keys = {
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', ''),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', '')
    }
    
    if not any(api_keys.values()):
        print("❌ No API keys configured. Please set up at least one in .env file:")
        print("   GEMINI_API_KEY=your_key")
        print("   ANTHROPIC_API_KEY=your_key")
        print("   OPENAI_API_KEY=your_key")
        return [], []
    
    # Initialize processors
    print("\n🔧 Initializing processors...")
    processor = MultiModelProcessor(api_keys)
    content_extractor = EnhancedContentExtractor(max_workers=4)
    
    # Load bookmarks
    print(f"\n📂 Loading bookmarks from {csv_file}...")
    df = pd.read_csv(csv_file)
    print(f"✅ Loaded {len(df)} bookmarks")
    
    # Process bookmarks
    results = []
    failed = []
    
    for idx, row in df.iterrows():
        print(f"\n📝 Processing {idx+1}/{len(df)}: {row.get('text', '')[:50]}...")
        
        try:
            # Extract URL from tweet
            urls = content_extractor._extract_urls(row.get('text', ''))
            url = urls[0] if urls else None
            
            # Extract content from URL if available
            content = row.get('text', '')
            metadata = {
                'source': 'twitter',
                'author': row.get('author', 'Unknown'),
                'date': row.get('date', ''),
                'original_tweet': content
            }
            
            if url:
                print(f"  🔗 Extracting content from: {url}")
                extracted = content_extractor.extract_from_url(url)
                
                if extracted and extracted.get('content'):
                    # Combine tweet and extracted content
                    content = f"Tweet: {content}\n\nExtracted Content:\n{extracted['content']}"
                    metadata['url'] = url
                    metadata['title'] = extracted.get('title', '')
            
            # Process with multi-model system
            result = await processor.process_content(content, metadata)
            
            # Store result
            if result.result and result.result.get('success'):
                results.append({
                    'id': result.id,
                    'tweet': row.get('text', ''),
                    'url': metadata.get('url', ''),
                    'complexity': result.complexity.value,
                    'model_used': result.model_type.value,
                    'processing_time': result.processing_time,
                    'analysis': result.result.get('response', ''),
                    'metadata': metadata
                })
                print(f"  ✅ Processed with {result.model_type.value} (complexity: {result.complexity.value})")
            else:
                failed.append({
                    'tweet': row.get('text', ''),
                    'error': result.result.get('error', 'Unknown error') if result.result else 'No result'
                })
                print(f"  ❌ Failed: {result.result.get('error', 'Unknown') if result.result else 'No result'}")
                
        except Exception as e:
            failed.append({
                'tweet': row.get('text', ''),
                'error': str(e)
            })
            print(f"  ❌ Error: {e}")
    
    # Save results
    print(f"\n\n💾 Saving results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_processed': len(df),
                'successful': len(results),
                'failed': len(failed),
                'models_used': list(set(r['model_used'] for r in results)),
                'complexity_distribution': {
                    'simple': len([r for r in results if r['complexity'] == 'simple']),
                    'medium': len([r for r in results if r['complexity'] == 'medium']),
                    'complex': len([r for r in results if r['complexity'] == 'complex'])
                }
            },
            'results': results,
            'failed': failed
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Results saved to {output_file}")
    
    # Display summary
    print("\n📊 Processing Summary:")
    print(f"  Total bookmarks: {len(df)}")
    print(f"  Successfully processed: {len(results)}")
    print(f"  Failed: {len(failed)}")
    
    if results:
        print("\n  Model usage:")
        model_counts = {}
        for r in results:
            model = r['model_used']
            model_counts[model] = model_counts.get(model, 0) + 1
        
        for model, count in model_counts.items():
            print(f"    {model}: {count} items")
    
    # Get system stats
    stats = processor.get_system_stats()
    kb_stats = stats.get('knowledge_base_stats', {})
    print(f"\n  Knowledge base entries: {kb_stats.get('total_entries', 0)}")
    
    return results, failed

async def create_summary_report(results: list, output_file: str = "bookmark_insights.md"):
    """Create a markdown summary report from processed results"""
    
    print(f"\n📝 Creating summary report...")
    
    report = ["# Twitter Bookmark Analysis Report\n"]
    report.append(f"Generated using Multi-Model AI Processing\n")
    report.append(f"Total bookmarks analyzed: {len(results)}\n")
    
    # Group by complexity
    complexity_groups = {
        'simple': [],
        'medium': [],
        'complex': []
    }
    
    for result in results:
        complexity_groups[result['complexity']].append(result)
    
    # Add sections for each complexity level
    for complexity, items in complexity_groups.items():
        if items:
            report.append(f"\n## {complexity.capitalize()} Content ({len(items)} items)\n")
            
            for item in items[:5]:  # Show top 5 from each category
                report.append(f"### 📌 {item['tweet'][:100]}...\n")
                
                if item.get('url'):
                    report.append(f"**URL**: {item['url']}\n")
                
                report.append(f"**Model**: {item['model_used']}\n")
                report.append(f"**Processing Time**: {item['processing_time']:.2f}s\n")
                
                # Try to parse analysis as JSON
                try:
                    analysis = json.loads(item['analysis'])
                    if isinstance(analysis, dict):
                        for key, value in analysis.items():
                            report.append(f"\n**{key.replace('_', ' ').title()}**:\n{value}\n")
                except:
                    # If not JSON, display as text
                    report.append(f"\n**Analysis**:\n{item['analysis'][:500]}...\n")
                
                report.append("\n---\n")
    
    # Save report
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"✅ Report saved to {output_file}")

# Command-line interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python integrate_multimodel.py <bookmarks.csv> [output.json]")
        print("\nExample: python integrate_multimodel.py bookmarks.csv results.json")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "multimodel_results.json"
    
    # Check if CSV file exists
    if not Path(csv_file).exists():
        print(f"❌ Error: File '{csv_file}' not found")
        sys.exit(1)
    
    # Run processing
    async def main():
        results, failed = await process_bookmarks_with_multimodel(csv_file, output_file)
        
        # Create summary report
        if results:
            await create_summary_report(results, "bookmark_insights.md")
    
    asyncio.run(main())