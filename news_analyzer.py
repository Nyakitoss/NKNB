import asyncio
from typing import List, Dict
from datetime import datetime
from openrouter_client import create_ai_client
import os
from dotenv import load_dotenv

load_dotenv()

class NewsAnalyzer:
    def __init__(self):
        # Используем OpenRouter для анализа
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if api_key:
            self.ai_client = create_ai_client("openrouter", api_key)
        else:
            self.ai_client = None
            print("**LOG: No OpenRouter API key found, analysis will be limited**")
    
    async def analyze_news(self, news_items: List[Dict], topics: List[str]) -> str:
        """Анализирует и сокращает новости через ИИ"""
        if not self.ai_client:
            return self._fallback_analysis(news_items, topics)
        
        try:
            print(f"**LOG: Analyzing {len(news_items)} news items with AI**")
            
            # Группируем новости по темам
            grouped_news = self._group_news_by_topics(news_items, topics)
            
            # Создаем промпт для анализа
            prompt = self._build_analysis_prompt(grouped_news, topics)
            
            # Отправляем в ИИ для анализа
            analysis = await self.ai_client.generate_news([f"анализ новостей: {', '.join(topics)}"])
            
            print(f"**LOG: AI analysis completed successfully**")
            return analysis
            
        except Exception as e:
            print(f"**LOG: AI analysis failed: {str(e)}**")
            return self._fallback_analysis(news_items, topics)
    
    def _group_news_by_topics(self, news_items: List[Dict], topics: List[str]) -> Dict[str, List[Dict]]:
        """Группирует новости по темам"""
        grouped = {topic: [] for topic in topics}
        topics_lower = [topic.lower() for topic in topics]
        
        for news_item in news_items:
            title = news_item.get("title", "").lower()
            desc = news_item.get("description", "").lower()
            
            for i, topic in enumerate(topics_lower):
                if topic in title or topic in desc:
                    grouped[topics[i]].append(news_item)
                    break
        
        return grouped
    
    def _build_analysis_prompt(self, grouped_news: Dict[str, List[Dict]], topics: List[str]) -> str:
        """Создает промпт для анализа новостей"""
        current_date = datetime.now().strftime("%d.%m.%Y")
        current_time = datetime.now().strftime("%H:%M:%S")
        
        prompt = f"""
Проанализируй и создай краткий новостной дайджест из следующих материалов за последние 24 часа:

ИСТОЧНИКИ: RSS ленты российских новостных сайтов
ДАТА: {current_date}
ВРЕМЯ: {current_time}

ГРУППИРОВАННЫЕ НОВОСТИ ПО ТЕМАМ:
"""
        
        for topic in topics:
            news_list = grouped_news.get(topic, [])
            prompt += f"\n📌 {topic.upper()}:\n"
            
            for i, news_item in enumerate(news_list[:5]):  # Максимум 5 новостей на тему
                title = news_item.get("title", "")
                desc = news_item.get("description", "")
                source = news_item.get("source", "RSS Feed")
                link = news_item.get("link", "")
                
                prompt += f"\n{i+1}. {title}\n"
                prompt += f"   Кратко: {desc[:200]}...\n"
                prompt += f"   Источник: {source}\n"
                if link:
                    prompt += f"   Ссылка: {link}\n"
        
        prompt += f"""
ТРЕБОВАНИЯ К АНАЛИЗУ:
1. СОКРАТИ каждую новость до 1-2 предложений
2. ВЫДЕЛИ главное и самое важное
3. ДОБАВЬ анализ влияния, если применимо
4. ИСПОЛЬЗУЙ актуальные данные из источников
5. СОЗДАЙ удобный формат для Telegram
6. ДОБАВЬ релевантные эмодзи
7. РАЗДЕЛИ темы пустыми строками
8. БУДЬ объективным и фактичным
9. ВКЛЮЧИ ссылки на источники после каждой новости

ФОРМАТ ВЫВОДА:
📰 **Ежедневный дайджест | {current_date}**

📌 **ТЕМА 1:**
🔹 **Главная новость** - краткое описание (1-2 предложения)
   📊 **Анализ:** возможные последствия
   **Источник:** [Оригинальная ссылка]

🔹 **Вторая новость** - краткое описание  
   📊 **Анализ:** возможные последствия
   **Источник:** [Оригинальная ссылка]

📌 **ТЕМА 2:**
🔹 **Новость** - краткое описание
   📊 **Анализ:** возможные последствия
   **Источник:** [Оригинальная ссылка]

Продолжайте с другими темами...

---
*Источник: агрегация RSS-лент российских СМИ*
*Анализ выполнен ИИ на основе доступных данных*
"""
        
        return prompt
    
    def _fallback_analysis(self, news_items: List[Dict], topics: List[str]) -> str:
        """Fallback analysis without AI with source links"""
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        # Group and select best news
        grouped_news = self._group_news_by_topics(news_items, topics)
        
        result = f"**Daily Digest | {current_date}**\n\n"
        
        has_news = False
        for topic in topics:
            news_list = grouped_news.get(topic, [])
            if news_list:
                has_news = True
                result += f"**{topic.upper()}:**\n"
                
                # Take 3 best news items per topic
                for i, news_item in enumerate(news_list[:3]):
                    title = news_item.get("title", "")
                    desc = news_item.get("description", "")
                    source = news_item.get("source", "RSS Feed")
                    link = news_item.get("link", "")
                    
                    # Shorten description
                    if len(desc) > 150:
                        desc = desc[:147] + "..."
                    
                    result += f"- **{title}**\n"
                    result += f"  {desc}\n"
                    
                    # Add source with link if available
                    if link:
                        result += f"  **Source:** [{source}]({link})\n"
                    else:
                        result += f"  **Source:** {source}\n"
                    
                    result += "\n"
            else:
                # If no news for the topic
                result += f"**{topic.upper()}:**\n"
                result += f"  - No news found for this topic in the last 24 hours.\n"
                result += f"  - News may appear tomorrow!\n\n"
        
        if not has_news:
            result += "**No news found for any topic in the last 24 hours.**\n\n"
            result += "**Try changing topics or repeat later.**\n"
        
        result += "---\n"
        result += "*Source: RSS aggregation of Russian and international media*\n"
        result += "*Analysis performed without AI (fallback mode)*\n"
        
        return result

# Глобальный экземпляр анализатора
news_analyzer = NewsAnalyzer()
