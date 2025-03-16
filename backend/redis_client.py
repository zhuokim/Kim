import logging
import os
import json
from typing import Dict, Any, Optional, List, Tuple, Union

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.storage = {}
        logger.info("Using local storage mode")

    async def ensure_connection(self):
        """Check if connection is available"""
        return True  # Local storage is always available

    async def set(self, key: str, value: str) -> bool:
        """Set key to hold the string value"""
        try:
            self.storage[key] = value
            return True
        except Exception as e:
            logger.error(f"Error in set operation: {str(e)}")
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get the value of key"""
        try:
            return self.storage.get(key)
        except Exception as e:
            logger.error(f"Error in get operation: {str(e)}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key"""
        try:
            self.storage.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Error in delete operation: {str(e)}")
            return False

    async def zadd(self, key: str, mapping: Dict[str, float]) -> bool:
        """Add members to a sorted set"""
        try:
            if key not in self.storage:
                self.storage[key] = {}
            self.storage[key].update(mapping)
            return True
        except Exception as e:
            logger.error(f"Error in zadd operation: {str(e)}")
            return False

    async def zrange(self, key: str, start: int, stop: int, withscores: bool = False) -> Union[List[str], List[tuple]]:
        """Return a range of members from a sorted set"""
        try:
            data = self.storage.get(key, {})
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
            if key not in self.storage:
                self.storage[key] = {}
            self.storage[key].update(mapping)
            return True
        except Exception as e:
            logger.error(f"Error in hset operation: {str(e)}")
            return False

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all the fields and values in a hash"""
        try:
            return self.storage.get(key, {})
        except Exception as e:
            logger.error(f"Error in hgetall operation: {str(e)}")
            return {}

# 创建 Redis 客户端实例
redis_client = RedisClient()