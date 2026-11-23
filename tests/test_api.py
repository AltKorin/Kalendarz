"""Prawa API serwer–serwer (przyjecia/api.py, #758) — Konto podmienione, bez sieci."""
import json
import time as czas
from datetime import date, time
from unittest import mock

import pytest
import requests
from django.core.cache import cache

from przyjecia import uslugi
from przyjecia.models import Lokal, Przyjecie

FIRMA = "d8c0be9a-361c-449c-8dbf-8903330cf6ec"
GRAFIK = "grafik-api-id"
URL = "/api/przyjecia"
OK = {"firma": FIRMA, "od": "2026-11-16", "do": "2026-11-22"}
AUTH = {"HTTP_AUTHORIZATION": "Bearer dobry"}


def odpowiedz_konta(**kw):
    d = {"active": True, "client_id": GRAFIK, "scope": "api", "exp": int(czas.time()) + 3600, **kw}
    return mock.Mock(status_code=200, json=lambda: d, raise_for_status=lambda: None)


@pytest.fixture
def api(settings, db):
    settings.API_KLIENCI = [GRAFIK]
    settings.OIDC_ISSUER = "https://konto.test/o"
    cache.clear()
    lokal = Lokal.objects.create(nazwa="Sami Swoi", firma=FIRMA)
    obcy = Lokal.objects.create(nazwa="Obcy", firma="inna-firma")
    menu = uslugi.wczytaj_pakiet(json.loads((uslugi.KATALOG / "pakiety/sami-swoi/menu-1.json").read_text()), lokal)
    obce_menu = uslugi.wczytaj_pakiet(json.loads((uslugi.KATALOG / "pakiety/sami-swoi/menu-1.json").read_text()), obcy)
    Przyjecie.objects.create(lokal=obcy, data=date(2026, 11, 21), start=time(12), klient="Obcy", doroslych=5,
                             menu=obce_menu, cena_os=1, rodzaj="stypa")
    for dzien, klient, status in [(21, "Nowak", "wstepna"), (22, "Kowalscy", "potwierdzona"), (22, "Odwołani", "odwolana"),
                                  (30, "Poza", "potwierdzona")]:
        Przyjecie.objects.create(lokal=lokal, data=date(2026, 11, dzien), start=time(13), klient=klient, doroslych=38, dzieci=2,
                                 menu=menu, cena_os=menu.cena_os, rodzaj="stypa", status=status)
    with mock.patch("przyjecia.api.requests.post", return_value=odpowiedz_konta()) as post:
        yield post


def test_zwraca_przyjecia_z_zakresu_bez_odwolanych_i_bez_klienta(client, api):
    r = client.get(URL, OK, **AUTH)
    assert r.status_code == 200
    p = r.json()["przyjecia"]
    assert [(x["data"], x["status"]) for x in p] == [("2026-11-21", "wstepna"), ("2026-11-22", "potwierdzona")]
    assert p[0] == {"id": p[0]["id"], "data": "2026-11-21", "koniec": "2026-11-21", "start": "13:00",
                    "rodzaj": "Stypa", "goscie": 40, "osoby_opis": "", "status": "wstepna"}
    assert "Nowak" not in r.content.decode()


def test_token_trzymany_w_cache(client, api):
    client.get(URL, OK, **AUTH)
    client.get(URL, OK, **AUTH)
    assert api.call_count == 1


@pytest.mark.parametrize("naglowek", [{}, {"HTTP_AUTHORIZATION": "Bearer "}, {"HTTP_AUTHORIZATION": "Basic abc"},
                                      {"HTTP_AUTHORIZATION": "dobry"}])
def test_bez_tokenu_401_bez_pytania_konta(client, api, naglowek):
    r = client.get(URL, OK, **naglowek)
    assert r.status_code == 401 and "przyjecia" not in r.json()
    api.assert_not_called()


@pytest.mark.parametrize("konto", [dict(active=False), dict(client_id="obcy"), dict(scope="openid"), dict(scope="")])
def test_niewazny_token_401(client, api, konto):
    api.return_value = odpowiedz_konta(**konto)
    assert client.get(URL, OK, **AUTH).status_code == 401


def test_konto_nie_odpowiada_503(client, api):
    api.side_effect = requests.Timeout()
    assert client.get(URL, OK, **AUTH).status_code == 503


def test_obca_firma_404(client, api):
    assert client.get(URL, {**OK, "firma": "inna"}, **AUTH).status_code == 404
    assert client.get(URL, {k: v for k, v in OK.items() if k != "firma"}, **AUTH).status_code == 404


@pytest.mark.parametrize("zakres", [{"od": "2026-11-22", "do": "2026-11-16"}, {"od": "2026-11-01", "do": "2027-01-02"},
                                    {"od": "jutro", "do": "2026-11-22"}, {"od": "", "do": ""}, {"od": "2026-11-16"}])
def test_zly_zakres_400(client, api, zakres):
    q = {"firma": FIRMA, **zakres}
    assert client.get(URL, q, **AUTH).status_code == 400


def test_granica_zakresu(client, api, settings):
    settings.API_MAX_DNI = 7
    assert client.get(URL, OK, **AUTH).status_code == 200  # 16–22 = 7 dni
    assert client.get(URL, {**OK, "do": "2026-11-23"}, **AUTH).status_code == 400


def test_bez_listy_klientow_endpointu_nie_ma(client, api, settings):
    settings.API_KLIENCI = []
    assert client.get(URL, OK, **AUTH).status_code == 404


def test_tylko_get(client, api):
    assert client.post(URL, OK, **AUTH).status_code == 405
