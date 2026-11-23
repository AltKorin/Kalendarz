"""Prawa demo (docstring przyjecia/demo.py)."""
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

from przyjecia import demo, uslugi
from przyjecia.models import Lokal, Przyjecie


@pytest.fixture(autouse=True)
def wlaczone(settings):
    settings.DEMO_MAX, settings.DEMO_HOURS, settings.DEMO_PER_HOUR = 3, 24, 50
    settings.KALENDARZ_PUBLICZNY = True
    cache.clear()


@pytest.mark.parametrize("wariant", ["restauracja", "hotel"])
def test_demo_buduje_lokal_i_loguje(client, db, wariant):
    r = client.post(f"/demo/{wariant}/")
    assert r.status_code == 302
    lokal = Lokal.objects.get()
    assert lokal.demo_do and lokal.firma is None and lokal.przyjecia.count() >= 5
    assert client.get("/przyjecia/").status_code == 200
    # plan obsługi i wydruki działają na danych demo
    z_menu = lokal.przyjecia.filter(menu__isnull=False).first()
    assert uslugi.dane_przyjecia(z_menu)["obowiazki"]
    assert client.get("/terminy/pelny.pdf").status_code == 200


def test_hotel_demo_pokazuje_kolizje(client, db):
    client.post("/demo/hotel/")
    lokal = Lokal.objects.get()
    od = timezone.localdate()
    assert uslugi.przeglad_terminow(lokal, od, od + timedelta(days=60), od)["nakladania"]


def test_wylaczone_demo_nie_istnieje(client, db, settings):
    settings.DEMO_MAX = 0
    assert client.post("/demo/hotel/").status_code == 404
    assert not Lokal.objects.exists() and not User.objects.exists()


def test_nieznany_wariant_404(client, db):
    assert client.post("/demo/kasyno/").status_code == 404
    assert client.get("/demo/hotel/").status_code == 405


def test_limit_naraz_to_odmowa(client, db, settings):
    settings.DEMO_MAX = 1
    client.post("/demo/hotel/")
    client.logout()
    client.post("/demo/hotel/")
    assert Lokal.objects.count() == 1


def test_limit_na_ip(client, db, settings):
    settings.DEMO_PER_HOUR = 1
    client.post("/demo/hotel/")
    client.post("/demo/restauracja/")
    assert Lokal.objects.count() == 1


def test_wygasle_znika_z_kontem_a_klient_zostaje(client, db):
    klient = Lokal.objects.create(nazwa="Prawdziwy klient")
    client.post("/demo/restauracja/")
    stare = Lokal.objects.get(demo_do__isnull=False)
    stare.demo_do = timezone.now() - timedelta(minutes=1)
    stare.save()
    demo.sprzatnij()
    assert list(Lokal.objects.all()) == [klient]
    assert not User.objects.filter(username__startswith="demo-").exists()
    assert not Przyjecie.objects.exists()


def test_w_demo_nie_zaklada_sie_kont(client, db):
    client.post("/demo/restauracja/")
    client.post("/zespol/nowe/", {"login": "intruz", "haslo": "dlugie-haslo-123"}, content_type="application/json")
    assert not User.objects.filter(username="intruz").exists()


def test_strona_publiczna_tylko_gdy_wlaczona(client, db, settings):
    r = client.get("/", HTTP_X_INERTIA="true")
    assert r.json()["component"] == "Start" and {d["id"] for d in r.json()["props"]["demo"]} == {"restauracja", "hotel"}
    settings.KALENDARZ_PUBLICZNY = False
    assert client.get("/")["Location"] == "/logowanie/"
