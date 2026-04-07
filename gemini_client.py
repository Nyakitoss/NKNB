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
        self.models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        
    async def generate_news(self, topics: List[str]) -> str:
        """Генерация новостей с retry механизмом и fallback моделей"""
        
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
                        return response.text
                    else:
                        raise Exception("Empty response from Gemini")
                        
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Если модель не найдена, пробуем следующую
                    if 'not found' in error_str or '404' in error_str:
                        print(f"Model {model} not found, trying next...")
                        continue
                    
                    # Если это ошибка перегрузки, пробуем еще раз с той же моделью
                    elif any(keyword in error_str for keyword in ['503', 'unavailable', 'overloaded', 'high demand']):
                        if attempt < self.max_retries - 1:
                            delay = self._calculate_delay(attempt)
                            print(f"Gemini API overloaded (attempt {attempt + 1}/{self.max_retries}). Retrying in {delay}s...")
                            await asyncio.sleep(delay)
                            break  # перезапускаем retry с первой модели
                        else:
                            raise Exception("Gemini API временно недоступен. Попробуйте позже.")
                    
                    # Другие ошибки не retry'им
                    elif 'quota' in error_str or 'limit' in error_str:
                        raise Exception("Превышен лимит API. Проверьте использование Gemini API.")
                    
                    elif 'api key' in error_str:
                        raise Exception("Неверный API ключ Gemini.")
                    
                    else:
                        print(f"Error with {model}: {e}")
                        if model == self.models[-1]:  # последняя модель
                            if attempt < self.max_retries - 1:
                                delay = self._calculate_delay(attempt)
                                print(f"Retrying in {delay}s...")
                                await asyncio.sleep(delay)
                                break
                            else:
                                raise e
                        continue
        
        raise Exception("Не удалось сгенерировать новости после всех попыток.")
    
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
