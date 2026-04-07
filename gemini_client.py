import asyncio
import time
from typing import List, Optional
from google import genai
from google.genai import types

class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.max_retries = 3
        self.base_delay = 2  # seconds
        
    async def generate_news(self, topics: List[str]) -> str:
        """Генерация новостей с retry механизмом"""
        
        prompt = self._build_prompt(topics)
        
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model="gemini-2.0-flash-exp",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=8000,
                    )
                )
                
                if response.text:
                    return response.text
                else:
                    raise Exception("Empty response from Gemini")
                    
            except Exception as e:
                error_str = str(e).lower()
                
                # Если это ошибка перегрузки, пробуем еще раз
                if any(keyword in error_str for keyword in ['503', 'unavailable', 'overloaded', 'high demand']):
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_delay(attempt)
                        print(f"Gemini API overloaded (attempt {attempt + 1}/{self.max_retries}). Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Последняя попытка не удалась
                        raise Exception("Gemini API暂时不可用，请稍后再试。Gemini API temporarily unavailable, please try again later.")
                
                # Другие ошибки не retry'им
                elif 'quota' in error_str or 'limit' in error_str:
                    raise Exception("API quota exceeded. Please check your Gemini API usage.")
                
                elif 'api key' in error_str:
                    raise Exception("Invalid Gemini API key.")
                
                else:
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_delay(attempt)
                        print(f"Gemini API error (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise e
        
        raise Exception("Failed to generate news after all retries.")
    
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
