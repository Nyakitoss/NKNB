import os
import json
import redis
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

# Глобальный экземпляр для совместимости с существующим кодом
storage = StorageManager()
