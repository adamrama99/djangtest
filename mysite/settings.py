"""
Django settings for mysite project.
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env(key: str, default=None):
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    value = env(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default=None):
    value = env(key)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_database_url(database_url: str):
    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()
    engine_map = {
        "postgres": "django.db.backends.postgresql",
        "postgresql": "django.db.backends.postgresql",
        "pgsql": "django.db.backends.postgresql",
        "sqlite": "django.db.backends.sqlite3",
        "mysql": "django.db.backends.mysql",
    }

    if scheme not in engine_map:
        raise ValueError(
            "DATABASE_URL memakai skema yang tidak didukung. "
            "Gunakan sqlite, postgres/postgresql, atau mysql."
        )

    if scheme == "sqlite":
        raw_path = unquote(parsed.path or "")
        if not raw_path or raw_path == "/":
            db_path = BASE_DIR / "db.sqlite3"
        elif raw_path == "/:memory:":
            db_path = ":memory:"
        else:
            relative_path = raw_path.lstrip("/")
            db_path = Path(relative_path)
            if not db_path.is_absolute():
                db_path = BASE_DIR / db_path
        return {
            "ENGINE": engine_map[scheme],
            "NAME": str(db_path),
        }

    return {
        "ENGINE": engine_map[scheme],
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


load_env_file(ENV_FILE)


SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    "django-insecure-portable-default-key-change-this-on-public-production",
)

DEBUG = env_bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = ["its-request.mingpromo.com", "media-track.mingpromo.com", "127.0.0.1", "localhost", "103.102.153.146"]

CSRF_TRUSTED_ORIGINS = ["http://its-request.mingpromo.com", "https://its-request.mingpromo.com", "http://media-track.mingpromo.com", "https://media-track.mingpromo.com"]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "products",
]

MIDDLEWARE = [       # Backend Laravel Anda
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mysite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mysite.wsgi.application"
ASGI_APPLICATION = "mysite.asgi.application"


database_url = env("DATABASE_URL")
if database_url:
    DATABASES = {"default": parse_database_url(database_url)}
else:
    db_engine = env("DB_ENGINE", "django.db.backends.sqlite3")
    if db_engine == "django.db.backends.sqlite3":
        DATABASES = {
            "default": {
                "ENGINE": db_engine,
                "NAME": env("DB_NAME", str(BASE_DIR / "db.sqlite3")),
            }
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": db_engine,
                "NAME": env("DB_NAME", "djangtest"),
                "USER": env("DB_USER", ""),
                "PASSWORD": env("DB_PASSWORD", ""),
                "HOST": env("DB_HOST", "localhost"),
                "PORT": env("DB_PORT", ""),
            }
        }


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = [
    'backends.EmailBackend',
]

# settings.py
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptPasswordHasher',        # Untuk bcrypt dari Laravel ($2y$)
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',        # Untuk password baru Django
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

SERVE_STATIC_FILES = env_bool("DJANGO_SERVE_STATIC", default=True)
SERVE_MEDIA_FILES = env_bool("DJANGO_SERVE_MEDIA", default=True)

STATIC_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
