from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# ====== Paths ======
BASE_DIR = Path(__file__).resolve().parent.parent

# ====== .env local (solo en tu PC) ======
load_dotenv(BASE_DIR / ".env")

# ====== Básicos ======
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-ganbaru-no-usar-en-prod")
DEBUG = os.environ.get("DEBUG", "1") == "1"

# Host de Render (cuando despliegas)
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

CSRF_TRUSTED_ORIGINS = [f"https://{RENDER_HOST}"] if RENDER_HOST else []

# ====== Apps ======
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "tienda",

    # Cloudinary (para media en la nube)
    "cloudinary",
    "cloudinary_storage",
]

# ====== Middleware ======
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # estáticos en prod
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "papeleria_ganbaru.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "papeleria_ganbaru.wsgi.application"

# ====== Base de datos ======
# Por defecto SQLite (dev local)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Si hay DATABASE_URL (Render), usar Postgres
# Si hay DATABASE_URL (Render o local), usar Postgres
if os.environ.get("DATABASE_URL"):
    url = os.environ["DATABASE_URL"]

    # ¿La URL apunta a tu máquina?
    is_local = ("localhost" in url) or ("127.0.0.1" in url)

    DATABASES["default"] = dj_database_url.config(
        default=url,
        conn_max_age=600,
        ssl_require=not is_local,   # ← True en Render, False en local
    )

# ====== Archivos estáticos ======
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ====== Media (Cloudinary o local) ======
# Si definiste Cloudinary en variables, úsalo. Si no, usa media local (para tu PC).
if os.getenv("CLOUDINARY_CLOUD_NAME"):
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
        "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
        "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
    }

    MEDIA_URL = "/media/"
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# ====== Seguridad detrás de proxy (Render) ======
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ====== Auth ======    
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ====== Email (dev) ======
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TIME_ZONE = "America/Santiago"
USE_TZ = True