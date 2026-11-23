"""wczytaj_menu (CMD Dockera, każdy start kontenera) — seed tylko do pustej bazy (#773).

Prawa:
- pusta baza (pierwsza instalacja) dostaje menu startowe,
- menu usunięte albo przemianowane przez klienta NIE wraca po restarcie,
- kolejne uruchomienia niczego nie dodają (idempotentne).
"""
import io

import pytest
from django.core.management import call_command

from przyjecia.models import Lokal, Menu


@pytest.fixture(autouse=True)
def jeden_lokal(settings, tmp_path):
    settings.KALENDARZ_LOKAL = "sami-swoi"
    settings.MEDIA_ROOT = tmp_path


def uruchom():
    out = io.StringIO()
    call_command("wczytaj_menu", stdout=out)
    return out.getvalue()


def test_pusta_baza_dostaje_menu_startowe(db):
    uruchom()
    assert Menu.objects.count() >= 1


def test_usuniete_menu_nie_wraca_po_restarcie(db):
    uruchom()
    nazwy = list(Menu.objects.values_list("nazwa", flat=True))
    Menu.objects.filter(nazwa=nazwy[0]).delete()
    uruchom()
    assert not Menu.objects.filter(nazwa=nazwy[0]).exists()


def test_przemianowane_menu_nie_wraca_pod_stara_nazwa(db):
    uruchom()
    m = Menu.objects.first()
    stara = m.nazwa
    m.nazwa = "Menu weselne Marcina"
    m.save()
    ile = Menu.objects.count()
    uruchom()
    assert not Menu.objects.filter(nazwa=stara).exists() and Menu.objects.count() == ile


def test_kolejne_uruchomienia_nic_nie_dodaja(db):
    uruchom()
    ile = Menu.objects.count()
    assert "pomijam" in uruchom()
    assert Menu.objects.count() == ile


def test_pierwszy_start_zaklada_lokal_z_pliku_z_logo(db):
    uruchom()
    lokal = Lokal.objects.get()
    assert lokal.nazwa == "Restauracja Sami Swoi" and lokal.logo and lokal.sala == "Sala bankietowa"
    assert set(Menu.objects.values_list("lokal", flat=True)) == {lokal.pk}


def test_wspolna_instancja_niczego_nie_zaklada(db, settings):
    settings.KALENDARZ_LOKAL = ""
    uruchom()
    assert not Lokal.objects.exists() and not Menu.objects.exists()
