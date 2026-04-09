import asyncio
import aiohttp
import json
from typing import List, Optional, Dict
from abc import ABC, abstractmethod

class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_news(self, topics: List[str]) -> str:
        pass

class GroqProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise Exception("Groq API key is required")
        
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        # Best models for news generation (updated 2024)
        self.models = [
            "llama-3.1-70b-versatile",  # Best quality, latest model
            "llama3-70b-8192",          # Stable and reliable
            "mixtral-8x7b-32768"        # Good for long content
        ]
        self.current_model_index = 0
        
        print(f"🔑 Groq provider initialized with {len(self.models)} models")
        
    def _get_current_model(self) -> str:
        return self.models[self.current_model_index]
    
    async def generate_news(self, topics: List[str]) -> str:
        prompt = self._build_prompt(topics)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Try different models if one fails
        for model_index in range(len(self.models)):
            model = self.models[model_index]
            
            data = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional news aggregator. Generate accurate, current news summaries based on real events. Focus on recent developments and provide factual information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 8000
            }
            
            try:
                print(f"🚀 Trying Groq model: {model}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=90)  # Increased timeout
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            print(f"✅ Successfully generated news using {model}")
                            return result["choices"][0]["message"]["content"]
                        else:
                            error_text = await response.text()
                            print(f"❌ Model {model} failed: {response.status} - {error_text}")
                            
                            # Handle specific error codes
                            if response.status == 429:
                                print("⏳ Rate limit hit, waiting before next model...")
                                await asyncio.sleep(2)
                            
                            if model_index < len(self.models) - 1:
                                continue
                            else:
                                raise Exception(f"All Groq models failed. Last error: {response.status} - {error_text}")
                                
            except asyncio.TimeoutError:
                print(f"⏰ Model {model} timeout (90s)")
                if model_index < len(self.models) - 1:
                    continue
                else:
                    raise Exception("All Groq models timed out")
            except Exception as e:
                error_str = str(e).lower()
                print(f"💥 Model {model} error: {str(e)}")
                
                # Handle specific errors
                if "quota" in error_str or "limit" in error_str:
                    raise Exception(f"Groq quota exceeded: {str(e)}")
                elif "api key" in error_str:
                    raise Exception(f"Invalid Groq API key: {str(e)}")
                
                if model_index < len(self.models) - 1:
                    continue
                else:
                    raise Exception(f"All Groq models failed. Last error: {str(e)}")
    
    def _build_prompt(self, topics: List[str]) -> str:
        return f"""
Создай актуальный новостной дайджест по темам: {", ".join(topics)}.

ТРЕБОВАНИЯ:
• Используй актуальную информацию о последних событиях (24 часа)
• Пиши на русском языке
• Создай удобный формат для Telegram
• Добавляй релевантные эмодзи к каждой новости
• Включай анализ влияния, когда это применимо
• Четко разделяй разные темы
• Будь объективным и фактичным

ФОРМАТ:
📰 Ежедневный новостной дайджест

📌 {topics[0]}:
🔹 Новость 1 - краткое описание события
   📊 Анализ влияния: возможные последствия

🔹 Новость 2 - краткое описание события  
   📊 Анализ влияния: возможные последствия

📌 {topics[1] if len(topics) > 1 else 'Другие темы'}:
🔹 Новость - краткое описание события
   📊 Анализ влияния: возможные последствия

Продолжай с другими темами...

ВАЖНО: Этот новостной дайджест создан ИИ. Рекомендуется проверять информацию из надежных источников.
"""

class UniversalAIClient:
    def __init__(self, provider: str, api_key: str):
        self.provider_name = provider.lower()
        self.api_key = api_key
        self.provider = self._create_provider()
        
    def _create_provider(self) -> BaseAIProvider:
        providers = {
            "groq": GroqProvider,
        }
        
        if self.provider_name not in providers:
            raise Exception(f"Unsupported provider: {self.provider_name}")
            
        return providers[self.provider_name](self.api_key)
    
    async def generate_news(self, topics: List[str]) -> str:
        try:
            print(f"Generating news using {self.provider_name} provider")
            return await self.provider.generate_news(topics)
        except Exception as e:
            raise Exception(f"{self.provider_name.title()} API error: {str(e)}")

# Factory function for easy integration
def create_ai_client(provider: str, api_key: str) -> UniversalAIClient:
    return UniversalAIClient(provider, api_key)
