"""Rzut sali (#821): układ stolików, kształt, podpowiedź z kliknięcia w wolny stolik, flaga, izolacja lokali."""
import json

import pytest
from django.contrib.auth.models import User

from przyjecia.models import Lokal, Stolik
from tests.conftest import czlonek


def post(client, url, dane):
    return client.post(url, json.dumps(dane), content_type="application/json", HTTP_X_INERTIA="true")


def props(r):
    return r.json()["props"]


def komunikat(client):
    return props(client.get("/stoliki/", HTTP_X_INERTIA="true"))["komunikaty"][0]


@pytest.fixture
def sala(client, lokal, settings):
    settings.REZERWACJE_STOLIKOW = settings.RZUT_SALI = True
    client.force_login(czlonek(User.objects.create_user("kelner", password="x" * 12), lokal))
    return [Stolik.objects.create(lokal=lokal, numer=n, miejsc=4) for n in ("1", "2", "3")]


def test_zapis_ukladu_i_zdjecie_z_rzutu(client, sala):
    a, b, c = sala
    c.x, c.y = 100, 100
    c.save()
    post(client, "/stoliki/", {"uklad": [{"id": a.pk, "x": 0, "y": 1000}, {"id": b.pk, "x": 500, "y": 250},
                                         {"id": c.pk, "x": None, "y": None}]})
    assert komunikat(client)["poziom"] == "success"
    assert [(s.x, s.y) for s in Stolik.objects.order_by("numer")] == [(0, 1000), (500, 250), (None, None)]
    widok = props(client.get("/rezerwacje/", HTTP_X_INERTIA="true"))
    assert widok["rzut"] is True and {s["numer"]: (s["x"], s["y"]) for s in widok["stoliki"]}["2"] == (500, 250)


@pytest.mark.parametrize("zly", [
    lambda s: {"uklad": "nie lista"},
    lambda s: {"uklad": [{"id": s.pk, "x": 1001, "y": 10}]},
    lambda s: {"uklad": [{"id": s.pk, "x": -1, "y": 10}]},
    lambda s: {"uklad": [{"id": s.pk, "x": 10, "y": None}]},
    lambda s: {"uklad": [{"id": s.pk, "x": "lewo", "y": 10}]},
    lambda s: {"uklad": [{"x": 10, "y": 10}]},
    lambda s: {"uklad": [{"id": 999999, "x": 10, "y": 10}]},
])
def test_zly_uklad_nic_nie_zapisuje(client, sala, zly):
    a = sala[0]
    post(client, "/stoliki/", {"uklad": [{"id": sala[1].pk, "x": 5, "y": 5}, *zly(a)["uklad"]]}
         if isinstance(zly(a)["uklad"], list) else zly(a))
    assert komunikat(client)["poziom"] == "error"
    assert not Stolik.objects.filter(x__isnull=False).exists()  # wszystko albo nic


def test_cudzego_stolika_nie_da_sie_ulozyc(client, sala):
    obcy = Stolik.objects.create(lokal=Lokal.objects.create(nazwa="Obcy"), numer="9")
    post(client, "/stoliki/", {"uklad": [{"id": obcy.pk, "x": 10, "y": 10}]})
    obcy.refresh_from_db()
    assert obcy.x is None and komunikat(client)["poziom"] == "error"


def test_rzut_wylaczony_flaga(client, sala, settings):
    settings.RZUT_SALI = False
    assert post(client, "/stoliki/", {"uklad": [{"id": sala[0].pk, "x": 10, "y": 10}]}).status_code == 404
    assert props(client.get("/stoliki/", HTTP_X_INERTIA="true"))["rzut"] is False
    assert not Stolik.objects.filter(x__isnull=False).exists()


@pytest.mark.parametrize("ksztalt,ok", [("okragly", True), ("prostokatny", True), ("trojkat", False), ("", True)])
def test_ksztalt_stolika(client, sala, ksztalt, ok):
    a = sala[0]
    post(client, "/stoliki/", {"id": a.pk, "numer": "1", "miejsc": 4, "ksztalt": ksztalt})
    a.refresh_from_db()
    assert a.ksztalt == ((ksztalt or "prostokatny") if ok else "prostokatny")


def test_klik_w_wolny_stolik_podpowiada_godzine_i_stolik(client, sala):
    r = props(client.get(f"/rezerwacje/nowa/?d=2026-12-05&od=19:30&stolik={sala[1].pk}", HTTP_X_INERTIA="true"))
    assert (r["rezerwacja"]["data"], r["rezerwacja"]["od"], r["rezerwacja"]["stoliki"]) == ("2026-12-05", "19:30", [sala[1].pk])


@pytest.mark.parametrize("zapytanie", ["od=25:00&stolik=abc", "od=19&stolik=999999", "od=<script>&stolik=-1", ""])
def test_zla_podpowiedz_daje_domyslne(client, sala, zapytanie):
    r = props(client.get(f"/rezerwacje/nowa/?{zapytanie}", HTTP_X_INERTIA="true"))["rezerwacja"]
    assert (r["od"], r["stoliki"]) == ("18:00", [])


def test_podpowiedz_nie_wpuszcza_cudzego_stolika(client, sala):
    obcy = Stolik.objects.create(lokal=Lokal.objects.create(nazwa="Obcy"), numer="9")
    assert props(client.get(f"/rezerwacje/nowa/?stolik={obcy.pk}", HTTP_X_INERTIA="true"))["rezerwacja"]["stoliki"] == []
