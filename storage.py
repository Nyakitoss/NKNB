import os
import json
import redis
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

class StorageManager:
    def __init__(self):
        self.use_redis = os.getenv("USE_REDIS", "false").lower() == "true"
        
        if self.use_redis:
            self.redis_client = self._create_redis_client()
            self._test_redis_connection()
        else:
            self.redis_client = None
            self._local_storage = {}
    
    def _create_redis_client(self):
        """Create Redis client from URL or individual parameters"""
        redis_url = os.getenv("REDIS_URL")
        
        if redis_url:
            # Use REDIS_URL (Railway format: redis://user:pass@host:port)
            print(f"**LOG: Connecting to Redis via URL: {redis_url.split('@')[1] if '@' in redis_url else redis_url}**")
            return redis.from_url(redis_url, decode_responses=True)
        else:
            # Use individual parameters (fallback)
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", 6379))
            password = os.getenv("REDIS_PASSWORD")
            
            print(f"**LOG: Connecting to Redis via host: {host}:{port}**")
            return redis.Redis(
                host=host,
                port=port,
                password=password,
                decode_responses=True
            )
    
    def _test_redis_connection(self):
        try:
            self.redis_client.ping()
            print("**LOG: Redis connected successfully**")
        except Exception as e:
            print(f"**LOG: Redis connection failed: {e}**")
            print("**LOG: Falling back to local storage**")
            self.use_redis = False
            self.redis_client = None
            self._local_storage = {}
    
    def get_channels_data(self) -> Dict[str, Any]:
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get("channels_data")
                return json.loads(data) if data else {}
            except Exception as e:
                print(f"❌ Redis read error: {e}")
                return {}
        else:
            return self._local_storage.get("channels_data", {})
    
    def save_channels_data(self, data: Dict[str, Any]) -> bool:
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.set("channels_data", json.dumps(data, ensure_ascii=False))
                return True
            except Exception as e:
                print(f"❌ Redis write error: {e}")
                return False
        else:
            self._local_storage["channels_data"] = data
            return True
    
    def get_channel_config(self, channel_id: str) -> Optional[Dict[str, Any]]:
        data = self.get_channels_data()
        return data.get(channel_id)
    
    def save_channel_config(self, channel_id: str, config: Dict[str, Any]) -> bool:
        data = self.get_channels_data()
        data[channel_id] = config
        return self.save_channels_data(data)
    
    def delete_channel_config(self, channel_id: str) -> bool:
        data = self.get_channels_data()
        if channel_id in data:
            del data[channel_id]
            return self.save_channels_data(data)
        return False
    
    def get_user_channels(self, user_id: int) -> Dict[str, Any]:
        """Get all channels accessible by user"""
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get(f"user_channels:{user_id}")
                return json.loads(data) if data else {}
            except Exception as e:
                print(f"**LOG: Redis read error for user channels: {e}**")
                return {}
        else:
            return self._local_storage.get(f"user_channels:{user_id}", {})
    
    def save_user_channel(self, user_id: int, channel_id: str, channel_info: Dict[str, Any]) -> bool:
        """Save channel to user's accessible channels list"""
        if self.use_redis and self.redis_client:
            try:
                user_channels = self.get_user_channels(user_id)
                user_channels[channel_id] = {
                    "title": channel_info.get("title", ""),
                    "username": channel_info.get("username", ""),
                    "added_at": datetime.now().isoformat()
                }
                self.redis_client.set(f"user_channels:{user_id}", json.dumps(user_channels, ensure_ascii=False))
                return True
            except Exception as e:
                print(f"**LOG: Redis write error for user channels: {e}**")
                return False
        else:
            user_channels = self._local_storage.get(f"user_channels:{user_id}", {})
            user_channels[channel_id] = {
                "title": channel_info.get("title", ""),
                "username": channel_info.get("username", ""),
                "added_at": datetime.now().isoformat()
            }
            self._local_storage[f"user_channels:{user_id}"] = user_channels
            return True
    
    def remove_user_channel(self, user_id: int, channel_id: str) -> bool:
        """Remove channel from user's accessible channels list"""
        if self.use_redis and self.redis_client:
            try:
                user_channels = self.get_user_channels(user_id)
                if channel_id in user_channels:
                    del user_channels[channel_id]
                    self.redis_client.set(f"user_channels:{user_id}", json.dumps(user_channels, ensure_ascii=False))
                return True
            except Exception as e:
                print(f"**LOG: Redis delete error for user channels: {e}**")
                return False
        else:
            user_channels = self._local_storage.get(f"user_channels:{user_id}", {})
            if channel_id in user_channels:
                del user_channels[channel_id]
                self._local_storage[f"user_channels:{user_id}"] = user_channels
            return True

# Глобальный экземпляр для совместимости с существующим кодом
storage = StorageManager()
