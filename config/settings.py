"""
Django settings for ZASCA project.

配置加载优先级（从高到低）：
1. 环境变量（os.environ）- 方便 DEMO 配置和容器部署
2. .env 文件 - 本地开发配置
3. 默认值 - 确保基本可用

DEMO 模式（ZASCA_DEMO=1）会强制锁定特定配置，不受 .env 影响。
"""

import os
from pathlib import Path

import pymysql
pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ========== .env 文件加载 ==========
# 优先级：环境变量 > .env 文件 > 默认值
# 使用 python-dotenv 加载 .env，但不覆盖已存在的环境变量
from dotenv import load_dotenv

ENV_FILE = BASE_DIR / '.env'
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=False)


def _env(key, default=None):
    """
    读取配置的统一入口。
    优先级：环境变量 > .env 文件 > 默认值
    """
    return os.environ.get(key, default)


# ========== 核心配置（必须在初始化时定义） ==========

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _env('DJANGO_SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env('DEBUG', 'True').lower() == 'true'

# 允许的主机列表
# 在DEBUG模式下，允许所有主机
if DEBUG:
    ALLOWED_HOSTS = ['*']
    # CSRF Trusted Origins - 添加内网穿透域名
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost',
        'http://127.0.0.1',
        'https://localhost',
        'https://127.0.0.1',
        'https://demo.supercmd.dpdns.org',  # 内网穿透域名
        'https://zasca.supercmd.dpdns.org',
    ]
else:
    ALLOWED_HOSTS = _env('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    CSRF_TRUSTED_ORIGINS = _env('CSRF_TRUSTED_ORIGINS', 'https://localhost,https://127.0.0.1').split(',')

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 第三方应用
    'rest_framework',
    'corsheaders',

    # 模板组件框架（必须在本地应用之前，确保 cotton 模板优先发现）
    'django_cotton',

    # 本地应用
    'apps.accounts',
    'apps.hosts',
    'apps.operations',
    'apps.dashboard',
    'apps.certificates',
    'apps.bootstrap',  # 主机引导系统
    'apps.audit',
    'apps.tasks',
    'apps.themes',  # 主题系统
    'apps.tunnel',  # 隧道管理
    'apps.tickets',  # 工单系统
    'apps.provider',  # 提供商后台（新版 Tailwind/MD3）
    'apps.provider_backend',  # 提供商后台（旧版，保留中间件和API）
    'plugins',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'config.maintenance_middleware.MaintenanceModeMiddleware',  # 维护模式中间件
    'config.local_lock_middleware.LocalLockMiddleware',  # 本地访问限制中间件
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.bootstrap.middleware.SessionValidationMiddleware',  # 主机引导系统的会话验证中间件
    'config.demo_middleware.DemoModeMiddleware',  # DEMO模式中间件
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.dashboard.context_processors.system_config',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DB_ENGINE = _env('DB_ENGINE', 'sqlite').lower()

if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': _env('DB_NAME', 'zasca'),
            'USER': _env('DB_USER', 'root'),
            'PASSWORD': _env('DB_PASSWORD', ''),
            'HOST': _env('DB_HOST', '127.0.0.1'),
            'PORT': _env('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': (
                    "SET sql_mode='STRICT_TRANS_TABLES'"
                ),
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = _env(
    'CORS_ALLOW_ALL_ORIGINS', 'True' if DEBUG else 'False'
).lower() == 'true'


# Winrm settings
WINRM_TIMEOUT = int(_env('WINRM_TIMEOUT', '30'))  # Winrm连接超时时间（秒）
WINRM_MAX_RETRIES = int(_env('WINRM_RETRY_COUNT', '3'))  # Winrm连接最大重试次数

# Logging settings
# 默认只输出到 stdout，方便 nohup/systemd 等收集日志
# 如需文件日志，设置环境变量 LOG_FILE=/path/to/zasca.log
LOG_LEVEL = _env('LOG_LEVEL', 'INFO')
LOG_FILE = _env('LOG_FILE', '')

_logging_handlers = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    },
}
_logging_root_handlers = ['console']
_logging_logger_handlers = ['console']

if LOG_FILE:
    _logging_handlers['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': LOG_FILE,
        'maxBytes': 1024 * 1024 * 10,  # 10MB
        'backupCount': 5,
        'formatter': 'verbose',
    }
    _logging_root_handlers.append('file')
    _logging_logger_handlers.append('file')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': _logging_handlers,
    'root': {
        'handlers': _logging_root_handlers,
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': _logging_logger_handlers,
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'zasca': {
            'handlers': _logging_logger_handlers,
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# 安全配置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

USE_X_FORWARDED_FOR = _env(
    'USE_X_FORWARDED_FOR', 'False'
).lower() == 'true'

SESSION_COOKIE_SECURE = _env(
    'SESSION_COOKIE_SECURE', 'True' if not DEBUG else 'False'
).lower() == 'true'
CSRF_COOKIE_SECURE = _env(
    'CSRF_COOKIE_SECURE', 'True' if not DEBUG else 'False'
).lower() == 'true'
SESSION_COOKIE_HTTPONLY = True

# HTTPS相关安全配置 (仅在生产环境中启用)
if not DEBUG:
    SECURE_SSL_REDIRECT = _env('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SECURE_HSTS_SECONDS = 31536000  # 一年
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Redis 配置 (保留用于兼容性检查，实际不再使用)
REDIS_URL = _env('REDIS_URL', 'redis://localhost:6379/0')

# Celery 配置 (使用 SQLite 替代 Redis)
CELERY_BROKER_URL = _env(
    'CELERY_BROKER_URL',
    f'sqla+sqlite:///{BASE_DIR / "celery_broker.sqlite3"}'
)
CELERY_RESULT_BACKEND = _env(
    'CELERY_RESULT_BACKEND',
    f'db+sqlite:///{BASE_DIR / "celery_results.sqlite3"}'
)
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'polling_interval': 1,
}

# Gateway 控制面配置
GATEWAY_ENABLED = _env(
    'GATEWAY_ENABLED', 'False'
).lower() in ('true', '1', 'yes')
GATEWAY_CONTROL_SOCKET = _env(
    'GATEWAY_CONTROL_SOCKET', '/run/zasca/control.sock'
)

# RDP 域名配置
RDP_DOMAIN = _env('RDP_DOMAIN', 'zasca.com')

# ========== DEMO模式配置（强制锁定，不受 .env 影响） ==========
ZASCA_DEMO = os.environ.get('ZASCA_DEMO', '').lower() == '1'

if ZASCA_DEMO:
    # DEMO模式强制使用 DEMO.sqlite3，不受 DB_ENGINE 或 .env 影响
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'DEMO.sqlite3',
        }
    }

    # DEMO模式保留最小长度验证，仅放宽复杂度要求
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
            'OPTIONS': {'min_length': 4},
        },
    ]

    # 允许所有主机
    ALLOWED_HOSTS = ['*']

    # DEBUG模式开启
    DEBUG = True

    # 生成随机SECRET_KEY（每次启动不同）
    import secrets as _secrets
    SECRET_KEY = _secrets.token_urlsafe(50)
    import logging as _logging
    _logging.getLogger('zasca').warning('DEMO模式: 使用随机生成的SECRET_KEY，重启后所有session将失效')

# DEMO模式启动消息
if ZASCA_DEMO:
    from config.demo_startup import show_demo_startup_message
    show_demo_startup_message()

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Bootstrap认证配置
BOOTSTRAP_SHARED_SALT = _env('BOOTSTRAP_SHARED_SALT', '')
