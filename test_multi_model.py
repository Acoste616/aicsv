"""
Test script for Multi-Model Processing System
"""

import asyncio
import os
from dotenv import load_dotenv
from multi_model_processor import MultiModelProcessor, ContentComplexity

# Load environment variables
load_dotenv()

async def test_system():
    """Test the multi-model processing system"""
    
    print("🚀 Multi-Model Processing System Test")
    print("="*50)
    
    # Check for API keys
    api_keys = {
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', ''),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', '')
    }
    
    # Display available models
    print("\n📋 API Key Status:")
    for key, value in api_keys.items():
        status = "✅ Configured" if value else "❌ Missing"
        print(f"  {key}: {status}")
    
    if not any(api_keys.values()):
        print("\n⚠️  No API keys found. Please configure at least one in .env file")
        return
    
    # Initialize processor
    print("\n🔧 Initializing processor...")
    try:
        processor = MultiModelProcessor(api_keys)
        print("✅ Processor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Test content samples
    test_samples = [
        {
            'content': "Hello world! This is a simple test.",
            'metadata': {'source': 'test', 'type': 'simple'}
        },
        {
            'content': "Machine learning algorithms can be categorized into supervised, unsupervised, and reinforcement learning. Each approach has its own strengths and use cases in solving different types of problems.",
            'metadata': {'source': 'test', 'type': 'medium'}
        },
        {
            'content': """
            Implementing a distributed consensus algorithm like Raft involves several key components:
            
            1. Leader Election: Nodes start as followers and can become candidates
            2. Log Replication: The leader replicates log entries to followers
            3. Safety: Only committed entries are applied to state machines
            
            ```python
            class RaftNode:
                def __init__(self, node_id, peers):
                    self.node_id = node_id
                    self.peers = peers
                    self.state = 'follower'
                    self.current_term = 0
                    self.voted_for = None
                    self.log = []
                    
                def request_vote(self, term, candidate_id):
                    if term > self.current_term:
                        self.current_term = term
                        self.voted_for = None
                    
                    if self.voted_for is None or self.voted_for == candidate_id:
                        self.voted_for = candidate_id
                        return True
                    return False
            ```
            
            The algorithm ensures that there's at most one leader per term and maintains consistency across the cluster even in the presence of network partitions and node failures.
            """,
            'metadata': {'source': 'test', 'type': 'complex'}
        }
    ]
    
    # Process each sample
    print("\n🔄 Processing test samples...")
    results = []
    
    for i, sample in enumerate(test_samples):
        print(f"\n📝 Sample {i+1}:")
        print(f"  Content preview: {sample['content'][:50]}...")
        
        try:
            result = await processor.process_content(
                sample['content'],
                sample['metadata']
            )
            
            print(f"  ✅ Processed successfully")
            print(f"  Complexity: {result.complexity.value}")
            print(f"  Model used: {result.model_type.value}")
            print(f"  Processing time: {result.processing_time:.2f}s")
            
            if result.result and result.result.get('success'):
                print(f"  Response preview: {result.result.get('response', '')[:100]}...")
            else:
                print(f"  ⚠️  Processing failed: {result.result.get('error', 'Unknown error')}")
            
            results.append(result)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Test batch processing
    print("\n\n🔄 Testing batch processing...")
    try:
        csv_data = [
            {'content': sample['content'], **sample['metadata']} 
            for sample in test_samples
        ]
        
        batch_results = await processor.process_csv_batch(csv_data)
        print(f"✅ Batch processed {len(batch_results)} items")
        
    except Exception as e:
        print(f"❌ Batch processing error: {e}")
    
    # Display system stats
    print("\n\n📊 System Statistics:")
    stats = processor.get_system_stats()
    
    print("\nCache Stats:")
    cache_stats = stats.get('cache_stats', {}).get('cache_stats', [])
    if cache_stats:
        for stat in cache_stats:
            print(f"  {stat['model']} ({stat['complexity']}): {stat['count']} requests")
    else:
        print("  No cache data yet")
    
    print("\nKnowledge Base Stats:")
    kb_stats = stats.get('knowledge_base_stats', {})
    print(f"  Total entries: {kb_stats.get('total_entries', 0)}")
    print(f"  Avg processing time: {kb_stats.get('avg_processing_time', 0):.2f}s")
    
    # Test search functionality
    print("\n\n🔍 Testing knowledge base search...")
    search_results = processor.knowledge_base.search("machine learning", limit=5)
    print(f"Found {len(search_results)} results for 'machine learning'")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_system())