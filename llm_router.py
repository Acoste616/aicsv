"""
Cloud LLM Router with automatic provider selection, fallback chain, and cost tracking.
"""

import os
import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import tiktoken
import google.generativeai as genai
from anthropic import Anthropic
import openai
from transformers import pipeline

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task complexity levels for LLM selection."""
    SIMPLE = "simple"          # Proste kategoryzacje
    MEDIUM = "medium"          # Średnie analizy
    COMPLEX = "complex"        # Kompleksowe threads


class Provider(Enum):
    """Available LLM providers."""
    GEMINI_FLASH = "gemini-flash"
    CLAUDE_HAIKU = "claude-haiku"
    CLAUDE_SONNET = "claude-sonnet"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    LOCAL = "local"


@dataclass
class ProviderConfig:
    """Configuration for each LLM provider."""
    name: str
    model_name: str
    cost_per_1k_tokens: float  # Cost in USD per 1000 tokens
    max_tokens: int
    supports_streaming: bool
    free_tier_limit: Optional[int] = None  # Free tokens per day


# Provider configurations with costs
PROVIDER_CONFIGS = {
    Provider.GEMINI_FLASH: ProviderConfig(
        name="Gemini Flash",
        model_name="gemini-1.5-flash",
        cost_per_1k_tokens=0.0,  # Free tier
        max_tokens=8192,
        supports_streaming=True,
        free_tier_limit=1_000_000
    ),
    Provider.CLAUDE_HAIKU: ProviderConfig(
        name="Claude 3 Haiku",
        model_name="claude-3-haiku-20240307",
        cost_per_1k_tokens=0.00025,  # $0.25 per 1M tokens
        max_tokens=4096,
        supports_streaming=True
    ),
    Provider.CLAUDE_SONNET: ProviderConfig(
        name="Claude 3 Sonnet",
        model_name="claude-3-5-sonnet-20241022",
        cost_per_1k_tokens=0.003,  # $3 per 1M tokens
        max_tokens=8192,
        supports_streaming=True
    ),
    Provider.GPT_4O_MINI: ProviderConfig(
        name="GPT-4o-mini",
        model_name="gpt-4o-mini",
        cost_per_1k_tokens=0.00015,  # $0.15 per 1M tokens
        max_tokens=4096,
        supports_streaming=True
    ),
    Provider.GPT_4O: ProviderConfig(
        name="GPT-4o",
        model_name="gpt-4o",
        cost_per_1k_tokens=0.0025,  # $2.50 per 1M tokens
        max_tokens=8192,
        supports_streaming=True
    ),
    Provider.LOCAL: ProviderConfig(
        name="Local Model",
        model_name="microsoft/Phi-3-mini-4k-instruct",
        cost_per_1k_tokens=0.0,
        max_tokens=4096,
        supports_streaming=False
    )
}


# Task type to provider mapping (priority order)
TASK_PROVIDER_MAPPING = {
    TaskType.SIMPLE: [Provider.GEMINI_FLASH, Provider.GPT_4O_MINI, Provider.CLAUDE_HAIKU],
    TaskType.MEDIUM: [Provider.CLAUDE_HAIKU, Provider.GPT_4O_MINI, Provider.GEMINI_FLASH],
    TaskType.COMPLEX: [Provider.CLAUDE_SONNET, Provider.GPT_4O, Provider.CLAUDE_HAIKU]
}


# Fallback chain for each provider
FALLBACK_CHAINS = {
    Provider.GEMINI_FLASH: [Provider.CLAUDE_HAIKU, Provider.GPT_4O_MINI, Provider.LOCAL],
    Provider.CLAUDE_HAIKU: [Provider.GPT_4O_MINI, Provider.GEMINI_FLASH, Provider.LOCAL],
    Provider.CLAUDE_SONNET: [Provider.GPT_4O, Provider.CLAUDE_HAIKU, Provider.LOCAL],
    Provider.GPT_4O_MINI: [Provider.CLAUDE_HAIKU, Provider.GEMINI_FLASH, Provider.LOCAL],
    Provider.GPT_4O: [Provider.CLAUDE_SONNET, Provider.GPT_4O_MINI, Provider.LOCAL],
    Provider.LOCAL: []  # No fallback for local
}


class CloudLLMRouter:
    """Intelligent LLM router with automatic provider selection and fallback."""
    
    def __init__(self):
        self.providers = {}
        self.cost_tracker = CostTracker()
        self.usage_stats = {}
        self.failed_providers = set()
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available LLM providers."""
        # Gemini
        if os.getenv("GOOGLE_API_KEY"):
            try:
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                self.providers[Provider.GEMINI_FLASH] = genai.GenerativeModel(
                    PROVIDER_CONFIGS[Provider.GEMINI_FLASH].model_name
                )
                logger.info("Initialized Gemini Flash provider")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        
        # Claude
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.providers[Provider.CLAUDE_HAIKU] = Anthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY")
                )
                self.providers[Provider.CLAUDE_SONNET] = self.providers[Provider.CLAUDE_HAIKU]
                logger.info("Initialized Claude providers")
            except Exception as e:
                logger.error(f"Failed to initialize Claude: {e}")
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                openai.api_key = os.getenv("OPENAI_API_KEY")
                self.providers[Provider.GPT_4O_MINI] = openai
                self.providers[Provider.GPT_4O] = openai
                logger.info("Initialized OpenAI providers")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
        
        # Local fallback
        try:
            self.providers[Provider.LOCAL] = pipeline(
                "text-generation",
                model=PROVIDER_CONFIGS[Provider.LOCAL].model_name,
                device_map="auto"
            )
            logger.info("Initialized local model provider")
        except Exception as e:
            logger.warning(f"Failed to initialize local model: {e}")
    
    def detect_task_type(self, prompt: str) -> TaskType:
        """Automatically detect task complexity from prompt."""
        prompt_lower = prompt.lower()
        
        # Simple tasks: categorization, classification, yes/no
        simple_keywords = ["categorize", "classify", "label", "yes or no", "true or false", 
                          "choose", "select", "which", "tag", "identify type"]
        
        # Complex tasks: analysis, reasoning, creative writing
        complex_keywords = ["analyze", "explain in detail", "create comprehensive", 
                           "design", "develop strategy", "write essay", "debate",
                           "complex reasoning", "multi-step", "detailed analysis"]
        
        # Check for simple tasks
        if any(keyword in prompt_lower for keyword in simple_keywords):
            return TaskType.SIMPLE
        
        # Check for complex tasks
        if any(keyword in prompt_lower for keyword in complex_keywords):
            return TaskType.COMPLEX
        
        # Default to medium
        return TaskType.MEDIUM
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Try tiktoken for accurate estimation
        try:
            encoding = tiktoken.encoding_for_model("gpt-4")
            return len(encoding.encode(text))
        except:
            # Fallback to rough estimation
            return len(text) // 4
    
    def estimate_cost(self, text: str, provider: Provider) -> float:
        """Estimate cost for processing text with given provider."""
        tokens = self.estimate_tokens(text)
        config = PROVIDER_CONFIGS[provider]
        cost = (tokens / 1000) * config.cost_per_1k_tokens
        return cost
    
    def select_optimal_provider(self, prompt: str, task_type: Optional[TaskType] = None) -> Provider:
        """Select the optimal provider based on task type and availability."""
        if task_type is None:
            task_type = self.detect_task_type(prompt)
        
        logger.info(f"Detected task type: {task_type.value}")
        
        # Get providers for this task type
        preferred_providers = TASK_PROVIDER_MAPPING[task_type]
        
        # Try each provider in order
        for provider in preferred_providers:
            if provider not in self.failed_providers and provider in self.providers:
                # Check if within free tier limits
                if provider == Provider.GEMINI_FLASH:
                    daily_usage = self.cost_tracker.get_daily_usage(provider)
                    free_tier_limit = PROVIDER_CONFIGS[provider].free_tier_limit
                    if free_tier_limit is not None and daily_usage < free_tier_limit:
                        return provider
                else:
                    return provider
        
        # If all preferred providers failed, use any available
        for provider, client in self.providers.items():
            if provider not in self.failed_providers:
                return provider
        
        # Last resort: local model
        return Provider.LOCAL
    
    def get_fallback_chain(self, primary_provider: Provider) -> List[Provider]:
        """Get fallback providers for the primary provider."""
        chain = FALLBACK_CHAINS.get(primary_provider, [])
        # Filter out failed providers
        return [p for p in chain if p not in self.failed_providers and p in self.providers]
    
    async def generate_with_fallback(self, prompt: str, provider: Optional[Provider] = None,
                                   max_retries: int = 3) -> Tuple[str, Provider, float]:
        """Generate response with automatic fallback on failure."""
        if provider is None:
            provider = self.select_optimal_provider(prompt)
        
        providers_to_try = [provider] + self.get_fallback_chain(provider)
        last_error = None
        
        for current_provider in providers_to_try:
            try:
                logger.info(f"Trying provider: {current_provider.value}")
                
                # Estimate cost
                estimated_cost = self.estimate_cost(prompt, current_provider)
                
                # Generate response
                response = await self._generate_with_provider(prompt, current_provider)
                
                # Track cost
                actual_cost = self.estimate_cost(prompt + response, current_provider)
                self.cost_tracker.track_usage(current_provider, len(prompt), len(response), actual_cost)
                
                # Clear from failed providers if it was there
                self.failed_providers.discard(current_provider)
                
                return response, current_provider, actual_cost
                
            except Exception as e:
                last_error = e
                logger.error(f"Provider {current_provider.value} failed: {e}")
                self.failed_providers.add(current_provider)
                continue
        
        # All providers failed
        raise Exception(f"All providers failed. Last error: {last_error}")
    
    async def _generate_with_provider(self, prompt: str, provider: Provider) -> str:
        """Generate response using specific provider."""
        config = PROVIDER_CONFIGS[provider]
        
        if provider == Provider.GEMINI_FLASH:
            model = self.providers[provider]
            response = model.generate_content(prompt)
            return response.text
        
        elif provider in [Provider.CLAUDE_HAIKU, Provider.CLAUDE_SONNET]:
            client = self.providers[provider]
            response = client.messages.create(
                model=config.model_name,
                max_tokens=config.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        
        elif provider in [Provider.GPT_4O_MINI, Provider.GPT_4O]:
            response = openai.ChatCompletion.create(
                model=config.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.max_tokens
            )
            return response.choices[0].message.content
        
        elif provider == Provider.LOCAL:
            pipeline = self.providers[provider]
            response = pipeline(prompt, max_new_tokens=config.max_tokens)
            return response[0]['generated_text']
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def get_cost_report(self) -> Dict[str, Any]:
        """Get detailed cost report."""
        return self.cost_tracker.get_report()


class CostTracker:
    """Track LLM usage costs."""
    
    def __init__(self):
        self.usage_log = []
        self.daily_usage = {}
    
    def track_usage(self, provider: Provider, input_tokens: int, output_tokens: int, cost: float):
        """Track usage for billing."""
        entry = {
            "timestamp": time.time(),
            "provider": provider.value,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost
        }
        self.usage_log.append(entry)
        
        # Update daily usage
        today = time.strftime("%Y-%m-%d")
        if today not in self.daily_usage:
            self.daily_usage[today] = {}
        
        if provider not in self.daily_usage[today]:
            self.daily_usage[today][provider] = {
                "tokens": 0,
                "cost": 0.0,
                "requests": 0
            }
        
        self.daily_usage[today][provider]["tokens"] += entry["total_tokens"]
        self.daily_usage[today][provider]["cost"] += cost
        self.daily_usage[today][provider]["requests"] += 1
    
    def get_daily_usage(self, provider: Provider) -> int:
        """Get today's token usage for a provider."""
        today = time.strftime("%Y-%m-%d")
        if today in self.daily_usage and provider in self.daily_usage[today]:
            return self.daily_usage[today][provider]["tokens"]
        return 0
    
    def get_report(self) -> Dict[str, Any]:
        """Generate cost report."""
        total_cost = sum(entry["cost"] for entry in self.usage_log)
        
        provider_costs = {}
        for entry in self.usage_log:
            provider = entry["provider"]
            if provider not in provider_costs:
                provider_costs[provider] = {
                    "cost": 0.0,
                    "tokens": 0,
                    "requests": 0
                }
            provider_costs[provider]["cost"] += entry["cost"]
            provider_costs[provider]["tokens"] += entry["total_tokens"]
            provider_costs[provider]["requests"] += 1
        
        return {
            "total_cost": total_cost,
            "total_requests": len(self.usage_log),
            "provider_breakdown": provider_costs,
            "daily_usage": self.daily_usage,
            "average_cost_per_request": total_cost / len(self.usage_log) if self.usage_log else 0
        }


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        router = CloudLLMRouter()
        
        # Test simple task
        simple_prompt = "Categorize this text as positive or negative: 'I love this product!'"
        response, provider, cost = await router.generate_with_fallback(simple_prompt)
        print(f"Simple task - Provider: {provider.value}, Cost: ${cost:.6f}")
        print(f"Response: {response[:100]}...")
        
        # Test complex task
        complex_prompt = "Analyze the implications of quantum computing on cryptography and provide a detailed strategy for organizations to prepare for the post-quantum era."
        response, provider, cost = await router.generate_with_fallback(complex_prompt)
        print(f"\nComplex task - Provider: {provider.value}, Cost: ${cost:.6f}")
        print(f"Response: {response[:100]}...")
        
        # Get cost report
        report = router.get_cost_report()
        print(f"\nCost Report:")
        print(f"Total cost: ${report['total_cost']:.6f}")
        print(f"Total requests: {report['total_requests']}")
        print(f"Provider breakdown: {report['provider_breakdown']}")
    
    asyncio.run(main())