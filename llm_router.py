import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime

import google.generativeai as genai
import anthropic
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    SIMPLE = "simple"      # Categorization, simple extraction
    MEDIUM = "medium"      # Analysis, summaries
    COMPLEX = "complex"    # Deep analysis, threads


class LLMProvider(Enum):
    GEMINI_FLASH = "gemini-flash"
    CLAUDE_HAIKU = "claude-haiku"
    CLAUDE_SONNET = "claude-sonnet"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    LOCAL = "local"


@dataclass
class LLMConfig:
    provider: LLMProvider
    model_name: str
    cost_per_1k_tokens: float
    max_tokens: int
    temperature: float = 0.3
    timeout: int = 30


@dataclass
class CostTracking:
    provider: LLMProvider
    tokens_used: int
    cost: float
    timestamp: datetime


class CloudLLMRouter:
    """Intelligent LLM router with automatic provider selection and fallback"""
    
    # Provider configurations with costs (per 1K tokens)
    PROVIDER_CONFIGS = {
        LLMProvider.GEMINI_FLASH: LLMConfig(
            provider=LLMProvider.GEMINI_FLASH,
            model_name="gemini-1.5-flash",
            cost_per_1k_tokens=0.0,  # Free tier
            max_tokens=1000
        ),
        LLMProvider.CLAUDE_HAIKU: LLMConfig(
            provider=LLMProvider.CLAUDE_HAIKU,
            model_name="claude-3-haiku-20240307",
            cost_per_1k_tokens=0.0025,  # $0.25 per 1M tokens
            max_tokens=2000
        ),
        LLMProvider.CLAUDE_SONNET: LLMConfig(
            provider=LLMProvider.CLAUDE_SONNET,
            model_name="claude-3-sonnet-20240229",
            cost_per_1k_tokens=0.003,  # $3 per 1M tokens
            max_tokens=4000
        ),
        LLMProvider.GPT_4O_MINI: LLMConfig(
            provider=LLMProvider.GPT_4O_MINI,
            model_name="gpt-4o-mini",
            cost_per_1k_tokens=0.00015,  # $0.15 per 1M tokens
            max_tokens=2000
        ),
        LLMProvider.GPT_4O: LLMConfig(
            provider=LLMProvider.GPT_4O,
            model_name="gpt-4o",
            cost_per_1k_tokens=0.0025,  # $2.50 per 1M tokens
            max_tokens=4000
        )
    }
    
    # Task complexity to provider mapping
    COMPLEXITY_PROVIDERS = {
        TaskComplexity.SIMPLE: [
            LLMProvider.GEMINI_FLASH,
            LLMProvider.GPT_4O_MINI,
            LLMProvider.CLAUDE_HAIKU
        ],
        TaskComplexity.MEDIUM: [
            LLMProvider.CLAUDE_HAIKU,
            LLMProvider.GPT_4O_MINI,
            LLMProvider.GEMINI_FLASH
        ],
        TaskComplexity.COMPLEX: [
            LLMProvider.CLAUDE_SONNET,
            LLMProvider.GPT_4O,
            LLMProvider.CLAUDE_HAIKU
        ]
    }
    
    def __init__(self, 
                 gemini_api_key: Optional[str] = None,
                 anthropic_api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 monthly_budget: float = 10.0):
        """Initialize router with API keys and budget"""
        self.gemini_api_key = gemini_api_key
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.monthly_budget = monthly_budget
        
        self.cost_history: List[CostTracking] = []
        self.current_month_cost = 0.0
        
        # Initialize clients
        self._init_clients()
    
    def _init_clients(self):
        """Initialize API clients"""
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            
        if self.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
    
    def estimate_cost(self, text: str, provider: LLMProvider) -> float:
        """Estimate cost for processing text with given provider"""
        # Rough token estimation (4 chars = 1 token)
        estimated_tokens = len(text) / 4
        config = self.PROVIDER_CONFIGS.get(provider)
        if config:
            return (estimated_tokens / 1000) * config.cost_per_1k_tokens
        return 0.0
    
    def detect_complexity(self, text: str, task_type: str = "analyze") -> TaskComplexity:
        """Automatically detect task complexity based on content"""
        text_length = len(text)
        
        # Simple heuristics for complexity detection
        if task_type in ["categorize", "extract", "classify"]:
            return TaskComplexity.SIMPLE
        elif task_type in ["summarize", "analyze"] and text_length < 1000:
            return TaskComplexity.MEDIUM
        elif text_length > 2000 or task_type in ["deep_analyze", "thread", "research"]:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.MEDIUM
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Get list of available providers based on configured API keys"""
        available = []
        
        if self.gemini_api_key:
            available.append(LLMProvider.GEMINI_FLASH)
            
        if self.anthropic_api_key:
            available.extend([LLMProvider.CLAUDE_HAIKU, LLMProvider.CLAUDE_SONNET])
            
        if self.openai_api_key:
            available.extend([LLMProvider.GPT_4O_MINI, LLMProvider.GPT_4O])
            
        return available
    
    def select_provider(self, 
                       complexity: TaskComplexity, 
                       force_provider: Optional[LLMProvider] = None) -> LLMProvider:
        """Select best provider based on complexity and availability"""
        if force_provider and force_provider in self.get_available_providers():
            return force_provider
        
        # Get providers for complexity level
        preferred_providers = self.COMPLEXITY_PROVIDERS[complexity]
        available_providers = self.get_available_providers()
        
        # Find first available provider from preferred list
        for provider in preferred_providers:
            if provider in available_providers:
                # Check budget constraints
                if self.current_month_cost < self.monthly_budget:
                    return provider
        
        # Fallback to cheapest available
        if available_providers:
            return min(available_providers, 
                      key=lambda p: self.PROVIDER_CONFIGS[p].cost_per_1k_tokens)
        
        raise ValueError("No LLM providers available")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _call_gemini(self, prompt: str, config: LLMConfig) -> str:
        """Call Gemini API with retry logic"""
        model = genai.GenerativeModel(config.model_name)
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=config.max_tokens,
                temperature=config.temperature
            )
        )
        return response.text
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _call_claude(self, prompt: str, config: LLMConfig) -> str:
        """Call Claude API with retry logic"""
        response = await self.anthropic_client.messages.create(
            model=config.model_name,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _call_openai(self, prompt: str, config: LLMConfig) -> str:
        """Call OpenAI API with retry logic"""
        response = await openai.ChatCompletion.acreate(
            model=config.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        return response.choices[0].message.content
    
    async def process_with_fallback(self, 
                                  prompt: str, 
                                  complexity: TaskComplexity,
                                  force_provider: Optional[LLMProvider] = None) -> Tuple[str, LLMProvider, float]:
        """Process prompt with automatic fallback on failure"""
        providers = self.COMPLEXITY_PROVIDERS[complexity]
        available = self.get_available_providers()
        
        # Filter to available providers
        fallback_chain = [p for p in providers if p in available]
        
        if force_provider and force_provider in available:
            fallback_chain = [force_provider] + [p for p in fallback_chain if p != force_provider]
        
        last_error = None
        
        for provider in fallback_chain:
            try:
                config = self.PROVIDER_CONFIGS[provider]
                logger.info(f"Trying provider: {provider.value}")
                
                # Estimate cost
                estimated_cost = self.estimate_cost(prompt, provider)
                
                # Check budget
                if self.current_month_cost + estimated_cost > self.monthly_budget:
                    logger.warning(f"Budget exceeded, skipping {provider.value}")
                    continue
                
                # Call appropriate API
                start_time = time.time()
                
                if provider == LLMProvider.GEMINI_FLASH:
                    result = await self._call_gemini(prompt, config)
                elif provider in [LLMProvider.CLAUDE_HAIKU, LLMProvider.CLAUDE_SONNET]:
                    result = await self._call_claude(prompt, config)
                elif provider in [LLMProvider.GPT_4O_MINI, LLMProvider.GPT_4O]:
                    result = await self._call_openai(prompt, config)
                else:
                    continue
                
                # Track cost
                actual_tokens = len(result) / 4  # Rough estimate
                actual_cost = (actual_tokens / 1000) * config.cost_per_1k_tokens
                
                self.track_cost(provider, int(actual_tokens), actual_cost)
                
                logger.info(f"Success with {provider.value} in {time.time() - start_time:.2f}s")
                return result, provider, actual_cost
                
            except Exception as e:
                last_error = e
                logger.error(f"Error with {provider.value}: {str(e)}")
                continue
        
        # All providers failed
        raise Exception(f"All providers failed. Last error: {last_error}")
    
    def track_cost(self, provider: LLMProvider, tokens: int, cost: float):
        """Track usage and costs"""
        tracking = CostTracking(
            provider=provider,
            tokens_used=tokens,
            cost=cost,
            timestamp=datetime.now()
        )
        self.cost_history.append(tracking)
        self.current_month_cost += cost
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary for current month"""
        provider_costs = {}
        for tracking in self.cost_history:
            if tracking.provider not in provider_costs:
                provider_costs[tracking.provider.value] = {
                    "total_cost": 0,
                    "total_tokens": 0,
                    "call_count": 0
                }
            
            provider_costs[tracking.provider.value]["total_cost"] += tracking.cost
            provider_costs[tracking.provider.value]["total_tokens"] += tracking.tokens_used
            provider_costs[tracking.provider.value]["call_count"] += 1
        
        return {
            "total_cost": self.current_month_cost,
            "budget_remaining": self.monthly_budget - self.current_month_cost,
            "budget_used_percent": (self.current_month_cost / self.monthly_budget) * 100,
            "provider_breakdown": provider_costs
        }
    
    async def process(self, 
                     text: str, 
                     task_type: str = "analyze",
                     force_provider: Optional[LLMProvider] = None,
                     output_format: str = "json") -> Dict[str, Any]:
        """Main processing method with intelligent routing"""
        # Detect complexity
        complexity = self.detect_complexity(text, task_type)
        
        # Create prompt based on task type
        prompt = self._create_prompt(text, task_type, output_format)
        
        # Process with fallback
        result, provider, cost = await self.process_with_fallback(
            prompt, complexity, force_provider
        )
        
        # Parse result if JSON expected
        if output_format == "json":
            try:
                parsed_result = json.loads(result)
            except json.JSONDecodeError:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    parsed_result = json.loads(json_match.group())
                else:
                    parsed_result = {"raw_response": result}
        else:
            parsed_result = {"response": result}
        
        return {
            "result": parsed_result,
            "provider": provider.value,
            "complexity": complexity.value,
            "cost": cost,
            "tokens": int(len(result) / 4)
        }
    
    def _create_prompt(self, text: str, task_type: str, output_format: str) -> str:
        """Create prompt based on task type"""
        prompts = {
            "categorize": f"""Categorize the following content into one of these categories: 
Technology, Business, Health, Education, Entertainment, Politics, Sports, Other.

Content: {text}

Return JSON: {{"category": "chosen_category", "confidence": 0.0-1.0}}""",
            
            "analyze": f"""Analyze the following content and extract key information:

Content: {text}

Return JSON with:
- title: Brief descriptive title
- category: Main category
- tags: List of relevant tags
- sentiment: positive/negative/neutral
- key_points: List of main points
- entities: Named entities found""",
            
            "summarize": f"""Summarize the following content concisely:

Content: {text}

Return JSON: {{"summary": "your summary", "key_points": ["point1", "point2"]}}""",
            
            "thread": f"""Analyze this Twitter thread and extract the main narrative:

Content: {text}

Return JSON with:
- main_topic: Core topic of the thread
- thread_summary: Cohesive summary
- key_insights: List of main insights
- call_to_action: Any CTA mentioned"""
        }
        
        return prompts.get(task_type, prompts["analyze"])


# Example usage
async def main():
    router = CloudLLMRouter(
        gemini_api_key="your-gemini-key",
        anthropic_api_key="your-anthropic-key", 
        openai_api_key="your-openai-key",
        monthly_budget=10.0
    )
    
    # Process a tweet
    result = await router.process(
        text="Just launched our new AI product! It uses advanced ML to categorize content 10x faster.",
        task_type="analyze"
    )
    
    print(json.dumps(result, indent=2))
    print("\nCost Summary:")
    print(json.dumps(router.get_cost_summary(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())