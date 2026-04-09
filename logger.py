import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path

class BotLogger:
    def __init__(self):
        self.log_file = Path("/app/data/bot_logs.json")
        self.log_file.parent.mkdir(exist_ok=True)
        self.hourly_task = None
        self.running = False
        
    async def log_bot_startup(self, ai_provider: str, models_count: int):
        """Log bot startup information"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "bot_startup",
            "ai_provider": ai_provider,
            "models_count": models_count,
            "message": f"Bot started with {ai_provider} provider and {models_count} models"
        }
        await self._write_log(log_entry)
        print(f"**LOG: Bot startup logged - Provider: {ai_provider}, Models: {models_count}**")
        
    async def start_hourly_logging(self):
        """Start logging current time every hour"""
        if self.running:
            return
            
        self.running = True
        print(f"**LOG: Started hourly logging system at {datetime.now().strftime('%H:%M:%S')}**")
        
        while self.running:
            try:
                current_time = datetime.now()
                log_entry = {
                    "timestamp": current_time.isoformat(),
                    "type": "hourly_check",
                    "message": f"Bot current time: {current_time.strftime('%d.%m.%Y %H:%M:%S')}",
                    "status": "running"
                }
                
                await self._write_log(log_entry)
                print(f"**LOG: Hourly check - {current_time.strftime('%d.%m.%Y %H:%M:%S')}**")
                
                # Wait until next hour
                next_hour = (current_time + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                sleep_seconds = (next_hour - current_time).total_seconds()
                
                await asyncio.sleep(sleep_seconds)
                
            except Exception as e:
                error_msg = f"Hourly logging error: {str(e)}"
                print(f"**LOG: {error_msg}**")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def log_generation_start(self, topics: list, models: list):
        """Log start of news generation"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "generation_start",
            "topics": topics,
            "available_models": models,
            "message": f"Starting news generation for topics: {', '.join(topics)}"
        }
        await self._write_log(log_entry)
    
    async def log_model_attempt(self, model: str, attempt: int, total: int):
        """Log attempt to use specific model"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "model_attempt",
            "model": model,
            "attempt": f"{attempt}/{total}",
            "message": f"Trying model: {model} ({attempt}/{total})"
        }
        await self._write_log(log_entry)
    
    async def log_model_error(self, model: str, error: str):
        """Log model error"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "model_error",
            "model": model,
            "error": error,
            "message": f"Model {model} failed: {error}"
        }
        await self._write_log(log_entry)
    
    async def log_generation_success(self, model: str, content_length: int):
        """Log successful generation"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "generation_success",
            "model": model,
            "content_length": content_length,
            "message": f"Successfully generated news using {model} ({content_length} characters)"
        }
        await self._write_log(log_entry)
    
    async def log_generation_failure(self, last_error: str):
        """Log generation failure"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "generation_failure",
            "last_error": last_error,
            "message": f"All models failed. Last error: {last_error}"
        }
        await self._write_log(log_entry)
    
    async def log_publication_success(self, model: str, channel_id: str):
        """Log successful publication"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "publication_success",
            "model": model,
            "channel_id": channel_id,
            "message": f"News published successfully using {model} to channel {channel_id}"
        }
        await self._write_log(log_entry)
    
    async def log_publication_failure(self, channel_id: str, error: str):
        """Log publication failure"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "publication_failure",
            "channel_id": channel_id,
            "error": error,
            "message": f"Failed to publish to channel {channel_id}: {error}"
        }
        await self._write_log(log_entry)
    
    async def _write_log(self, log_entry: dict):
        """Write log entry to file"""
        try:
            # Read existing logs
            logs = []
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            
            # Add new entry
            logs.append(log_entry)
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Write back to file
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"**LOG: Failed to write log entry: {str(e)}**")
    
    def stop(self):
        """Stop hourly logging"""
        self.running = False
        print(f"**LOG: Stopped hourly logging system at {datetime.now().strftime('%H:%M:%S')}**")

# Global logger instance
logger = BotLogger()
