import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from storage import storage

class CacheManager:
    def __init__(self):
        self.cache_prefix = "news_cache:"
        self.limits_prefix = "api_limits:"
        self.cache_duration_hours = 2  # news cached for 2 hours
        self.requests_today = {}
        self.last_reset_date = {}
        
    def _get_cache_key(self, topics: List[str]) -> str:
        """Generate cache key based on topics"""
        topics_sorted = sorted(topics)
        topics_str = "_".join(topics_sorted)
        return f"{self.cache_prefix}{topics_str}"
    
    def get_cached_news(self, topics: List[str]) -> Optional[str]:
        """Get cached news if available and not expired"""
        cache_key = self._get_cache_key(topics)
        
        try:
            cached_data = storage.get_channels_data()
            if cache_key in cached_data:
                cache_entry = cached_data[cache_key]
                cache_time = datetime.fromisoformat(cache_entry["timestamp"])
                
                # Check if cache is still valid
                if datetime.now() - cache_time < timedelta(hours=self.cache_duration_hours):
                    print(f"Using cached news for topics: {', '.join(topics)}")
                    return cache_entry["content"]
                else:
                    # Remove expired cache
                    del cached_data[cache_key]
                    storage.save_channels_data(cached_data)
                    
        except Exception as e:
            print(f"Cache read error: {e}")
            
        return None
    
    def cache_news(self, topics: List[str], news_content: str):
        """Cache generated news"""
        cache_key = self._get_cache_key(topics)
        
        try:
            cached_data = storage.get_channels_data()
            cached_data[cache_key] = {
                "content": news_content,
                "timestamp": datetime.now().isoformat()
            }
            storage.save_channels_data(cached_data)
            print(f"Cached news for topics: {', '.join(topics)}")
            
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def check_api_limits(self, provider: str = "openrouter") -> Dict[str, any]:
        """Check and update API usage limits for different providers"""
        today = datetime.now().date().isoformat()
        
        # Default limits
        default_limits = {
            "gemini": 15,
            "groq": 43200,
            "grok": 100,
            "openrouter": 1000
        }
        
        try:
            limits_data = storage.get_channels_data()
            limits_key = f"{self.limits_prefix}{provider}_usage"
            
            if limits_key in limits_data:
                usage = limits_data[limits_key]
                self.requests_today[provider] = usage.get("requests_today", 0)
                self.last_reset_date[provider] = usage.get("last_reset_date")
                
                # Reset counter if it's a new day
                if self.last_reset_date[provider] != today:
                    self.requests_today[provider] = 0
                    self.last_reset_date[provider] = today
            else:
                self.requests_today[provider] = 0
                self.last_reset_date[provider] = today
                
            daily_limit = default_limits.get(provider, 100)
            
            return {
                "requests_today": self.requests_today[provider],
                "daily_limit": daily_limit,
                "remaining": max(0, daily_limit - self.requests_today[provider]),
                "reset_time": self.last_reset_date[provider],
                "can_request": self.requests_today[provider] < daily_limit
            }
            
        except Exception as e:
            print(f"API limits check error: {e}")
            daily_limit = default_limits.get(provider, 100)
            return {
                "requests_today": 0,
                "daily_limit": daily_limit,
                "remaining": daily_limit,
                "reset_time": today,
                "can_request": True
            }
    
    def record_api_request(self, provider: str = "openrouter") -> bool:
        """Record an API request, return True if successful"""
        limits = self.check_api_limits(provider)
        
        if not limits["can_request"]:
            return False
            
        try:
            limits_data = storage.get_channels_data()
            limits_key = f"{self.limits_prefix}{provider}_usage"
            
            self.requests_today[provider] += 1
            
            limits_data[limits_key] = {
                "requests_today": self.requests_today[provider],
                "last_reset_date": self.last_reset_date[provider]
            }
            
            storage.save_channels_data(limits_data)
            print(f"API request recorded for {provider}. Total today: {self.requests_today[provider]}/{limits['daily_limit']}")
            return True
            
        except Exception as e:
            print(f"API request recording error: {e}")
            return False
    
    def get_time_until_reset(self) -> str:
        """Get time until daily limit resets"""
        if not self.last_reset_date:
            return "Unknown"
            
        now = datetime.now()
        next_reset = datetime.combine(
            datetime.now().date() + timedelta(days=1), 
            datetime.min.time()
        )
        
        time_until = next_reset - now
        hours = time_until.seconds // 3600
        minutes = (time_until.seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

# Global cache instance
cache_manager = CacheManager()
