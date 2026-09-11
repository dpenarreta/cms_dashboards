"""
Django settings for config project (Dashboard de Cartera).
"""

import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


# `DEBUG` por defecto en False y `SECRET_KEY` sin valor de respaldo: un despliegue al que le falta
# una variable debe fallar ruidosamente, no arrancar en modo desarrollo ni firmar con una clave
# que está publicada en el repositorio. Para desarrollo local, `backend/.env` define DEBUG=True.
DEBUG = env_bool('DEBUG', False)
SECRET_KEY = os.getenv('SECRET_KEY') or ('django-insecure-solo-para-desarrollo' if DEBUG else '')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]
if DEBUG:
    ALLOWED_HOSTS.append('testserver')

# Claves de firma: sin ellas, cualquiera que conozca el default del repositorio puede emitir
# tokens válidos para cualquier usuario. Con DEBUG=False se exige que estén definidas de verdad y
# se corta el arranque si falta alguna, en vez de dejar que la cascada
# JWT_SECRET_KEY -> SECRET_KEY -> literal público pase inadvertida.
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or SECRET_KEY
if not DEBUG:
    _faltantes = [
        nombre for nombre, valor in (('SECRET_KEY', SECRET_KEY), ('JWT_SECRET_KEY', JWT_SECRET_KEY))
        if not valor or valor.startswith('django-insecure') or valor == 'change-me'
    ]
    if _faltantes:
        raise ImproperlyConfigured(
            'Con DEBUG=False hay que definir una clave real en: ' + ', '.join(_faltantes) +
            '. Generá una con: python -c "import secrets; print(secrets.token_urlsafe(64))"'
        )

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
    # Cifrado activado y certificado validado por defecto: el tráfico hacia SQL Server lleva
    # credenciales y datos de cartera, así que ir en claro tiene que ser una excepción que el
    # entorno declara a mano (DB_ENCRYPT=no en `.env` de desarrollo), no el comportamiento base.
    encrypt = os.getenv('DB_ENCRYPT', 'yes')
    trust_cert = os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'no')
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

# --- Conexión externa de solo lectura ("Conectar vista de base de datos") --
# Conexión "por defecto" de la app hacia una base productiva de origen — separada de DATABASES de
# arriba (que es la base propia de esta app). No se modela como una segunda entrada de DATABASES
# a propósito: se usa vía pyodbc directo (`cartera/services/db_source.py`) para una única consulta
# de solo lectura por carga, no para que el ORM la enrute — evita el riesgo de que una migración o
# un query de Django termine apuntando por error a la base productiva. Sin EXTERNAL_DB_HOST
# configurado, `db_source.conectar` lanza un error de negocio claro en vez de intentar conectar a
# 'localhost' por defecto.
EXTERNAL_DB_HOST = os.getenv('EXTERNAL_DB_HOST', '')
EXTERNAL_DB_PORT = os.getenv('EXTERNAL_DB_PORT', '1433')
EXTERNAL_DB_NAME = os.getenv('EXTERNAL_DB_NAME', '')
EXTERNAL_DB_USER = os.getenv('EXTERNAL_DB_USER', '')
EXTERNAL_DB_PASSWORD = os.getenv('EXTERNAL_DB_PASSWORD', '')
# Mismo criterio que DB_ENCRYPT/DB_TRUST_SERVER_CERTIFICATE de arriba: cifrado y validación de
# certificado por defecto, ir en claro se declara explícitamente en el entorno.
EXTERNAL_DB_ENCRYPT = os.getenv('EXTERNAL_DB_ENCRYPT', 'yes')
EXTERNAL_DB_TRUST_SERVER_CERTIFICATE = os.getenv('EXTERNAL_DB_TRUST_SERVER_CERTIFICATE', 'no')

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
# Umbral por IP, agregado a los intentos por cuenta: el conteo por cuenta no detecta el patrón de
# probar una contraseña habitual contra muchas cuentas distintas desde la misma máquina (cada
# cuenta recibe un solo fallo). Más alto que el por-cuenta a propósito, para no castigar a una
# oficina detrás de una única IP saliente. 0 lo desactiva.
LOGIN_MAX_FAILED_ATTEMPTS_PER_IP = int(os.getenv('LOGIN_MAX_FAILED_ATTEMPTS_PER_IP', 30))

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

