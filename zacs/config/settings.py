"""
Django settings for ZASCA project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
PRODUCTION_SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not PRODUCTION_SECRET_KEY:
    import secrets
    import string
    # 生成安全的随机密钥
    alphabet = string.ascii_letters + string.digits + string.punctuation
    PRODUCTION_SECRET_KEY = ''.join(secrets.choice(alphabet) for _ in range(50))
    print("警告：未设置 DJANGO_SECRET_KEY 环境变量，已生成临时密钥")
    print("请在生产环境中设置强密钥：export DJANGO_SECRET_KEY='您的密钥'")
SECRET_KEY = PRODUCTION_SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', '').lower() in ['true', '1', 'yes']

# 环境标记：生产模式
PRODUCTION_MODE = os.environ.get('PRODUCTION_MODE', '').lower() in ['true', '1', 'yes'] or not DEBUG

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
    # 生产环境安全配置
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    # 验证并清理主机名
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
        raise ValueError("生产环境必须设置 ALLOWED_HOSTS 环境变量")

    CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'https://localhost,https://127.0.0.1').split(',')
    # 清理受信任的源
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS if origin.strip()]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 第三方应用
    'rest_framework',
    'corsheaders',
    'django_bootstrap5',

    # 本地应用
    'apps.accounts',
    'apps.hosts',
    'apps.operations',
    'apps.dashboard',
    'apps.certificates',
    'apps.bootstrap',
    'apps.audit',
    'apps.tasks',
    'apps.errors',
    'apps.themes',
    'plugins',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'config.maintenance_middleware.MaintenanceModeMiddleware',  # 维护模式中间件
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.bootstrap.middleware.SessionValidationMiddleware',  # 会话验证中间件
    'apps.bootstrap.middleware.SessionPersistenceMiddleware',  # 会话持久化中间件
    'config.demo_middleware.DemoModeMiddleware',  # DEMO模式中间件
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 自定义错误处理
handler400 = 'apps.errors.views.handler400'
handler403 = 'apps.errors.views.handler403'
handler404 = 'apps.errors.views.handler404'
handler500 = 'apps.errors.views.handler500'

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'frontend' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.themes.context_processors.theme_context',  # 主题上下文处理器
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

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
STATICFILES_DIRS = [BASE_DIR / 'frontend' / 'static']

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
CORS_ALLOW_ALL_ORIGINS = DEBUG


# Winrm settings
WINRM_TIMEOUT = 30  # Winrm连接超时时间（秒）
WINRM_MAX_RETRIES = 3  # Winrm连接最大重试次数

# 导入日志过滤器
from utils.sensitive_log_filters import SensitiveDataFilter, AuditFilter

# Logging settings
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'sensitive_data': {
            '()': SensitiveDataFilter,
        },
        'audit_operations': {
            '()': AuditFilter,
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(timestamp)s %(level)s %(name)s %(message)s %(user)s %(ip)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['sensitive_data', 'audit_operations'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'zasca.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['sensitive_data', 'audit_operations'],
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO' if PRODUCTION_MODE else 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO' if PRODUCTION_MODE else 'DEBUG',
            'propagate': False,
        },
        'zasca': {
            'handlers': ['console', 'file'],
            'level': 'INFO' if PRODUCTION_MODE else 'DEBUG',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'audit': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# 安全配置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'  # 防止点击劫持

# HTTPS相关安全配置 (仅在生产环境中启用)
if PRODUCTION_MODE and not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 一年
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # 额外的生产环境安全配置
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Cookie 安全设置
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True

    # 设置 Cookie 过期时间
    SESSION_COOKIE_AGE = 86400  # 24 小时
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

    # 限制文件上传大小
    FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
    DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

    # 防止时间攻击
    USE_TZ = True

    # 安全头设置
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    X_FRAME_OPTIONS = 'DENY'

# Geetest (极验) 验证码配置
GEETEST_ID = os.environ.get('GEETEST_ID')
GEETEST_KEY = os.environ.get('GEETEST_KEY')
# 是否在极验服务不可用时回退到本地验证码（True/False）
GEETEST_FALLBACK_LOCAL = os.environ.get('GEETEST_FALLBACK_LOCAL', 'True').lower() == 'true'
# 缓存极验服务状态的秒数（用于短期内避免重复探测）
GEETEST_SERVER_STATUS_CACHE_SECONDS = int(os.environ.get('GEETEST_SERVER_STATUS_CACHE_SECONDS', '300'))

# DEMO模式配置
if os.environ.get('ZASCA_DEMO', '').lower() == '1':
    # 使用DEMO数据库
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'DEMO.sqlite3',
        }
    }
    
    # 禁用密码验证器以允许简单密码
    AUTH_PASSWORD_VALIDATORS = []
    
    # 允许所有主机
    ALLOWED_HOSTS = ['*']
    
    # DEBUG模式开启
    DEBUG = True
    
    # 设置固定密钥
    SECRET_KEY = 'demo-mode-secret-key-for-testing-purposes-only'

# DEMO模式启动消息
if os.environ.get('ZASCA_DEMO', '').lower() == '1':
    from config.demo_startup import show_demo_startup_message
    show_demo_startup_message()

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Bootstrap认证配置
BOOTSTRAP_SHARED_SALT = os.environ.get('BOOTSTRAP_SHARED_SALT', 'MY_SECRET_2024')

# WinRM 客户端安全配置
WINRM_CLIENT_CERT_VALIDATION = os.environ.get('WINRM_CLIENT_CERT_VALIDATION', 'ignore')  # ignore 或 validate
WINRM_CLIENT_CERT_PATH = os.environ.get('WINRM_CLIENT_CERT_PATH')
WINRM_CLIENT_KEY_PATH = os.environ.get('WINRM_CLIENT_KEY_PATH')
WINRM_CLIENT_CA_PATH = os.environ.get('WINRM_CLIENT_CA_PATH')

# API 限流配置（每分钟请求次数）
API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', '60'))
LOGIN_RATE_LIMIT = int(os.environ.get('LOGIN_RATE_LIMIT', '30'))
