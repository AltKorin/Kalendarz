"""Rezerwacje stolików à la carte w panelu (#820): flaga, CRUD, kolizje, izolacja lokali."""
import json
from datetime import date, time, timedelta

import pytest
from django.contrib.auth.models import User

from przyjecia.models import Lokal, Rezerwacja, Stolik
from tests.conftest import czlonek

DZIEN = (date.today() + timedelta(days=3)).isoformat()


def post(client, url, dane):
    return client.post(url, json.dumps(dane), content_type="application/json", HTTP_X_INERTIA="true")


def props(r):
    return r.json()["props"]


@pytest.fixture
def sala(client, lokal, settings):
    settings.REZERWACJE_STOLIKOW = True
    client.force_login(czlonek(User.objects.create_user("kelner", password="x" * 12), lokal))
    return {n: Stolik.objects.create(lokal=lokal, numer=n, miejsc=m) for n, m in [("1", 2), ("5", 4), ("6", 4)]}


def nowa(client, **kw):
    return post(client, "/rezerwacje/nowa/", {"data": DZIEN, "od": "18:00", "klient": "Kowalski", "osoby": 4, **kw})


def test_flaga_wylaczona_to_404(client, lokal, settings):
    settings.REZERWACJE_STOLIKOW = False
    client.force_login(czlonek(User.objects.create_user("k", password="x" * 12), lokal))
    for url in ("/rezerwacje/", "/rezerwacje/nowa/", "/stoliki/"):
        assert client.get(url).status_code == 404
    assert client.get("/", HTTP_X_INERTIA="true").json()["props"]["rezerwacje_dzis"] is None


def test_nowa_rezerwacja_z_domyslnym_koncem_i_kilkoma_stolikami(client, sala, lokal):
    lokal.czas_rezerwacji = 150
    lokal.save()
    r = nowa(client, stoliki=[sala["5"].pk, sala["6"].pk], uwagi="urodziny")
    assert r.status_code == 302 and r["Location"] == f"/rezerwacje/?d={DZIEN}"
    rez = Rezerwacja.objects.get()
    assert (rez.od, rez.do, rez.lokal) == (time(18), time(20, 30), lokal)
    assert {s.numer for s in rez.stoliki.all()} == {"5", "6"}
    dzien = props(client.get(f"/rezerwacje/?d={DZIEN}", HTTP_X_INERTIA="true"))
    assert dzien["osob"] == 4 and dzien["rezerwacje"][0]["stoliki"] == ["5", "6"]
    assert {s["numer"]: s["zajety"] for s in dzien["stoliki"]}["5"] == ["18:00–20:30"]


def test_zajety_stolik_blokuje_a_styk_nie(client, sala):
    nowa(client, do="20:00", stoliki=[sala["5"].pk])
    r = nowa(client, od="19:00", klient="Nowak", stoliki=[sala["5"].pk, sala["1"].pk])
    assert "Stolik 5 zajęty 18:00–20:00 (Kowalski)" in props(r)["bledy"]["stoliki"]
    assert nowa(client, od="20:00", klient="Nowak", stoliki=[sala["5"].pk]).status_code == 302
    assert nowa(client, od="19:00", klient="Wiśniewski", stoliki=[sala["6"].pk]).status_code == 302


def test_odwolana_nie_zajmuje_stolika(client, sala):
    nowa(client, stoliki=[sala["5"].pk], status="odwolana")
    assert nowa(client, klient="Nowak", stoliki=[sala["5"].pk]).status_code == 302


def test_zmiana_wlasnej_rezerwacji_nie_koliduje_sama_ze_soba(client, sala):
    nowa(client, stoliki=[sala["5"].pk])
    rez = Rezerwacja.objects.get()
    r = post(client, f"/rezerwacje/{rez.pk}/", {"data": DZIEN, "od": "18:30", "do": "23:00", "klient": "Kowalski",
                                                "osoby": 9, "stoliki": [sala["5"].pk], "status": "potwierdzona"})
    assert r.status_code == 302
    rez.refresh_from_db()
    assert (rez.od, rez.do, rez.osoby) == (time(18, 30), time(23), 9)


@pytest.mark.parametrize("zmiana,pole", [
    ({"klient": "   "}, "klient"),
    ({"osoby": 0}, "osoby"),
    ({"osoby": ""}, "osoby"),
    ({"od": "20:00", "do": "19:00"}, "do"),
    ({"od": "20:00", "do": "20:00"}, "do"),
    ({"od": ""}, "od"),
    ({"data": "jutro"}, "data"),
])
def test_odrzuca_zle_dane(client, sala, zmiana, pole):
    r = nowa(client, **zmiana)
    assert pole in props(r)["bledy"]
    assert not Rezerwacja.objects.exists()