# --- Interpretación completa del dashboard (IA, Gemini) ----------------------
# Sin GEMINI_API_KEY configurada, `dashboard_interpretation.generar_interpretacion` lanza
# CarteraError (codigo='IA_NO_CONFIGURADA') en vez de fallar con un error genérico de red.
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 15))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7))),
    # Rotación activada: cada refresco emite un refresh nuevo y `Session.refresh_token_jti` se
    # actualiza, con lo cual la detección de reutilización de `refresh_tokens` (comparar el `jti`
    # presentado contra el vigente) pasa a poder dispararse de verdad — antes era una rama
    # inalcanzable, porque el `jti` nunca cambiaba. `BLACKLIST_AFTER_ROTATION` sigue en False a
    # propósito: la revocación es por el modelo `Session` propio, no por la blacklist de
    # simplejwt (ver `@.claude/rules/security.md`).
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': os.getenv('JWT_ALGORITHM', 'HS256'),
    'SIGNING_KEY': JWT_SECRET_KEY,
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
    # `login`: límite por IP, complementario al bloqueo por cuenta de
    # `BruteForceProtectionService` — ese cuenta fallos de UNA cuenta, así que no ve el patrón de
    # probar una contraseña habitual contra cientos de cuentas desde la misma IP.
    # `ia`: los endpoints de Gemini cuestan dinero por llamada y `hallazgos-ia` se dispara al
    # abrir un dashboard, así que necesitan tope propio.
    'DEFAULT_THROTTLE_RATES': {
        'password_reset': os.getenv('PASSWORD_RESET_THROTTLE_RATE', '5/hour'),
        # 60/min por IP: generoso a propósito. La defensa real contra fuerza bruta es el conteo
        # de FALLOS de `BruteForceProtectionService` (por cuenta y por IP); esto solo acota la
        # ráfaga. Un límite ajustado castigaría a una oficina entera detrás de una única IP
        # saliente, que es un caso normal y no un ataque.
        'login': os.getenv('LOGIN_THROTTLE_RATE', '60/min'),
        'ia': os.getenv('IA_THROTTLE_RATE', '20/hour'),
    },
}

# Los throttles de DRF llevan su contador en la caché, y la caché NO se reinicia entre tests
# (`django.test.TestCase` solo revierte la base). Con los límites activos, el test número N que
# inicia sesión falla por el consumo acumulado de los N-1 anteriores: una falla que depende del
# orden de ejecución y no de la corrección del código. Se desactivan durante `manage.py test` y
# los tests que verifican los límites los reactivan con `override_settings`
# (`apps.authentication.tests.LoginThrottleTests`). Mismo criterio con el que Django ya fuerza
# `EMAIL_BACKEND` a `locmem` durante las pruebas.
_EJECUTANDO_TESTS = 'test' in sys.argv

if _EJECUTANDO_TESTS:
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        clave: None for clave in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
    }

