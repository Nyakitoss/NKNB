import asyncio
import time
from typing import List, Optional
from google import genai
from google.genai import types
from cache_manager import cache_manager

class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.max_retries = 3
        self.base_delay = 2  # seconds
        self.models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        
    async def generate_news(self, topics: List[str]) -> str:
        """Generate news with caching and API limits tracking"""
        
        # Check cache first
        cached_news = cache_manager.get_cached_news(topics)
        if cached_news:
            return cached_news
        
        # Check API limits
        limits = cache_manager.check_api_limits()
        if not limits["can_request"]:
            time_until_reset = cache_manager.get_time_until_reset()
            raise Exception(
                f"API limit exceeded. Used {limits['requests_today']}/{limits['daily_limit']} requests. "
                f"Reset in {time_until_reset}. Try using cached news or wait for reset."
            )
        
        # Record API request
        if not cache_manager.record_api_request():
            raise Exception("Failed to record API request - possible limit issue")
        
        # Generate new content
        prompt = self._build_prompt(topics)
        
        for attempt in range(self.max_retries):
            for model in self.models:
                try:
                    print(f"Trying model: {model} (attempt {attempt + 1}/{self.max_retries})")
                    
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.7,
                            max_output_tokens=8000,
                        )
                    )
                    
                    if response.text:
                        print(f"Successfully generated news using {model}")
                        
                        # Cache the result
                        cache_manager.cache_news(topics, response.text)
                        
                        return response.text
                    else:
                        raise Exception("Empty response from Gemini")
                        
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # If model not found, try next
                    if 'not found' in error_str or '404' in error_str:
                        print(f"Model {model} not found, trying next...")
                        continue
                    
                    # If API overloaded, retry
                    elif any(keyword in error_str for keyword in ['503', 'unavailable', 'overloaded', 'high demand']):
                        if attempt < self.max_retries - 1:
                            delay = self._calculate_delay(attempt)
                            print(f"Gemini API overloaded (attempt {attempt + 1}/{self.max_retries}). Retrying in {delay}s...")
                            await asyncio.sleep(delay)
                            break
                        else:
                            raise Exception("Gemini API temporarily unavailable. Try again later.")
                    
                    # Other errors
                    elif 'quota' in error_str or 'limit' in error_str:
                        limits = cache_manager.check_api_limits()
                        time_until_reset = cache_manager.get_time_until_reset()
                        raise Exception(
                            f"API quota exceeded. Used {limits['requests_today']}/{limits['daily_limit']} requests. "
                            f"Reset in {time_until_reset}."
                        )
                    
                    elif 'api key' in error_str:
                        raise Exception("Invalid Gemini API key.")
                    
                    else:
                        print(f"Error with {model}: {e}")
                        if model == self.models[-1]:
                            if attempt < self.max_retries - 1:
                                delay = self._calculate_delay(attempt)
                                print(f"Retrying in {delay}s...")
                                await asyncio.sleep(delay)
                                break
                            else:
                                raise e
                        continue
        
        raise Exception("Failed to generate news after all attempts.")
    
    def _build_prompt(self, topics: List[str]) -> str:
        """Создание промпта для генерации новостей"""
        
        return f"""
Собери актуальные новости за последние 24 часа.

Темы:
{", ".join(topics)}

Требования:

— новости должны быть свежими  
— если новости на английском — переведи  
— напиши всё на русском  
— формат удобный для Telegram  
— разделяй новости и темы от друг друга, то есть после новостей будет пустая строка, так же как и после темы
— добавляй смайлик в начало новости, который будет соответствовать этой новости
— если всё что говорится в новости может сказаться на мире, то после новости анализируй и пиши блок текста о том как это может сказаться на мире и жизни
— добавь в самом конце дайджеста такой текст "Данные новости были проанализированы и записаны ИИ Gemini, создатель не ручается за актуальность и правдивость данной информации, настоятельно рекомендую проверять информацию из надежных источников."

Формат:

📰 Утренний дайджест

📌 Тема:

    — новость  
    
        — как это может сказаться на мире и жизни (если последствия будут ощутимыми)

    — новость  
    
        — как это может сказаться на мире и жизни (если последствия будут ощутимыми)
____________________________________________________________________________________        
📌 Тема:

    — новость  
    
        — как это может сказаться на мире и жизни (если последствия будут ощутимыми)

    — новость  
    
        — как это может сказаться на мире и жизни (если последствия будут ощутимыми)
____________________________________________________________________________________
и так далее
"""
    
    def _calculate_delay(self, attempt: int) -> int:
        """Расчет задержки с экспоненциальным бэккофом"""
        return self.base_delay * (2 ** attempt)  # 2s, 4s, 8s

# Глобальный экземпляр для совместимости
def create_gemini_client(api_key: str) -> GeminiClient:
    return GeminiClient(api_key)
