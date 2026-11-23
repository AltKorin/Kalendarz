"""Demo bez logowania (wzór: HotelAgenda `agenda/demo.py`, fc `apps/core/demo.py`).

„Wypróbuj demo” = własny lokal odwiedzającego, zbudowany względem dzisiejszej daty z `dane/demo.json` (restauracja
albo hotel), konto bez hasła (wchodzi tylko ta sesja), skasowane po DEMO_HOURS. Wygasłe sprząta start kolejnego demo.

Prawa (tests/test_demo.py):
- DEMO_MAX = 0 → demo nie istnieje (404), żadnych kont ani lokali,
- najwyżej DEMO_MAX piaskownic naraz i DEMO_PER_HOUR startów z jednego IP — ponad limit odmowa, nie kolejka,
- wygasła piaskownica znika razem z kontem; lokale klientów (bez demo_do) nigdy nie są ruszane,
- piaskownica nie ma firmy z Konta (API i logowanie przez Konto jej nie widzą).
"""
import json
import secrets
from datetime import time, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from . import uslugi
from .models import Czlonek, Lokal

DANE = Path(__file__).parent / "dane" / "demo.json"


class DemoNiedostepne(Exception):
    pass


def warianty():
    d = json.loads(DANE.read_text(encoding="utf-8"))
    return {k: {"przycisk": v["przycisk"], "opis": v["opis"]} for k, v in d.items() if not k.startswith("_")}


def _czas(s):
    return time.fromisoformat(s) if s else None


def zbuduj(wariant, user, demo_do):
    """Lokal demo z danymi względem dziś. Zwraca lokal."""
    d = json.loads(DANE.read_text(encoding="utf-8"))[wariant]
    lokal = Lokal.objects.create(**d["lokal"], demo_do=demo_do)
    Czlonek.objects.create(user=user, lokal=lokal, kierownik=True)
    for pakiet in d["pakiety"]:
        uslugi.wczytaj_pakiet(json.loads((uslugi.KATALOG / "pakiety" / f"{pakiet}.json").read_text(encoding="utf-8")),
                              lokal)
    menu = {m.nazwa: m for m in lokal.menu.all()}
    dzis = timezone.localdate()
    piatek = dzis + timedelta(days=(4 - dzis.weekday()) % 7)  # weekendowe imprezy mają wypadać w weekend
    for p in d["przyjecia"]:
        p = dict(p)
        data = (dzis if p.pop("od_dzis", False) else piatek) + timedelta(days=p.pop("dni"))
        noce = p.pop("noce", 0)
        m = menu.get(p.pop("menu", None))
        lokal.przyjecia.create(
            data=data, koniec=data + timedelta(days=noce) if noce else None, start=_czas(p.pop("start", None)),
            tort=_czas(p.pop("tort", None)), menu=m, cena_os=m.cena_os if m else 0,
            cena_dziecko=m.cena_dziecko if m else None, **p)
    return lokal


def sprzatnij():
    """Wygasłe piaskownice razem z kontami (nigdy nie były czyjeś)."""
    for lokal in Lokal.objects.filter(demo_do__lt=timezone.now()):
        konta = list(User.objects.filter(czlonkostwa__lokal=lokal, username__startswith="demo-"))
        lokal.przyjecia.all().delete()  # Przyjecie.menu = PROTECT — najpierw przyjęcia, potem lokal z menu
        lokal.delete()
        for u in konta:
            u.delete()


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return xff.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")


def start(request, wariant):
    if settings.DEMO_MAX <= 0 or wariant not in warianty():
        raise DemoNiedostepne(None)
    sprzatnij()
    klucz = f"demo-ip:{_ip(request)}"
    if cache.get(klucz, 0) >= settings.DEMO_PER_HOUR:
        raise DemoNiedostepne("Za dużo uruchomień demo z tego adresu — spróbuj za godzinę.")
    with transaction.atomic():
        if Lokal.objects.filter(demo_do__isnull=False).count() >= settings.DEMO_MAX:
            raise DemoNiedostepne("Demo jest teraz oblegane — spróbuj za kilka minut.")  # backpressure, nie kolejka
        user = User(username=f"demo-{secrets.token_hex(4)}", first_name="Gość demo")
        user.set_unusable_password()
        user.save()
        lokal = zbuduj(wariant, user, timezone.now() + timedelta(hours=settings.DEMO_HOURS))
    cache.set(klucz, cache.get(klucz, 0) + 1, 3600)  # ponytail: licznik w pamięci procesu — wspólny cache przy ruchu
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return lokal