# --- Cabeceras y cookies de seguridad ------------------------------------------
# Todo esto se activa fuera de desarrollo (los 6 avisos de `manage.py check --deploy`). En
# desarrollo queda apagado porque el servidor local es HTTP y una cookie `Secure` no viajaría.
# Nunca durante `manage.py test`: el cliente de pruebas habla HTTP, así que con el redirect activo
# TODA petición de test responde 301 en vez de llegar a la vista (402 pruebas caían así al correr
# la suite con DEBUG=False, que es como corre en CI). `manage.py check --deploy` no pasa por acá
# —su argv no trae 'test'—, así que la verificación de despliegue sigue exigiéndolo.
SECURE_SSL_REDIRECT = False if _EJECUTANDO_TESTS else env_bool('SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# --- Cookie del refresh token (SEC-19) ---------------------------------------
# El refresh token viaja en una cookie `HttpOnly` en vez de devolverse en el cuerpo: así JavaScript
# no puede leerlo, y un XSS deja de poder llevarse una credencial de 7 días para usarla después
# fuera del navegador de la víctima.
REFRESH_COOKIE_NAME = 'cms_dashboards_refresh'
# `path` acotado a los endpoints de autenticación: la cookie no se manda en ninguna otra petición
# de la API, así que no queda expuesta en cada llamada a un dashboard.
REFRESH_COOKIE_PATH = '/api/auth'
# `Lax` alcanza mientras el frontend se sirva desde el mismo sitio que la API (el proxy de Vite en
# desarrollo, o un nginx único en producción): con `Lax` el navegador NO manda la cookie en un POST
# de otro sitio, que es lo que protege al endpoint de refresco de un CSRF. Si algún día el frontend
# vive en otro dominio, hay que poner 'None' — y `None` exige HTTPS, porque sin `Secure` el
# navegador descarta la cookie.
REFRESH_COOKIE_SAMESITE = os.getenv('REFRESH_COOKIE_SAMESITE', 'Lax')
REFRESH_COOKIE_SECURE = env_bool('REFRESH_COOKIE_SECURE', not DEBUG)
SECURE_HSTS_SECONDS = 0 if DEBUG else int(os.getenv('SECURE_HSTS_SECONDS', 31536000))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
# Detrás de un proxy/balanceador que termina TLS, para que Django reconozca la petición como
# segura y `SECURE_SSL_REDIRECT` no entre en un bucle de redirecciones.
if env_bool('USE_X_FORWARDED_PROTO', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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
# Los directorios NO se crean acá: importar este módulo no debe tocar el sistema de archivos (ver
# `cartera/utils/archivos.py::asegurar_directorio`, que los crea justo antes de escribir).
# Se retiró además `CARTERA_EXPORTS_DIR`: no lo usaba ninguna línea del proyecto y solo dejaba un
# directorio vacío en cada arranque — la exportación arma el archivo en memoria y lo devuelve en
# la respuesta (`services/export_service.py`), nunca lo escribe a disco.
CARTERA_TEMP_UPLOADS_DIR = MEDIA_ROOT / 'uploads_temp'
# A diferencia de CARTERA_TEMP_UPLOADS_DIR (se limpia a las 24h, `clean_temp_uploads`), el archivo
# que queda aplicado a un dashboard se copia acá para que su mapeo de columnas se pueda seguir
# ajustando después desde "Configurar componente" sin tener que volver a cargarlo.
CARTERA_ARCHIVOS_DIR = MEDIA_ROOT / 'archivos_dashboard'

if _EJECUTANDO_TESTS:
    # Las pruebas que suben un archivo escribían en el `media/` real del desarrollador y no
    # limpiaban nada: se habían acumulado más de 11.000 archivos huérfanos, que es lo que
    # `clean_temp_uploads` terminó barriendo la primera vez que se ejecutó. Solo
    # `test_borrado_de_archivos.py` aislaba estos directorios, con su propio `override_settings`;
    # el resto no. Se resuelve en un único lugar, con el mismo mecanismo que ya se usa acá para
    # los throttles y `SECURE_SSL_REDIRECT`, en vez de pedirle a cada prueba que se acuerde.
    # Un `override_settings` explícito de una prueba sigue teniendo precedencia sobre esto.
    _MEDIA_DE_PRUEBAS = Path(tempfile.gettempdir()) / 'cms_dashboards_pruebas'
    CARTERA_TEMP_UPLOADS_DIR = _MEDIA_DE_PRUEBAS / 'uploads_temp'
    CARTERA_ARCHIVOS_DIR = _MEDIA_DE_PRUEBAS / 'archivos_dashboard'
    MEDIA_ROOT = _MEDIA_DE_PRUEBAS / 'media'

# Fila máxima insertada por lote hacia SQL Server (sección 16 - rendimiento).
CARTERA_BULK_BATCH_SIZE = 2000

# --- Logging -------------------------------------------------------------------
# Sin este bloque, los loggers propios (`cartera.*`, `apps.*`) no tenían ningún handler: caían al
# `lastResort` de Python, que escribe a stderr sin formato, sin nivel configurable y sin el nombre
# del logger. Los `logger.exception` que diagnostican una conexión fallida a la base externa o un
# error del servicio de IA se volvían casi ilegibles justo cuando hacen falta.
#
# Solo consola a propósito: la rotación de archivos y el envío a un agregador son decisiones del
# entorno de despliegue (systemd/journald, Docker, IIS), no de la aplicación. `LOG_LEVEL` permite
# subir a DEBUG en un incidente sin tocar código.
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detallado': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'consola': {
            'class': 'logging.StreamHandler',
            'formatter': 'detallado',
        },
    },
    'root': {
        'handlers': ['consola'],
        'level': 'WARNING',
    },
    'loggers': {
        # Código propio: se sigue al nivel elegido.
        'cartera': {'handlers': ['consola'], 'level': LOG_LEVEL, 'propagate': False},
        'apps': {'handlers': ['consola'], 'level': LOG_LEVEL, 'propagate': False},
        # Django: se conserva su comportamiento habitual, sin bajar a DEBUG el log de consultas
        # SQL (`django.db.backends`), que es ruidosísimo y se activa aparte cuando se lo necesita.
        'django': {'handlers': ['consola'], 'level': 'INFO', 'propagate': False},
        'django.db.backends': {'handlers': ['consola'], 'level': 'WARNING', 'propagate': False},
    },
}
