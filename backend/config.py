import os
from pathlib import Path

# 基础目录配置
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leaderboard.db")

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 调试模式
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# 静态文件和模板配置
STATIC_DIR = BASE_DIR / "backend" / "static"
TEMPLATES_DIR = BASE_DIR / "backend" / "templates"

# 其他配置
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "https://*.onrender.com"
] 