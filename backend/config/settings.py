"""
Django settings for config project (Dashboard de Cartera).
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-me')
DEBUG = env_bool('DEBUG', True)
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]
if DEBUG:
    ALLOWED_HOSTS.append('testserver')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'cartera',
    # --- Integración skelleton_base (docs/integracion/) -------------------------
    'apps.core',
    'apps.audit',
    'apps.permissions',
    'apps.authentication',
    'apps.users',
    'apps.roles',
    'apps.branding',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- Base de datos ---------------------------------------------------------
# SQL Server vía mssql-django. Para desarrollo local sin SQL Server disponible,
# basta con exportar DB_ENGINE=sqlite y no se toca ninguna línea de este archivo.
if os.getenv('DB_ENGINE', 'mssql') == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    extra_params = []
    encrypt = os.getenv('DB_ENCRYPT', 'no')
    trust_cert = os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'yes')
    extra_params.append(f'Encrypt={encrypt}')
    extra_params.append(f'TrustServerCertificate={trust_cert}')

    DATABASES = {
        'default': {
            'ENGINE': 'mssql',
            'NAME': os.getenv('DB_NAME', 'cms_dashboards'),
            'USER': os.getenv('DB_USER', 'sa'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '1433'),
            'OPTIONS': {
                'driver': 'ODBC Driver 17 for SQL Server',
                'extra_params': ';'.join(extra_params),
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'users.User'

# Argon2 primero: hash de contraseñas más robusto que el PBKDF2 por defecto de Django (requiere
# el paquete `argon2-cffi`, ya en requirements.txt). Los hashers siguientes son solo fallback de
# lectura (por si alguna vez hay hashes con otro algoritmo).
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# --- JWT (apps.authentication) ------------------------------------------------
LOGIN_MAX_FAILED_ATTEMPTS = int(os.getenv('LOGIN_MAX_FAILED_ATTEMPTS', 5))
LOGIN_LOCKOUT_MINUTES = int(os.getenv('LOGIN_LOCKOUT_MINUTES', 15))

# --- Correo / recuperación de contraseña (apps.authentication, Módulo D) -------
# Por defecto, backend de consola: nunca se envía un correo real sin configurar EMAIL_BACKEND
# explícitamente. Las pruebas automatizadas (`manage.py test`) ignoran esto de todas formas —
# Django las fuerza siempre al backend en memoria (`locmem`), sin importar esta configuración.
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@cms-dashboards.local')

# Nunca hardcodear el dominio del enlace de recuperación — siempre desde esta variable.
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
PASSWORD_RESET_TOKEN_LIFETIME_MINUTES = int(os.getenv('PASSWORD_RESET_TOKEN_LIFETIME_MINUTES', 30))

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 15))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7))),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': os.getenv('JWT_ALGORITHM', 'HS256'),
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY', SECRET_KEY),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Django REST Framework ---------------------------------------------------
# `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` (Fase 5 de la integración con skelleton_base,
# docs/integracion/decisions.md #6): todo endpoint exige sesión salvo que una vista fije
# explícitamente `permission_classes = [AllowAny]` (login, refresh, tema institucional público).
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.authentication.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'EXCEPTION_HANDLER': 'cartera.exceptions.cartera_exception_handler',
    # `password_reset`: usado por `PasswordResetRequestView` (sección 7.6, prevención de abuso).
    'DEFAULT_THROTTLE_RATES': {
        'password_reset': os.getenv('PASSWORD_RESET_THROTTLE_RATE', '5/hour'),
    },
}

# --- CORS --------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173').split(',') if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# --- Carga de archivos ---------------------------------------------------------
UPLOAD_MAX_SIZE_BYTES = int(os.getenv('UPLOAD_MAX_SIZE_BYTES', 25 * 1024 * 1024))
DATA_UPLOAD_MAX_MEMORY_SIZE = UPLOAD_MAX_SIZE_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = UPLOAD_MAX_SIZE_BYTES
CARTERA_TEMP_UPLOADS_DIR = MEDIA_ROOT / 'uploads_temp'
CARTERA_TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
CARTERA_EXPORTS_DIR = MEDIA_ROOT / 'exports_temp'
CARTERA_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Fila máxima insertada por lote hacia SQL Server (sección 16 - rendimiento).
CARTERA_BULK_BATCH_SIZE = 2000