def test_cudzy_stolik_i_cudza_rezerwacja_niedostepne(client, sala):
    obcy = Lokal.objects.create(nazwa="Obcy")
    s_obcy = Stolik.objects.create(lokal=obcy, numer="9")
    r_obca = Rezerwacja.objects.create(lokal=obcy, data=DZIEN, od=time(18), do=time(20), klient="X", osoby=2)
    assert "stoliki" in props(nowa(client, stoliki=[s_obcy.pk]))["bledy"]
    assert client.get(f"/rezerwacje/{r_obca.pk}/").status_code == 404
    assert client.post(f"/rezerwacje/{r_obca.pk}/usun/").status_code == 404
    assert client.post(f"/stoliki/{s_obcy.pk}/usun/").status_code == 404
    assert post(client, "/stoliki/", {"id": s_obcy.pk, "numer": "10", "miejsc": 2}).status_code == 404


def test_usun_rezerwacje(client, sala):
    nowa(client)
    rez = Rezerwacja.objects.get()
    assert client.get(f"/rezerwacje/{rez.pk}/usun/").status_code == 405
    assert client.post(f"/rezerwacje/{rez.pk}/usun/").status_code == 302
    assert not Rezerwacja.objects.exists()


def test_stoliki_dodaj_zmien_usun(client, sala, lokal):
    post(client, "/stoliki/", {"numer": " 12 ", "miejsc": "6"})
    s = Stolik.objects.get(numer="12")
    assert s.miejsc == 6
    post(client, "/stoliki/", {"id": s.pk, "numer": "Ogród 1", "miejsc": 8})
    s.refresh_from_db()
    assert (s.numer, s.miejsc) == ("Ogród 1", 8)
    client.post(f"/stoliki/{s.pk}/usun/")
    assert not Stolik.objects.filter(pk=s.pk).exists()


@pytest.mark.parametrize("dane", [{"numer": "", "miejsc": 4}, {"numer": "  ", "miejsc": 4}, {"numer": "5", "miejsc": 4},
                                  {"numer": "7", "miejsc": 0}, {"numer": "7", "miejsc": "dużo"}, {"numer": "7", "miejsc": 100}])
def test_stolik_zle_dane_nic_nie_zapisuje(client, sala, dane):
    przed = Stolik.objects.count()
    r = post(client, "/stoliki/", dane)
    assert r.status_code == 302 and Stolik.objects.count() == przed
    assert props(client.get("/stoliki/", HTTP_X_INERTIA="true"))["komunikaty"][0]["poziom"] == "error"


def test_stolik_z_przyszla_rezerwacja_nie_do_usuniecia(client, sala):
    nowa(client, stoliki=[sala["5"].pk])
    client.post(f"/stoliki/{sala['5'].pk}/usun/")
    assert Stolik.objects.filter(pk=sala["5"].pk).exists()


def test_stolik_tylko_z_przeszla_rezerwacja_usuwa_sie_a_rezerwacja_zostaje(client, sala, lokal):
    rez = Rezerwacja.objects.create(lokal=lokal, data=date.today() - timedelta(days=1), od=time(18), do=time(20),
                                    klient="Dawny", osoby=2)
    rez.stoliki.add(sala["1"])
    client.post(f"/stoliki/{sala['1'].pk}/usun/")
    assert not Stolik.objects.filter(pk=sala["1"].pk).exists() and Rezerwacja.objects.filter(pk=rez.pk).exists()


@pytest.mark.parametrize("czas,ok", [(90, True), (15, True), (720, True), (10, False), (721, False), ("", False), ("x", False)])
def test_domyslny_czas_rezerwacji(client, sala, lokal, czas, ok):
    post(client, "/stoliki/", {"czas": czas})
    lokal.refresh_from_db()
    assert (lokal.czas_rezerwacji == czas) if ok else lokal.czas_rezerwacji == 120


def test_pulpit_pokazuje_rezerwacje_dzis(client, sala, lokal):
    for kto, status in [("A", "potwierdzona"), ("B", "odwolana")]:
        Rezerwacja.objects.create(lokal=lokal, data=date.today(), od=time(12), do=time(14), klient=kto, osoby=3,
                                  status=status)
    assert props(client.get("/", HTTP_X_INERTIA="true"))["rezerwacje_dzis"] == {"liczba": 1, "osob": 3, "sala": False}
