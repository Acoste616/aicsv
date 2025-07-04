import asyncio
import logging
from llm_router import CloudLLMRouter, Provider, TaskType

# Setup logging
logging.basicConfig(level=logging.INFO)

async def demo_router():
    """Demonstrate CloudLLMRouter usage"""
    router = CloudLLMRouter()
    
    print("🚀 CloudLLMRouter Demo")
    print("=" * 50)
    
    # Example prompts for different use cases
    test_cases = [
        {
            "prompt": "Is this tweet positive or negative: 'I love this product!'",
            "description": "Simple classification task"
        },
        {
            "prompt": "Analyze the main themes in this customer feedback and suggest improvements",
            "description": "Medium analysis task"
        },
        {
            "prompt": "Provide a comprehensive step-by-step analysis of our marketing strategy, including competitor analysis, market positioning, ROI calculations, and detailed recommendations for the next quarter",
            "description": "Complex analysis task"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['description']}")
        print(f"Prompt: {test_case['prompt'][:80]}...")
        
        try:
            # Route the request
            response = await router.route_request(test_case['prompt'])
            
            print(f"✅ Success!")
            print(f"   Provider: {response.provider.value}")
            print(f"   Cost: ${response.cost:.6f}")
            print(f"   Response time: {response.response_time:.3f}s")
            print(f"   Tokens used: {response.tokens_used}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    # Demonstrate fallback mechanism
    print(f"\n🔄 Testing Fallback Mechanism")
    print("-" * 30)
    
    # Disable primary provider
    router.set_provider_availability(Provider.GEMINI_FLASH, False)
    print("Disabled Gemini Flash")
    
    try:
        response = await router.route_request("Categorize this as important or not important")
        print(f"✅ Fallback successful!")
        print(f"   Used provider: {response.provider.value}")
        print(f"   Cost: ${response.cost:.6f}")
    except Exception as e:
        print(f"❌ Fallback failed: {str(e)}")
    
    # Re-enable for final report
    router.set_provider_availability(Provider.GEMINI_FLASH, True)
    
    # Generate cost report
    print(f"\n💰 Cost Report")
    print("=" * 30)
    report = router.get_cost_report()
    
    for key, value in report.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

if __name__ == "__main__":
    asyncio.run(demo_router())