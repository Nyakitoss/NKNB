import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Optional, Dict
from abc import ABC, abstractmethod
from logger import logger

class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_news(self, topics: List[str]) -> str:
        pass

class OpenRouterProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise Exception("OpenRouter API key is required")
        
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        
        # Best free models with internet access, prioritized by quality and recency
        self.models = [
            # Latest and most capable models (2026)
            "liquidai/lfm2.5-1.2b-thinking",      # Latest with thinking capabilities
            "liquidai/lfm2.5-1.2b-instruct",      # Latest instruct model
            "nvidia/nemotron-3-nano-30b-a3b",     # Large NVIDIA model
            "arcee-ai/trinity-mini",              # Specialized for current events
            "nvidia/nemotron-nano-12b-2-vl",      # Vision-language model
            "qwen/qwen3-next-80b-a3b-instruct",  # Large Qwen model
            "nvidia/nemotron-nano-9b-v2",         # Updated NVIDIA model
            
            # High-quality models from 2025
            "openai/gpt-oss-120b",               # Large OpenAI model
            "openai/gpt-oss-20b",                # Medium OpenAI model
            "z-ai/glm-4.5-air",                  # GLM with web access
            "qwen/qwen3-coder-480b-a35b",        # Large Qwen coder
            "venice/uncensored",                 # Uncensored model
            
            # Google models (2025)
            "google/gemma-3n-2b",               # Latest Gemma nano
            "google/gemma-3n-4b",               # Latest Gemma nano
            "google/gemma-3-4b",                # Latest Gemma
            "google/gemma-3-12b",               # Medium Gemma
            "google/gemma-3-27b",               # Large Gemma
            
            # Meta models (2024)
            "meta-llama/llama-3.3-70b-instruct", # Latest Llama
            "meta-llama/llama-3.2-3b-instruct",  # Small Llama
            
            # Other capable models
            "nous-hermes-3-405b-instruct"        # Large Hermes model
        ]
        
        self.current_model_index = 0
        print(f"**LOG: OpenRouter provider initialized with {len(self.models)} free models**")
        
    def _get_current_model(self) -> str:
        return self.models[self.current_model_index]
    
    async def generate_news(self, topics: List[str]) -> str:
        """Generate news with detailed logging and model fallback"""
        await logger.log_generation_start(topics, self.models)
        
        prompt = self._build_prompt(topics)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Nyakitoss/NKNB",  # Help OpenRouter track usage
            "X-Title": "News Bot"  # App name for OpenRouter
        }
        
        last_error = None
        
        # Try each model in order
        for model_index, model in enumerate(self.models):
            await logger.log_model_attempt(model, model_index + 1, len(self.models))
            
            try:
                data = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional news aggregator with access to real-time internet. Generate accurate, current news summaries based on the latest events. Focus on recent developments and provide factual information with proper context. Use web search to get the most recent information."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 8000
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=120)  # 2 minute timeout
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            news_content = result["choices"][0]["message"]["content"]
                            
                            await logger.log_generation_success(model, len(news_content))
                            return news_content
                        else:
                            error_text = await response.text()
                            last_error = f"Model {model} failed: HTTP {response.status} - {error_text}"
                            await logger.log_model_error(model, last_error)
                            
                            # Handle specific error codes
                            if response.status == 429:
                                error_msg = f"Rate limit exceeded for {model}, trying next model..."
                                print(f"**LOG: RATE LIMIT - {error_msg}**")
                                await asyncio.sleep(3)  # Wait before next attempt
                                continue
                            elif response.status == 401:
                                error_msg = f"Invalid API key for {model}"
                                print(f"**LOG: AUTH ERROR - {error_msg}**")
                                raise Exception(f"OpenRouter API authentication failed: {error_text}")
                            elif response.status == 402:
                                error_msg = f"Model {model} requires payment, skipping..."
                                print(f"**LOG: PAYMENT REQUIRED - {error_msg}**")
                                continue
                            elif response.status == 403:
                                error_msg = f"Access forbidden for {model}"
                                print(f"**LOG: ACCESS ERROR - {error_msg}**")
                                continue
                            elif response.status == 503:
                                error_msg = f"Service unavailable for {model}"
                                print(f"**LOG: SERVICE ERROR - {error_msg}**")
                                await asyncio.sleep(5)  # Wait before retry
                                continue
                            else:
                                print(f"**LOG: UNEXPECTED ERROR - Continuing to next model**")
                                continue
                                
            except asyncio.TimeoutError:
                last_error = f"Model {model} timeout (120s)"
                await logger.log_model_error(model, last_error)
                continue
            except Exception as e:
                error_str = str(e).lower()
                last_error = f"Model {model} error: {str(e)}"
                await logger.log_model_error(model, last_error)
                
                # Handle specific errors
                if "quota" in error_str or "limit" in error_str:
                    error_msg = f"Quota exceeded for {model}, trying next model..."
                    print(f"**LOG: QUOTA ERROR - {error_msg}**")
                    continue
                elif "api key" in error_str:
                    error_msg = f"Invalid API key for {model}"
                    print(f"**LOG: API KEY ERROR - {error_msg}**")
                    raise Exception(f"OpenRouter API key error: {str(e)}")
                else:
                    print(f"**LOG: GENERAL ERROR - Continuing to next model**")
                    continue
        
        # All models failed
        await logger.log_generation_failure(last_error)
        error_msg = f"All OpenRouter models failed. Last error: {last_error}"
        raise Exception(error_msg)
    
    def _build_prompt(self, topics: List[str]) -> str:
        current_date = datetime.now().strftime("%d.%m.%Y")
        current_time = datetime.now().strftime("%H:%M:%S")
        
        return f"""
Create a current news digest for topics: {", ".join(topics)}.

CRITICAL REQUIREMENTS:
- Current date: {current_date}
- Current time: {current_time}
- USE ONLY FRESH NEWS from the last 24 hours
- You have REAL-TIME INTERNET ACCESS - use web search to get latest information!
- DO NOT use outdated data or training knowledge
- Write in Russian language
- Create Telegram-friendly format
- Add relevant emojis to each news item
- Include impact analysis when applicable
- Clearly separate different topics
- Be objective and factual
- Search for breaking news and recent developments

FORMAT:
**Daily News Digest | {current_date} | {current_time}**

**{topics[0]}:**
- News item 1 - brief description of the event
  **Impact Analysis:** potential consequences

- News item 2 - brief description of the event  
  **Impact Analysis:** potential consequences

**{topics[1] if len(topics) > 1 else 'Other Topics'}:**
- News item - brief description of the event
  **Impact Analysis:** potential consequences

Continue with other topics...

IMPORTANT: This news digest was created by AI with real-time internet access. ALWAYS verify information from multiple reliable sources before publication.
"""

class UniversalAIClient:
    def __init__(self, provider: str, api_key: str):
        self.provider_name = provider.lower()
        self.api_key = api_key
        self.provider = self._create_provider()
        
    def _create_provider(self) -> BaseAIProvider:
        providers = {
            "openrouter": OpenRouterProvider,
        }
        
        if self.provider_name not in providers:
            raise Exception(f"Unsupported provider: {self.provider_name}")
            
        return providers[self.provider_name](self.api_key)
    
    async def generate_news(self, topics: List[str]) -> str:
        try:
            print(f"**LOG: Generating news using {self.provider_name} provider**")
            return await self.provider.generate_news(topics)
        except Exception as e:
            print(f"**LOG: {self.provider_name.title()} API error: {str(e)}**")
            raise Exception(f"{self.provider_name.title()} API error: {str(e)}")

# Factory function for easy integration
def create_ai_client(provider: str, api_key: str) -> UniversalAIClient:
    return UniversalAIClient(provider, api_key)
