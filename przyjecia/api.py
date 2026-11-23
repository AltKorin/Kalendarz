"""API serwer–serwer: przyjęcia dla Grafiku (OpenProject #758). Kontrakt:

  GET /api/przyjecia?firma=<uuid z Konta>&od=RRRR-MM-DD&do=RRRR-MM-DD
  Authorization: Bearer <token aplikacji z Konta (client credentials, scope api)>
  → 200 {"przyjecia": [{id, data, start, rodzaj, goscie, status}]}

Prawa (tests/test_api.py):
- bez ważnego tokenu aplikacji = 401 i zero danych; ważny = aktywny w Konto (introspekcja), scope `api`,
  client_id z API_KLIENCI,
- firma bez lokalu w tej instalacji = 404 (i tak samo dla demo — piaskownice nie mają firmy),
- zakres: od <= do i najwyżej API_MAX_DNI dni, inaczej 400,
- Konto nie odpowiada = 503 (konsument pokazuje grafik bez przyjęć),
- bez API_KLIENCI endpointu nie ma (404, flaga).
"""
import hashlib
import time
from datetime import date

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET

from . import uslugi
from .models import Lokal


def _blad(tekst, status, **kw):
    return JsonResponse({"blad": tekst}, status=status, **kw)


def klient_tokenu(naglowek):
    """client_id aplikacji z nagłówka Authorization albo None. Wyjątek requests/ValueError = Konto nie odpowiada."""
    token = naglowek[7:].strip() if naglowek.startswith("Bearer ") else ""
    if not token:
        return None
    klucz = "api-token:" + hashlib.sha256(token.encode()).hexdigest()
    if cid := cache.get(klucz):
        return cid
    r = requests.post(settings.OIDC_ISSUER + "/introspect/", data={"token": token},
                      auth=(settings.OIDC_CLIENT_ID, settings.OIDC_CLIENT_SECRET), timeout=5)
    r.raise_for_status()
    i = r.json()
    if not (i.get("active") and i.get("client_id") in settings.API_KLIENCI and "api" in str(i.get("scope", "")).split()):
        return None
    # ponytail: cache w pamięci procesu (każdy worker pyta Konto osobno) — wspólny cache dopiero przy realnym ruchu
    cache.set(klucz, i["client_id"], max(1, min(300, int(i.get("exp", 0)) - int(time.time()))))
    return i["client_id"]


@require_GET
def przyjecia(request):
    if not (settings.API_KLIENCI and settings.OIDC_ISSUER):
        raise Http404
    try:
        klient = klient_tokenu(request.headers.get("Authorization", ""))
    except (requests.RequestException, ValueError):
        return _blad("Konto sudomie nie odpowiada — spróbuj później", 503)
    if not klient:
        return _blad("Brak ważnego tokenu aplikacji", 401, headers={"WWW-Authenticate": "Bearer"})
    lokal = Lokal.objects.filter(firma=request.GET.get("firma") or None).first() if request.GET.get("firma") else None
    if not lokal:
        return _blad("Ta instalacja nie obsługuje tej firmy", 404)
    try:
        od, do = date.fromisoformat(request.GET["od"]), date.fromisoformat(request.GET["do"])
    except (KeyError, ValueError):
        return _blad("Podaj od i do jako RRRR-MM-DD", 400)
    if do < od or (do - od).days >= settings.API_MAX_DNI:
        return _blad(f"Zakres: od ≤ do, najwyżej {settings.API_MAX_DNI} dni", 400)
    return JsonResponse({"przyjecia": uslugi.przyjecia_w_zakresie(lokal, od, do)})
