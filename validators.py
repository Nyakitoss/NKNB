import re
from typing import Optional, List
from telethon import errors

class ValidationError(Exception):
    pass

class InputValidator:
    @staticmethod
    def validate_channel_username(username: str) -> str:
        """Валидация username канала"""
        if not username:
            raise ValidationError("❌ Username не может быть пустым")
        
        username = username.strip()
        
        if not username.startswith("@"):
            raise ValidationError("❌ Username должен начинаться с @")
        
        # Удаляем @ для проверки
        clean_username = username[1:]
        
        if len(clean_username) < 5:
            raise ValidationError("❌ Username слишком короткий (минимум 5 символов)")
        
        if len(clean_username) > 32:
            raise ValidationError("❌ Username слишком длинный (максимум 32 символа)")
        
        if not re.match(r'^[a-zA-Z0-9_]+$', clean_username):
            raise ValidationError("❌ Username может содержать только буквы, цифры и _")
        
        return username
    
    @staticmethod
    def validate_topics(topics: List[str], available_topics: List[str]) -> List[str]:
        """Валидация выбранных тем"""
        if not topics:
            raise ValidationError("❌ Выберите хотя бы одну тему")
        
        invalid_topics = [topic for topic in topics if topic not in available_topics]
        if invalid_topics:
            raise ValidationError(f"❌ Недопустимые темы: {', '.join(invalid_topics)}")
        
        return topics
    
    @staticmethod
    def validate_time_format(time_str: str) -> str:
        """Валидация формата времени"""
        if not time_str:
            return "09:00"  # время по умолчанию
        
        try:
            hours, minutes = map(int, time_str.split(":"))
            
            if not (0 <= hours <= 23):
                raise ValidationError("❌ Часы должны быть от 0 до 23")
            
            if not (0 <= minutes <= 59):
                raise ValidationError("❌ Минуты должны быть от 0 до 59")
            
            return f"{hours:02d}:{minutes:02d}"
        
        except ValueError:
            raise ValidationError("❌ Неверный формат времени. Используйте ЧЧ:ММ")

class ErrorHandler:
    @staticmethod
    def handle_telegram_error(error: Exception) -> str:
        """Обработка ошибок Telegram API"""
        if isinstance(error, errors.ChannelPrivateError):
            return "❌ Канал является приватным. Используйте публичный канал."
        
        elif isinstance(error, errors.ChatIdInvalidError):
            return "❌ Неверный ID канала. Проверьте username."
        
        elif isinstance(error, errors.UserBannedInChannelError):
            return "❌ Бот заблокирован в канале."
        
        elif isinstance(error, errors.ChatAdminRequiredError):
            return "❌ Бот должен быть администратором канала."
        
        elif isinstance(error, errors.FloodWaitError):
            wait_time = error.seconds
            return f"⏠️ Слишком много запросов. Подождите {wait_time} секунд."
        
        elif isinstance(error, errors.MessageTooLongError):
            return "❌ Слишком длинное сообщение."
        
        else:
            return f"❌ Ошибка Telegram: {str(error)}"
    
    @staticmethod
    def handle_gemini_error(error: Exception) -> str:
        """Обработка ошибок Gemini API"""
        error_str = str(error).lower()
        
        if "quota" in error_str or "limit" in error_str:
            return "❌ Превышен лимит запросов к Gemini API. Попробуйте позже."
        
        elif "api key" in error_str:
            return "❌ Неверный API ключ Gemini."
        
        elif "content" in error_str and "policy" in error_str:
            return "❌ Контент нарушает политику Gemini API."
        
        elif "503" in error_str or "unavailable" in error_str or "high demand" in error_str:
            return "⏳ Gemini API перегружен. Повторная попытка через несколько секунд..."
        
        elif "暂时不可用" in error_str or "temporarily unavailable" in error_str:
            return "⏳ Gemini API временно недоступен. Попробуйте через минуту."
        
        else:
            return f"❌ Ошибка Gemini API: {str(error)}"
    
    @staticmethod
    def handle_storage_error(error: Exception) -> str:
        """Обработка ошибок хранения данных"""
        error_str = str(error).lower()
        
        if "connection" in error_str:
            return "❌ Проблемы с подключением к хранилищу данных."
        
        elif "redis" in error_str:
            return "❌ Ошибка Redis. Пробуем локальное хранилище..."
        
        else:
            return f"❌ Ошибка сохранения данных: {str(error)}"
