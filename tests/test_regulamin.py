"""Prawa przyjecia/regulamin.py (docstring modułu)."""
import json

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from przyjecia import regulamin
from przyjecia.models import AkceptacjaRegulaminu
from tests.conftest import czlonek

J = {"content_type": "application/json"}


@pytest.fixture(autouse=True)
def wymagany(settings):
    settings.REGULAMIN_WYMAGANY = True


@pytest.fixture
def szef(lokal):
    return czlonek(User.objects.create_user("szef", password="x" * 12), lokal, kierownik=True)


def test_bez_akceptacji_kierownik_trafia_na_regulamin_i_akceptuje(client, lokal, szef):
    client.force_login(szef)
    assert client.get("/przyjecia/")["Location"] == "/regulamin/akceptuj/"
    client.post("/regulamin/akceptuj/", json.dumps({"akceptuje": False}), **J)
    assert not AkceptacjaRegulaminu.objects.exists()  # bez zaznaczenia nic się nie zapisuje
    r = client.post("/regulamin/akceptuj/", json.dumps({"akceptuje": True}), **J, HTTP_X_FORWARDED_FOR="203.0.113.7")
    assert r.status_code == 302
    a = AkceptacjaRegulaminu.objects.get()
    assert (a.wersja, a.sha256, a.ip, a.user) == (regulamin.WERSJA, regulamin.skrot(), "203.0.113.7", szef)
    assert client.get("/przyjecia/").status_code == 200


def test_obsluga_nie_akceptuje_za_firme(client, lokal):
    ania = czlonek(User.objects.create_user("ania", password="x" * 12), lokal)
    client.force_login(ania)
    r = client.post("/regulamin/akceptuj/", json.dumps({"akceptuje": True}), **J, HTTP_X_INERTIA="true")
    assert r.json()["props"]["akceptacja"]["kierownik"] is False and not AkceptacjaRegulaminu.objects.exists()
    assert client.get("/przyjecia/")["Location"] == "/regulamin/akceptuj/"


def test_nowa_wersja_wymaga_ponownej_akceptacji(lokal, szef, monkeypatch):
    regulamin.zaakceptuj(lokal, szef, "127.0.0.1")
    assert regulamin.zaakceptowany(lokal)
    monkeypatch.setattr(regulamin, "WERSJA", "2099-01-01")
    assert not regulamin.zaakceptowany(lokal)


def test_demo_i_instalacja_klienta_bez_akceptacji(lokal, settings):
    lokal.demo_do = timezone.now()
    assert regulamin.zaakceptowany(lokal)
    lokal.demo_do = None
    settings.REGULAMIN_WYMAGANY = False
    assert regulamin.zaakceptowany(lokal)


def test_akceptacji_nie_da_sie_zmienic_ani_usunac(lokal, szef):
    a = regulamin.zaakceptuj(lokal, szef, None)
    a.wersja = "podrobiona"
    with pytest.raises(PermissionError):
        a.save()
    with pytest.raises(PermissionError):
        a.delete()
    lokal.delete()  # razem z lokalem znika (usunięcie danych po rozwiązaniu umowy)
    assert not AkceptacjaRegulaminu.objects.exists()


def test_regulamin_publiczny_z_ga_tylko_gdy_ustawione(client, db, settings):
    settings.GA_MEASUREMENT_ID = ""
    r = client.get("/regulamin/", HTTP_X_INERTIA="true").json()["props"]
    assert "§ 1. Usługodawca" in r["html"] and r["ga"] == ""
    settings.GA_MEASUREMENT_ID = "G-TEST12345"
    assert client.get("/regulamin/", HTTP_X_INERTIA="true").json()["props"]["ga"] == "G-TEST12345"


def test_panel_nigdy_nie_dostaje_ga(client, lokal, szef, settings):
    settings.GA_MEASUREMENT_ID = "G-TEST12345"
    regulamin.zaakceptuj(lokal, szef, None)
    client.force_login(szef)
    assert "G-TEST12345" not in client.get("/", HTTP_X_INERTIA="true").content.decode()
