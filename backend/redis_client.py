import logging
import os
import json
import redis
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from .config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, DEBUG
from vercel_kv import VercelKV

# 设置日志
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.local_storage = {}
        self.kv = None
        
        # Try to initialize Vercel KV if environment variables are available
        kv_url = os.getenv("KV_REST_API_URL")
        kv_token = os.getenv("KV_REST_API_TOKEN")
        
        if kv_url and kv_token:
            try:
                self.kv = VercelKV(url=kv_url, token=kv_token)
                logger.info("Successfully connected to Vercel KV")
            except Exception as e:
                logger.warning(f"Could not connect to Vercel KV: {str(e)}")
                logger.info("Falling back to local storage")
        else:
            logger.info("No Vercel KV credentials found, using local storage")

    async def ensure_connection(self):
        """Check if connection is available"""
        if self.kv:
            try:
                await self.kv.ping()
                return True
            except:
                return False
        return True  # Local storage is always available

    async def set(self, key: str, value: str) -> bool:
        """Set key to hold the string value"""
        try:
            if self.kv:
                await self.kv.set(key, value)
            else:
                self.local_storage[key] = value
            return True
        except Exception as e:
            logger.error(f"Error in set operation: {str(e)}")
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get the value of key"""
        try:
            if self.kv:
                return await self.kv.get(key)
            return self.local_storage.get(key)
        except Exception as e:
            logger.error(f"Error in get operation: {str(e)}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key"""
        try:
            if self.kv:
                await self.kv.delete(key)
            else:
                self.local_storage.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Error in delete operation: {str(e)}")
            return False

    async def zadd(self, key: str, mapping: Dict[str, float]) -> bool:
        """Add members to a sorted set"""
        try:
            if self.kv:
                # Store sorted set as a special format in Vercel KV
                current = await self.kv.get(f"zset:{key}") or {}
                if not isinstance(current, dict):
                    current = {}
                current.update(mapping)
                await self.kv.set(f"zset:{key}", current)
            else:
                if key not in self.local_storage:
                    self.local_storage[key] = {}
                self.local_storage[key].update(mapping)
            return True
        except Exception as e:
            logger.error(f"Error in zadd operation: {str(e)}")
            return False

    async def zrange(self, key: str, start: int, stop: int, withscores: bool = False) -> Union[List[str], List[tuple]]:
        """Return a range of members from a sorted set"""
        try:
            if self.kv:
                data = await self.kv.get(f"zset:{key}") or {}
            else:
                data = self.local_storage.get(key, {})

            # Sort by score
            sorted_items = sorted(data.items(), key=lambda x: float(x[1]))
            
            # Handle negative indices
            if stop < 0:
                stop = len(sorted_items) + stop + 1
            
            # Get the range
            result = sorted_items[start:stop]
            
            if withscores:
                return [(item[0], float(item[1])) for item in result]
            return [item[0] for item in result]
        except Exception as e:
            logger.error(f"Error in zrange operation: {str(e)}")
            return []

    async def zrevrange(self, key: str, start: int, stop: int, withscores: bool = False) -> Union[List[str], List[tuple]]:
        """Return a range of members from a sorted set, by score, with scores in descending order"""
        try:
            result = await self.zrange(key, start, stop, withscores=withscores)
            if withscores:
                return [(item[0], float(item[1])) for item in reversed(result)]
            return list(reversed(result))
        except Exception as e:
            logger.error(f"Error in zrevrange operation: {str(e)}")
            return []

    async def hset(self, key: str, mapping: Dict[str, Any]) -> bool:
        """Set multiple hash fields to multiple values"""
        try:
            if self.kv:
                await self.kv.set(f"hash:{key}", mapping)
            else:
                if key not in self.local_storage:
                    self.local_storage[key] = {}
                self.local_storage[key].update(mapping)
            return True
        except Exception as e:
            logger.error(f"Error in hset operation: {str(e)}")
            return False

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all the fields and values in a hash"""
        try:
            if self.kv:
                result = await self.kv.get(f"hash:{key}") or {}
                return {str(k): str(v) for k, v in result.items()}
            return self.local_storage.get(key, {})
        except Exception as e:
            logger.error(f"Error in hgetall operation: {str(e)}")
            return {}

# 创建 Redis 客户端实例
redis_client = RedisClient()