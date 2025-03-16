import redis
import logging
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List, Tuple, Union

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.db = int(os.getenv('REDIS_DB', 0))
        self.client = None
        self.connect()
    
    def connect(self):
        """连接到Redis服务器"""
        try:
            logger.info(f"Attempting to connect to Redis at {self.host}:{self.port} (DB: {self.db})")
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
            pong = self.client.ping()
            logger.info(f"Redis ping response: {pong}")
            
            # 测试基本操作
            test_key = "test_connection"
            self.client.set(test_key, "test_value")
            test_value = self.client.get(test_key)
            self.client.delete(test_key)
            logger.info("Redis test operations successful")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    def ensure_connection(self):
        """确保Redis连接可用"""
        try:
            if not self.client or not self.client.ping():
                self.connect()
        except Exception as e:
            logger.error(f"Redis connection check failed: {str(e)}")
            self.connect()

    def set(self, key: str, value: Union[str, int, float]) -> bool:
        """设置键值对"""
        try:
            self.ensure_connection()
            return self.client.set(key, value)
        except Exception as e:
            logger.error(f"Error setting key {key}: {str(e)}")
            raise

    def get(self, key: str) -> Optional[str]:
        """获取键值"""
        try:
            self.ensure_connection()
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Error getting key {key}: {str(e)}")
            raise

    def delete(self, key: str) -> int:
        """删除键"""
        try:
            self.ensure_connection()
            return self.client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key {key}: {str(e)}")
            raise

    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """添加到有序集合"""
        try:
            self.ensure_connection()
            return self.client.zadd(name, mapping)
        except Exception as e:
            logger.error(f"Error adding to sorted set {name}: {str(e)}")
            raise

    def zrevrange(self, name: str, start: int, end: int, withscores: bool = False) -> List[Union[str, Tuple[str, float]]]:
        """获取有序集合的范围（按分数降序）"""
        try:
            self.ensure_connection()
            return self.client.zrevrange(name, start, end, withscores=withscores)
        except Exception as e:
            logger.error(f"Error getting range from sorted set {name}: {str(e)}")
            raise

    def scan_iter(self, match: Optional[str] = None, count: Optional[int] = None) -> List[str]:
        """扫描键"""
        try:
            self.ensure_connection()
            return list(self.client.scan_iter(match=match, count=count))
        except Exception as e:
            logger.error(f"Error scanning keys with pattern {match}: {str(e)}")
            raise

    def hset(self, name: str, mapping: Dict[str, str]) -> int:
        """设置哈希表字段"""
        try:
            self.ensure_connection()
            return self.client.hset(name, mapping=mapping)
        except Exception as e:
            logger.error(f"Error setting hash fields for {name}: {str(e)}")
            raise

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希表字段"""
        try:
            self.ensure_connection()
            return self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Error getting hash field {key} from {name}: {str(e)}")
            raise

    def hgetall(self, name: str) -> Dict[str, str]:
        """获取哈希表所有字段"""
        try:
            self.ensure_connection()
            return self.client.hgetall(name)
        except Exception as e:
            logger.error(f"Error getting all hash fields from {name}: {str(e)}")
            raise

    def exists(self, *names: str) -> int:
        """检查键是否存在"""
        try:
            self.ensure_connection()
            return self.client.exists(*names)
        except Exception as e:
            logger.error(f"Error checking existence of keys {names}: {str(e)}")
            raise

    def expire(self, name: str, time: int) -> bool:
        """设置键的过期时间（秒）"""
        try:
            self.ensure_connection()
            return self.client.expire(name, time)
        except Exception as e:
            logger.error(f"Error setting expiry for {name}: {str(e)}")
            raise

# 创建Redis客户端实例
redis_client = RedisClient()