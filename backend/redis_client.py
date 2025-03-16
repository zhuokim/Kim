import logging
import os
import json
import redis.asyncio as redis
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from .config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, DEBUG

# 设置日志
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.local_storage = {}
        self.redis = None
        
        # Try to initialize Redis if environment variables are available
        redis_url = os.getenv("REDIS_URL") or os.getenv("KV_REST_API_URL")
        
        if redis_url:
            try:
                self.redis = redis.from_url(redis_url)
                logger.info("Successfully connected to Redis")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {str(e)}")
                logger.info("Falling back to local storage")
        else:
            logger.info("No Redis credentials found, using local storage")

    async def ensure_connection(self):
        """Check if connection is available"""
        if self.redis:
            try:
                await self.redis.ping()
                return True
            except:
                return False
        return True  # Local storage is always available

    async def set(self, key: str, value: str) -> bool:
        """Set key to hold the string value"""
        try:
            if self.redis:
                await self.redis.set(key, value)
            else:
                self.local_storage[key] = value
            return True
        except Exception as e:
            logger.error(f"Error in set operation: {str(e)}")
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get the value of key"""
        try:
            if self.redis:
                value = await self.redis.get(key)
                return value.decode('utf-8') if value else None
            return self.local_storage.get(key)
        except Exception as e:
            logger.error(f"Error in get operation: {str(e)}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key"""
        try:
            if self.redis:
                await self.redis.delete(key)
            else:
                self.local_storage.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Error in delete operation: {str(e)}")
            return False

    async def zadd(self, key: str, mapping: Dict[str, float]) -> bool:
        """Add members to a sorted set"""
        try:
            if self.redis:
                await self.redis.zadd(key, mapping)
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
            if self.redis:
                result = await self.redis.zrange(key, start, stop, withscores=withscores)
                if withscores:
                    return [(item[0].decode('utf-8'), float(item[1])) for item in result]
                return [item.decode('utf-8') for item in result]
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
            if self.redis:
                result = await self.redis.zrevrange(key, start, stop, withscores=withscores)
                if withscores:
                    return [(item[0].decode('utf-8'), float(item[1])) for item in result]
                return [item.decode('utf-8') for item in result]
            else:
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
            if self.redis:
                await self.redis.hset(key, mapping=mapping)
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
            if self.redis:
                result = await self.redis.hgetall(key)
                return {k.decode('utf-8'): v.decode('utf-8') for k, v in result.items()}
            return self.local_storage.get(key, {})
        except Exception as e:
            logger.error(f"Error in hgetall operation: {str(e)}")
            return {}

# 创建 Redis 客户端实例
redis_client = RedisClient()