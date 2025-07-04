#!/usr/bin/env python3
"""
Test script to verify LLM providers are working correctly
"""

import os
from dotenv import load_dotenv
from llm_providers import LLMManager

def test_providers():
    """Test all available LLM providers"""
    print("🧪 TESTING LLM PROVIDERS")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Initialize LLM Manager
    print("\n📋 Initializing LLM Manager...")
    try:
        manager = LLMManager(preferred_provider="claude")
        print("✅ LLM Manager initialized")
    except Exception as e:
        print(f"❌ Failed to initialize LLM Manager: {e}")
        return
    
    # List available providers
    available = manager.list_available_providers()
    print(f"\n🔍 Available providers: {available}")
    
    if not available:
        print("\n❌ No providers available!")
        print("\n💡 Make sure to:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your API keys to .env")
        print("   3. Install required libraries: pip install anthropic google-generativeai")
        return
    
    # Test each available provider
    test_prompt = "What is 2+2? Answer with just the number."
    
    for provider_name in available:
        print(f"\n📌 Testing {provider_name} provider...")
        try:
            provider = manager.get_provider(provider_name)
            response = provider.generate(test_prompt, max_tokens=10)
            print(f"✅ {provider_name} response: {response}")
        except Exception as e:
            print(f"❌ {provider_name} error: {e}")
    
    # Test fallback mechanism
    print("\n🔄 Testing fallback mechanism...")
    try:
        # Try to get a non-existent provider
        provider = manager.get_provider("non_existent")
        print(f"✅ Fallback to: {provider.__class__.__name__}")
    except Exception as e:
        print(f"❌ Fallback failed: {e}")
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    test_providers()