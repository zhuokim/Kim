import logging
import os
import json
import redis
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from .config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, DEBUG

# 设置日志
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        try:
            self.redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True
            )
            # 测试连接
            self.redis.ping()
            logger.info("Successfully connected to Redis")
        except redis.ConnectionError as e:
            logger.warning(f"Could not connect to Redis: {e}")
            logger.info("Falling back to local storage")
            self.redis = None
            self._init_local_storage()

    def _init_local_storage(self):
        """初始化本地存储"""
        self.storage_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "local_storage"
        self.storage_dir.mkdir(exist_ok=True)
        self.data_file = self.storage_dir / "data.json"
        self.data = self._load_data()

    def _load_data(self):
        """从文件加载数据"""
        if hasattr(self, 'data_file') and self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading data: {str(e)}")
                return {}
        return {}

    def _save_data(self):
        """保存数据到文件"""
        if hasattr(self, 'data_file'):
            try:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error saving data: {str(e)}")

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置键值对"""
        try:
            if self.redis:
                return self.redis.set(key, json.dumps(value), ex=ex)
            else:
                self.data[key] = value
                self._save_data()
                return True
        except Exception as e:
            logger.error(f"Error in set: {str(e)}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        try:
            if self.redis:
                value = self.redis.get(key)
                return json.loads(value) if value else None
            else:
                return self.data.get(key)
        except Exception as e:
            logger.error(f"Error in get: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        """删除键"""
        try:
            if self.redis:
                return bool(self.redis.delete(key))
            else:
                if key in self.data:
                    del self.data[key]
                    self._save_data()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error in delete: {str(e)}")
            return False

    def zadd(self, name: str, mapping: Dict[str, float]) -> bool:
        """添加到有序集合"""
        try:
            if self.redis:
                return bool(self.redis.zadd(name, mapping))
            else:
                self.data.setdefault(name, {}).update(mapping)
                self._save_data()
                return True
        except Exception as e:
            logger.error(f"Error in zadd: {str(e)}")
            return False

    def zrevrange(self, name: str, start: int, end: int, withscores: bool = False) -> Union[List[str], List[Tuple[str, float]]]:
        """获取有序集合的范围"""
        try:
            if self.redis:
                result = self.redis.zrevrange(name, start, end, withscores=withscores)
                return result
            else:
                if name not in self.data:
                    return []
                sorted_items = sorted(self.data[name].items(), key=lambda x: x[1], reverse=True)
                items = sorted_items[start:end+1]
                if withscores:
                    return items
                return [item[0] for item in items]
        except Exception as e:
            logger.error(f"Error in zrevrange: {str(e)}")
            return []

# 创建 Redis 客户端实例
redis_client = RedisClient()