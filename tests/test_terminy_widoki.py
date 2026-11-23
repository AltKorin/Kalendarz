"""Terminy kilkudniowe w panelu (wzór: Hotel Niedźwiadek) — formularz, miesiąc, wydruki, okres."""
import json
from datetime import date

import pymupdf
import pytest
from django.contrib.auth.models import User

from przyjecia import uslugi
from przyjecia.models import Przyjecie
from tests.conftest import czlonek

NOWY = "/przyjecia/nowe/"


def post(client, dane):
    return client.post(NOWY, json.dumps(dane), content_type="application/json", HTTP_X_INERTIA="true")


@pytest.fixture
def hotel(client, lokal):
    client.force_login(czlonek(User.objects.create_user("recepcja", password="x" * 12), lokal, kierownik=True))
    return lokal


def test_termin_bez_menu_z_opisem_osob(client, hotel):
    r = client.post(NOWY, json.dumps({"data": "2026-12-31", "koniec": "2027-01-03", "klient": "Sylwester",
                                      "rodzaj": "święta", "osoby_opis": "cały hotel (planujemy)", "status": "potwierdzona",
                                      "sale": "Restauracja Muzyczna"}), content_type="application/json")
    assert r.status_code == 302
    p = Przyjecie.objects.get()
    assert p.menu is None and p.start is None and p.ostatni_dzien == date(2027, 1, 3) and p.cena_os == 0


@pytest.mark.parametrize("dane,pole", [
    ({"data": "2026-12-04", "klient": "Mikołajki"}, "osoby_opis"),                      # ani liczby, ani opisu
    ({"data": "2026-12-06", "koniec": "2026-12-04", "klient": "X", "doroslych": 5}, "koniec"),  # wyjazd przed przyjazdem
    ({"data": "2026-12-04", "klient": "   ", "doroslych": 5}, "klient"),
])
def test_termin_odrzuca_zle_dane(client, hotel, dane, pole):
    r = post(client, {"status": "wstepna", **dane})
    assert pole in r.json()["props"]["bledy"] and not Przyjecie.objects.exists()


def test_przyjecie_z_menu_nadal_wymaga_godziny_i_doroslych(client, hotel):
    menu = uslugi.wczytaj_pakiet(json.loads((uslugi.KATALOG / "pakiety/sami-swoi/menu-1.json").read_text()), hotel)
    r = post(client, {"data": "2026-12-05", "klient": "Nowak", "menu": menu.pk, "status": "wstepna"})
    assert {"start", "doroslych"} <= set(r.json()["props"]["bledy"])


def test_termin_z_konca_miesiaca_widac_w_nastepnym(client, hotel):
    Przyjecie.objects.create(lokal=hotel, data=date(2026, 12, 31), koniec=date(2027, 1, 3), klient="Sylwester",
                             osoby_opis="cały hotel")
    r = client.get("/przyjecia/?m=2027-01", HTTP_X_INERTIA="true")
    assert [p["klient"] for p in r.json()["props"]["przyjecia"]] == ["Sylwester"]


def test_strona_terminow_pokazuje_nakladania_i_wolne_okna(client, hotel):
    Przyjecie.objects.create(lokal=hotel, data=date(2026, 12, 31), koniec=date(2027, 1, 3), klient="Sylwester",
                             osoby_opis="cały hotel")
    Przyjecie.objects.create(lokal=hotel, data=date(2027, 1, 2), koniec=date(2027, 1, 6), klient="Trzech Króli",
                             doroslych=40)
    Przyjecie.objects.create(lokal=hotel, data=date(2027, 1, 2), koniec=date(2027, 1, 6), klient="Odwołani",
                             doroslych=4, status="odwolana")
    r = client.get("/terminy/?od=2026-12-28&do=2027-01-10", HTTP_X_INERTIA="true")
    props = r.json()["props"]
    assert [(n["a"], n["b"]) for n in props["nakladania"]] == [("Sylwester", "Trzech Króli")]
    assert "Odwołani" not in json.dumps(props)


@pytest.mark.parametrize("widok,strony", [("lista", 1), ("kalendarz", 1), ("pelny", 2)])
def test_wydruki_pdf(client, hotel, widok, strony):
    Przyjecie.objects.create(lokal=hotel, data=date(2026, 11, 27), koniec=date(2026, 11, 29), klient="Andrzejki",
                             osoby_opis="ok. 90", rodzaj="pakiet hotelu")
    r = client.get(f"/terminy/{widok}.pdf?od=2026-11-23&do=2027-01-17")
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    doc = pymupdf.open(stream=r.content)
    assert len(doc) >= strony and "Andrzejki" in "".join(p.get_text() for p in doc)


def test_nieznany_wydruk_404(client, hotel):
    assert client.get("/terminy/cokolwiek.pdf").status_code == 404


@pytest.mark.parametrize("od,do", [("", ""), ("zle", "2026-13-40"), ("2026-12-31", "2026-01-01"),
                                   ("2026-01-01", "2030-01-01")])
def test_okres_zawsze_poprawny_i_ograniczony(od, do):
    a, b = uslugi.okres(od, do, date(2026, 11, 23))
    assert a <= b and (b - a).days < uslugi.MAX_TYGODNI * 7
