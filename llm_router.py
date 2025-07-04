import asyncio
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time
import re

logger = logging.getLogger(__name__)

class TaskType(Enum):
    SIMPLE_CATEGORIZATION = "simple_categorization"
    MEDIUM_ANALYSIS = "medium_analysis"
    COMPLEX_THREAD = "complex_thread"

class Provider(Enum):
    GEMINI_FLASH = "gemini_flash"
    CLAUDE_HAIKU = "claude_haiku"
    CLAUDE_SONNET = "claude_sonnet"
    GPT_4O_MINI = "gpt_4o_mini"
    GPT_4O = "gpt_4o"
    LOCAL = "local"

@dataclass
class LLMResponse:
    content: str
    provider: Provider
    cost: float
    tokens_used: int
    response_time: float

@dataclass
class ProviderConfig:
    name: str
    cost_per_1k_tokens: float
    max_tokens: int
    available: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class CloudLLMRouter:
    def __init__(self):
        # Provider costs per 1k tokens (input + output combined estimate)
        self.PROVIDER_COSTS = {
            Provider.GEMINI_FLASH: 0.0,      # Free tier
            Provider.CLAUDE_HAIKU: 0.0015,   # $0.25 input + $1.25 output per 1M tokens
            Provider.CLAUDE_SONNET: 0.006,   # $3 input + $15 output per 1M tokens
            Provider.GPT_4O_MINI: 0.0006,    # $0.15 input + $0.60 output per 1M tokens
            Provider.GPT_4O: 0.015,          # $5 input + $15 output per 1M tokens
            Provider.LOCAL: 0.0              # Free local inference
        }
        
        # Task type to optimal provider mapping
        self.TASK_PROVIDERS = {
            TaskType.SIMPLE_CATEGORIZATION: [
                Provider.GEMINI_FLASH,
                Provider.GPT_4O_MINI,
                Provider.CLAUDE_HAIKU
            ],
            TaskType.MEDIUM_ANALYSIS: [
                Provider.CLAUDE_HAIKU,
                Provider.GPT_4O_MINI,
                Provider.GEMINI_FLASH
            ],
            TaskType.COMPLEX_THREAD: [
                Provider.CLAUDE_SONNET,
                Provider.GPT_4O,
                Provider.CLAUDE_HAIKU
            ]
        }
        
        # Global fallback chain
        self.FALLBACK_CHAIN = [
            Provider.GEMINI_FLASH,
            Provider.CLAUDE_HAIKU,
            Provider.CLAUDE_SONNET,
            Provider.LOCAL
        ]
        
        # Provider configurations
        self.providers: Dict[Provider, ProviderConfig] = {
            Provider.GEMINI_FLASH: ProviderConfig(
                name="Gemini Flash",
                cost_per_1k_tokens=0.0,
                max_tokens=1000000
            ),
            Provider.CLAUDE_HAIKU: ProviderConfig(
                name="Claude Haiku",
                cost_per_1k_tokens=0.0015,
                max_tokens=200000
            ),
            Provider.CLAUDE_SONNET: ProviderConfig(
                name="Claude Sonnet",
                cost_per_1k_tokens=0.006,
                max_tokens=200000
            ),
            Provider.GPT_4O_MINI: ProviderConfig(
                name="GPT-4o Mini",
                cost_per_1k_tokens=0.0006,
                max_tokens=128000
            ),
            Provider.GPT_4O: ProviderConfig(
                name="GPT-4o",
                cost_per_1k_tokens=0.015,
                max_tokens=128000
            ),
            Provider.LOCAL: ProviderConfig(
                name="Local Model",
                cost_per_1k_tokens=0.0,
                max_tokens=8000
            )
        }
        
        # Cost tracking
        self.total_cost = 0.0
        self.requests_count = 0
        self.provider_usage: Dict[Provider, int] = {p: 0 for p in Provider}
        
    def estimate_cost(self, text: str, provider: Provider) -> float:
        """Estimate cost for processing text with given provider"""
        tokens = len(text) / 4  # rough estimate: 1 token ≈ 4 characters
        return self.PROVIDER_COSTS[provider] * tokens / 1000
    
    def classify_task_type(self, prompt: str) -> TaskType:
        """Classify task type based on prompt content and complexity"""
        prompt_lower = prompt.lower()
        
        # Simple categorization keywords
        simple_keywords = [
            'categorize', 'classify', 'tag', 'label', 'sort', 'group',
            'yes/no', 'true/false', 'pick', 'choose', 'select'
        ]
        
        # Complex analysis keywords
        complex_keywords = [
            'analyze', 'explain', 'summarize', 'compare', 'evaluate',
            'reasoning', 'logic', 'step by step', 'detailed',
            'comprehensive', 'deep dive', 'thorough'
        ]
        
        # Check for simple categorization
        if any(keyword in prompt_lower for keyword in simple_keywords):
            return TaskType.SIMPLE_CATEGORIZATION
        
        # Check for complex analysis
        if any(keyword in prompt_lower for keyword in complex_keywords):
            return TaskType.COMPLEX_THREAD
        
        # Check prompt length and complexity
        words = len(prompt.split())
        sentences = len(re.split(r'[.!?]+', prompt))
        
        if words < 50 and sentences <= 2:
            return TaskType.SIMPLE_CATEGORIZATION
        elif words > 200 or sentences > 10:
            return TaskType.COMPLEX_THREAD
        else:
            return TaskType.MEDIUM_ANALYSIS
    
    def select_optimal_provider(self, task_type: TaskType, text: str) -> Provider:
        """Select the optimal provider based on task type and cost"""
        candidates = self.TASK_PROVIDERS[task_type]
        
        # Filter available providers
        available_providers = [
            p for p in candidates 
            if self.providers[p].available and 
            len(text) / 4 < self.providers[p].max_tokens
        ]
        
        if not available_providers:
            # Fall back to general fallback chain
            available_providers = [
                p for p in self.FALLBACK_CHAIN 
                if self.providers[p].available
            ]
        
        if not available_providers:
            raise RuntimeError("No available providers found")
        
        # Select cheapest available provider
        return min(available_providers, key=lambda p: self.PROVIDER_COSTS[p])
    
    async def call_provider(self, provider: Provider, prompt: str, **kwargs) -> LLMResponse:
        """Call specific provider with error handling"""
        start_time = time.time()
        
        try:
            # Simulate API call - in real implementation, this would call actual APIs
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Mock response based on provider
            if provider == Provider.GEMINI_FLASH:
                content = f"[Gemini Flash] {prompt[:100]}..."
            elif provider == Provider.CLAUDE_HAIKU:
                content = f"[Claude Haiku] {prompt[:100]}..."
            elif provider == Provider.CLAUDE_SONNET:
                content = f"[Claude Sonnet] {prompt[:100]}..."
            elif provider == Provider.GPT_4O_MINI:
                content = f"[GPT-4o Mini] {prompt[:100]}..."
            elif provider == Provider.GPT_4O:
                content = f"[GPT-4o] {prompt[:100]}..."
            elif provider == Provider.LOCAL:
                content = f"[Local Model] {prompt[:100]}..."
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            # Calculate metrics
            response_time = time.time() - start_time
            tokens_used = len(prompt + content) // 4
            cost = self.estimate_cost(prompt + content, provider)
            
            # Update tracking
            self.total_cost += cost
            self.requests_count += 1
            self.provider_usage[provider] += 1
            
            return LLMResponse(
                content=content,
                provider=provider,
                cost=cost,
                tokens_used=tokens_used,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Error calling {provider.value}: {str(e)}")
            raise
    
    async def route_request(self, prompt: str, **kwargs) -> LLMResponse:
        """Route request to optimal provider with fallback chain"""
        # Classify task type
        task_type = self.classify_task_type(prompt)
        logger.info(f"Classified task as: {task_type.value}")
        
        # Select optimal provider
        primary_provider = self.select_optimal_provider(task_type, prompt)
        logger.info(f"Selected primary provider: {primary_provider.value}")
        
        # Try primary provider first
        try:
            return await self.call_provider(primary_provider, prompt, **kwargs)
        except Exception as e:
            logger.warning(f"Primary provider {primary_provider.value} failed: {str(e)}")
        
        # Try fallback chain
        fallback_providers = [
            p for p in self.FALLBACK_CHAIN 
            if p != primary_provider and self.providers[p].available
        ]
        
        for provider in fallback_providers:
            try:
                logger.info(f"Trying fallback provider: {provider.value}")
                return await self.call_provider(provider, prompt, **kwargs)
            except Exception as e:
                logger.warning(f"Fallback provider {provider.value} failed: {str(e)}")
                continue
        
        # If all providers fail
        raise RuntimeError("All providers failed")
    
    def get_cost_report(self) -> Dict[str, Any]:
        """Generate cost and usage report"""
        return {
            "total_cost": round(self.total_cost, 6),
            "total_requests": self.requests_count,
            "average_cost_per_request": round(
                self.total_cost / max(self.requests_count, 1), 6
            ),
            "provider_usage": {
                provider.value: count 
                for provider, count in self.provider_usage.items()
                if count > 0
            },
            "cost_by_provider": {
                provider.value: round(
                    self.PROVIDER_COSTS[provider] * count, 6
                )
                for provider, count in self.provider_usage.items()
                if count > 0
            }
        }
    
    def set_provider_availability(self, provider: Provider, available: bool):
        """Set provider availability status"""
        self.providers[provider].available = available
        logger.info(f"Set {provider.value} availability to {available}")
    
    def update_provider_config(self, provider: Provider, **kwargs):
        """Update provider configuration"""
        config = self.providers[provider]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        logger.info(f"Updated {provider.value} configuration: {kwargs}")

# Example usage and testing
async def main():
    router = CloudLLMRouter()
    
    # Test different types of prompts
    test_prompts = [
        ("Categorize this email as spam or not spam", TaskType.SIMPLE_CATEGORIZATION),
        ("Analyze the sentiment of this customer review", TaskType.MEDIUM_ANALYSIS),
        ("Provide a comprehensive analysis of market trends", TaskType.COMPLEX_THREAD)
    ]
    
    print("=== CloudLLMRouter Test ===")
    
    for prompt, expected_type in test_prompts:
        print(f"\nTesting: {prompt}")
        
        # Test task classification
        classified_type = router.classify_task_type(prompt)
        print(f"Classified as: {classified_type.value}")
        print(f"Expected: {expected_type.value}")
        print(f"Match: {classified_type == expected_type}")
        
        # Test routing
        try:
            response = await router.route_request(prompt)
            print(f"Provider: {response.provider.value}")
            print(f"Cost: ${response.cost:.6f}")
            print(f"Response time: {response.response_time:.3f}s")
            print(f"Tokens: {response.tokens_used}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # Print cost report
    print("\n=== Cost Report ===")
    report = router.get_cost_report()
    for key, value in report.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())