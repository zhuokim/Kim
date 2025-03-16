#!/bin/bash

# 检查并启动 Redis
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server &
fi

# 等待 Redis 完全启动
sleep 2

# 检查 Python 虚拟环境
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 设置环境变量
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export JWT_SECRET=local_development_secret
export DEBUG=true

# 启动应用
echo "Starting leaderboard application..."
uvicorn backend.main:app --host 0.0.0.0 --port 5050 --reload 