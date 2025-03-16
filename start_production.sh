#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 加载环境变量
set -a
source production.env
set +a

# 启动应用
uvicorn backend.main:app \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --log-level $LOG_LEVEL \
    --ssl-keyfile $SSL_KEYFILE \
    --ssl-certfile $SSL_CERTFILE 