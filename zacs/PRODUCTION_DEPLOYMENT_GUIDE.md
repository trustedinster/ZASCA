# ZASCA 生产环境部署指南

## 概述
本指南帮助您将 ZASCA 系统安全地部署到生产环境。

## 环境准备

### 必需的环境变量
```bash
# Django 配置
export DJANGO_SECRET_KEY="your-very-long-secret-key-at-least-50-characters"
export DEBUG="false"
export PRODUCTION_MODE="true"

# 数据库配置
export DB_NAME="zasca_db"
export DB_USER="zasca_user"
export DB_PASSWORD="secure-db-password"
export DB_HOST="localhost"
export DB_PORT="5432"

# 主机配置
export ALLOWED_HOSTS="your-domain.com,www.your-domain.com"
export CSRF_TRUSTED_ORIGINS="https://your-domain.com,https://www.your-domain.com"

# WinRM 安全配置（推荐）
export WINRM_CLIENT_CERT_VALIDATION="validate"
export WINRM_CLIENT_CERT_PATH="/path/to/client-cert.pem"
export WINRM_CLIENT_KEY_PATH="/path/to/client-key.pem"
export WINRM_CLIENT_CA_PATH="/path/to/ca-cert.pem"

# 限流配置
export API_RATE_LIMIT="60"  # 每分钟 API 请求数
export LOGIN_RATE_LIMIT="30"  # 每分钟登录尝试数
```

### 系统要求
- Python 3.10+
- PostgreSQL 12+ / MySQL 8.0+
- Redis 6.0+ (用于缓存和异步任务)
- SSL 证书（推荐 Let's Encrypt）

## 部署步骤

### 1. 安装依赖
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 数据库初始化
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 3. 安全检查
```bash
python utils/production_checker.py
```

### 4. 启动服务
```bash
# 主服务
python manage.py runserver 0.0.0.0:8000

# 或生产环境部署
# gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# 异步任务（需要 Redis）
celery -A config worker -l info
celery -A config beat -l info
```

## 安全加固

### Nginx 配置示例
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/zasca/staticfiles/;
    }

    location /media/ {
        alias /path/to/zasca/media/;
    }
}
```

### 防火墙配置
```bash
# 允许端口
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS

# 如果 WinRM 客户端需要连接外部
sudo ufw allow out 5985/tcp  # WinRM HTTP
sudo ufw allow out 5986/tcp  # WinRM HTTPS
```

## 性能优化

### 数据库优化
1. 启用连接池
2. 定期 VACUUM 和 ANALYZE
3. 创建合适的索引

### 缓存配置
在 settings.py 中启用 Redis 缓存：
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## 监控与日志

### 日志轮转
配置 logrotate：
```bash
# /etc/logrotate.d/zasca
/path/to/zasca/logs/zasca.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

### 健康检查
1. 检查日志中的错误
2. 使用 Django Health Check
3. 监控数据库连接
4. 监控 Redis 连接

## 备份策略

### 数据库备份
```bash
# PostgreSQL 备份
pg_dump -U zasca_user zasca_db > zasca_$(date +%Y%m%d_%H%M%S).sql

# MySQL 备份
mysqldump -u zasca_user -p zasca_db > zasca_$(date +%Y%m%d_%H%M%S).sql
```

### 文件备份
- 定期备份 /media/ 目录
- 备份证书文件

## 常见问题排查

### 证书验证失败
1. 检查证书文件路径
2. 验证证书有效性
3. 检查证书链完整性

### 连接超时
1. 增加 WINRM_TIMEOUT
2. 检查网络连通性
3. 确认 WinRM 服务运行状态

## 维护计划

### 定期任务
1. 每周检查日志异常
2. 每月更新系统依赖
3. 每季度安全审计

### 更新部署
1. 备份当前环境
2. 在测试环境验证
3. 滚动更新生产环境

---

**注意**：部署前请务必运行 `python utils/production_checker.py` 进行安全检查和配置验证。