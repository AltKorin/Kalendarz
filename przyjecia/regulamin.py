"""Regulamin Kalendarza (dane/regulamin.html) i dowód jego akceptacji.

Prawa (tests/test_regulamin.py):
- lokal bez akceptacji BIEŻĄCEJ wersji nie pracuje w panelu (kierownik → ekran akceptacji, obsługa → komunikat),
- demo i instalacja klienta (REGULAMIN_WYMAGANY=0) nie wymagają akceptacji,
- akceptacja zapisuje wersję i sha256 dokładnie pokazanego tekstu, IP i osobę; nie da się jej zmienić ani usunąć,
- nowa wersja regulaminu = ponowna akceptacja (stara nie wystarcza).
"""
import hashlib
from functools import cache
from pathlib import Path

from django.conf import settings

from .models import AkceptacjaRegulaminu

PLIK = Path(__file__).parent / "dane" / "regulamin.html"
WERSJA = "2026-11-23"  # zmiana treści = nowa wersja + e-mail do właścicieli 14 dni wcześniej (§ 12)


@cache
def tresc():
    return PLIK.read_text(encoding="utf-8")


def skrot():
    return hashlib.sha256(tresc().encode()).hexdigest()


def wymagany(lokal):
    return bool(settings.REGULAMIN_WYMAGANY and lokal and not lokal.demo_do)


def zaakceptowany(lokal):
    return not wymagany(lokal) or lokal.akceptacje.filter(wersja=WERSJA).exists()


def zaakceptuj(lokal, user, ip):
    return AkceptacjaRegulaminu.objects.create(lokal=lokal, user=user, wersja=WERSJA, sha256=skrot(), ip=ip or None)
