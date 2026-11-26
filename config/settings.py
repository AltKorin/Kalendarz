"""Panel Kalendarza przyjęć. Konfiguracja z .env (Docker na Proxmoksie), nie z kodu."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(nazwa, domyslnie=""):
    return os.environ.get(nazwa, domyslnie)


DEBUG = env("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-tylko-lokalnie-nie-na-produkcje")
if not DEBUG and SECRET_KEY.startswith("dev-"):
    raise RuntimeError("Ustaw DJANGO_SECRET_KEY w .env produkcji.")
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [h for h in env("DJANGO_CSRF_TRUSTED_ORIGINS").split(",") if h]

# Instalacja jednego lokalu (samiswoi): lokale/<id>.json + pakiety/<id>/ — z nich powstaje lokal przy pierwszym
# starcie (wczytaj_menu). Wspólna instancja (kalendarz.sudomie.pl): puste — lokale zakłada logowanie przez Konto.
KALENDARZ_LOKAL = env("KALENDARZ_LOKAL")
# Strona publiczna z opisem i demo zamiast ekranu logowania (wspólna instancja). Instalacja klienta: 0.
KALENDARZ_PUBLICZNY = env("KALENDARZ_PUBLICZNY", "0") == "1"
KONTO_URL = env("KONTO_URL", "https://konto.sudomie.pl")
# Demo bez logowania (wzór: agenda/fc). 0 = przycisku nie ma. Limit naraz, czas życia, limit startów na IP/godz.
DEMO_MAX = int(env("DEMO_MAX", "0"))
DEMO_HOURS = int(env("DEMO_HOURS", "24"))
DEMO_PER_HOUR = int(env("DEMO_PER_HOUR", "20"))
# GA4 tylko na stronach publicznych (strona startowa, regulamin), Consent Mode v2 — jak agenda/fc. Puste = brak tagu.
GA_MEASUREMENT_ID = env("GA_MEASUREMENT_ID").strip()
if GA_MEASUREMENT_ID and not __import__("re").fullmatch(r"G-[A-Z0-9]{4,20}", GA_MEASUREMENT_ID):
    raise RuntimeError("GA_MEASUREMENT_ID musi wyglądać jak G-XXXXXXXXXX")
# Akceptacja regulaminu przez kierownika lokalu przed pracą w panelu (wspólna instancja). Instalacja klienta: umowa osobno.
# Rezerwacje stolików à la carte (#820). Feature flag: 0 = nie ma w menu, adresy dają 404.
REZERWACJE_STOLIKOW = env("REZERWACJE_STOLIKOW", "0") == "1"
REGULAMIN_WYMAGANY = env("REGULAMIN_WYMAGANY", "1" if KALENDARZ_PUBLICZNY else "0") == "1"

INSTALLED_APPS = [
    "jazzmin",  # MUSI być przed django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simple_history",
    "django_vite",
    "inertia",
    "core_audit",
    "core_sso",  # logowanie kontem sudomie (agency-platform-core)
    "przyjecia",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",  # PO AuthenticationMiddleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "inertia.middleware.InertiaMiddleware",
    "przyjecia.middleware.WspolneDaneMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": Path(env("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3"))),
}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
LOGIN_URL = "/logowanie/"

LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "dist"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))  # logo lokali; na produkcji wolumen /data
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # import Excela

# Inertia + Vite
INERTIA_LAYOUT = "base.html"
DJANGO_VITE = {"default": {
    "dev_mode": env("VITE_DEV", "1" if DEBUG else "0") == "1",
    "dev_server_port": 5173,
    "manifest_path": BASE_DIR / "frontend" / "dist" / "manifest.json",
}}
# axios w Inertii wysyła token z ciasteczka XSRF-TOKEN w nagłówku X-XSRF-TOKEN (CLAUDE.md)
CSRF_COOKIE_NAME = "XSRF-TOKEN"
# własna nazwa: inne produkty (Grafik…) na tym samym hoście/domenie nie nadpiszą sesji (zgubiony state OIDC)
SESSION_COOKIE_NAME = "kalendarz_sesja"
CSRF_HEADER_NAME = "HTTP_X_XSRF_TOKEN"

# Za nginx + Cloudflare Tunnel: oba ustawienia razem albo żadne (pętla przekierowań — CLAUDE.md)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env("DJANGO_SSL_REDIRECT", "1") == "1"
    # healthcheck Dockera pyta http://localhost:8000/zdrowie/ — port wystawiony tylko na 127.0.0.1
    SECURE_REDIRECT_EXEMPT = [r"^zdrowie/$"]
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, "localhost"]
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True

JAZZMIN_SETTINGS = {
    "site_title": "Kalendarz — serwis",
    "site_header": "Kalendarz przyjęć",
    "site_brand": "Kalendarz (serwis)",
    "welcome_sign": "Panel serwisowy — klient pracuje w panelu /",
}

LOGGING = {"version": 1, "handlers": {"console": {"class": "logging.StreamHandler"}},
           "root": {"handlers": ["console"], "level": "INFO"}}

# Logowanie przez Konto sudomie (OpenProject #757, https://konto.sudomie.pl/o) — ogólny klient OIDC;
# zmiana dostawcy = zmiana tych zmiennych, bez zmian w kodzie.
# Puste OIDC_ISSUER = przycisku „Zaloguj przez …” nie ma (flaga).
OIDC_ISSUER = env("OIDC_ISSUER").rstrip("/")
OIDC_DISCOVERY_URL = env("OIDC_DISCOVERY_URL") or (OIDC_ISSUER + "/.well-known/openid-configuration/" if OIDC_ISSUER else "")
OIDC_CLIENT_ID = env("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = env("OIDC_CLIENT_SECRET")
OIDC_NAZWA = env("OIDC_NAZWA", "Konto sudomie")  # napis na przycisku: „Zaloguj przez …”
# Którą firmę u dostawcy obsługuje ta instalacja (claim "firmy": [{"id", "nazwa", "rola"}]).
KALENDARZ_FIRMA = env("KALENDARZ_FIRMA")
# core_sso: Kalendarz to produkt jednofirmowy (jedna instalacja = jeden lokal), role nadaje przyjecia.uslugi.role_z_konta
# API serwer–serwer (#758): client_id klientów API z Konta (manage.py klient_api …), po przecinku.
# Puste = endpointu /api/przyjecia nie ma (flaga). Token sprawdzamy introspekcją w Koncie (OIDC_* wyżej).
API_KLIENCI = [c for c in env("API_KLIENCI").split(",") if c]
API_MAX_DNI = int(env("API_MAX_DNI", "62"))  # backpressure: najdłuższy zakres jednego zapytania
SSO_PRODUKT = "kalendarz"
SSO_FIRMA = KALENDARZ_FIRMA
SSO_PO_ZALOGOWANIU = "przyjecia.uslugi.role_z_konta"
SSO_KOMUNIKATY = {
    "brak_firmy": "Twoje konto nie należy do tej restauracji. Poproś właściciela o zaproszenie w Koncie sudomie.",
    "brak_dostepu": "Nie masz dostępu do Kalendarza w tej restauracji. Poproś właściciela o dostęp w Koncie sudomie.",
    "wylaczone": "Twoje konto w kalendarzu jest wyłączone. Skontaktuj się z kierownikiem.",
}
