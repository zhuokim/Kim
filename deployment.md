# 实时评分排行榜系统部署指南

## 1. 系统要求

- Python 3.9+
- Redis 6.0+
- Nginx (用于反向代理)
- Supervisor (用于进程管理)

## 2. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip redis-server nginx supervisor

# CentOS
sudo yum update
sudo yum install python3 python3-pip redis nginx supervisor
```

## 3. 安装 Python 依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 4. 配置 Redis

```bash
# 编辑 Redis 配置
sudo nano /etc/redis/redis.conf

# 确保以下配置正确
bind 127.0.0.1
port 6379
```

## 5. 配置 Supervisor

创建配置文件：`/etc/supervisor/conf.d/leaderboard.conf`

```ini
[program:leaderboard]
directory=/path/to/realtime-leaderboard
command=/path/to/realtime-leaderboard/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 5050
user=your_user
autostart=true
autorestart=true
stderr_logfile=/var/log/leaderboard.err.log
stdout_logfile=/var/log/leaderboard.out.log
```

## 6. 配置 Nginx

创建配置文件：`/etc/nginx/sites-available/leaderboard`

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## 7. 启动服务

```bash
# 启动 Redis
sudo systemctl start redis
sudo systemctl enable redis

# 启动 Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start leaderboard

# 启动 Nginx
sudo ln -s /etc/nginx/sites-available/leaderboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 8. 安全配置

1. 配置防火墙：
```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

2. 设置 SSL 证书（推荐使用 Let's Encrypt）：
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com
```

## 9. 环境变量配置

创建 `.env` 文件：
```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
JWT_SECRET=your_secret_key
```

## 10. 系统维护

- 日志文件位置：`/var/log/leaderboard.*.log`
- 定期备份 Redis 数据
- 监控系统资源使用情况

## 11. 故障排除

1. 检查日志：
```bash
sudo tail -f /var/log/leaderboard.err.log
```

2. 检查服务状态：
```bash
sudo supervisorctl status leaderboard
sudo systemctl status redis
sudo systemctl status nginx
```

3. 重启服务：
```bash
sudo supervisorctl restart leaderboard
sudo systemctl restart redis
sudo systemctl restart nginx
``` 