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

class GrokProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise Exception("xAI API key is required for Grok provider")
        
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"
        
        # Best models for news generation (prioritized by quality and reasoning)
        self.models = [
            "grok-4.20-0309-reasoning",      # Best reasoning model
            "grok-4-fast-reasoning",         # Fast with reasoning
            "grok-4-1-fast-reasoning",       # Fast reasoning v1
            "grok-4-0709",                   # Stable model
            "grok-3-mini",                   # Small but capable
            "grok-3"                         # Base model
        ]
        
        self.current_model_index = 0
        print(f"**LOG: Grok provider initialized with {len(self.models)} models**")
        
    def _get_current_model(self) -> str:
        return self.models[self.current_model_index]
    
    async def generate_news(self, topics: List[str]) -> str:
        """Generate news with detailed logging and model fallback"""
        await logger.log_generation_start(topics, self.models)
        
        prompt = self._build_prompt(topics)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
                            "content": "You are a professional news aggregator with access to real-time internet. Generate accurate, current news summaries based on the latest events. Focus on recent developments and provide factual information with proper context."
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
                                raise Exception(f"xAI API authentication failed: {error_text}")
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
                    raise Exception(f"xAI API key error: {str(e)}")
                else:
                    print(f"**LOG: GENERAL ERROR - Continuing to next model**")
                    continue
        
        # All models failed
        await logger.log_generation_failure(last_error)
        error_msg = f"All Grok models failed. Last error: {last_error}"
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
- You have REAL-TIME INTERNET ACCESS - use it!
- DO NOT use outdated data (before 2024)
- Write in Russian language
- Create Telegram-friendly format
- Add relevant emojis to each news item
- Include impact analysis when applicable
- Clearly separate different topics
- Be objective and factual

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
            "grok": GrokProvider,
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
