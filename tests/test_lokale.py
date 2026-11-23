"""Wielofirmowość — prawa:
- pracownik lokalu A nie widzi, nie zmienia i nie usuwa niczego z lokalu B (404, dane nietknięte),
- konto bez lokalu nie wchodzi do panelu (wylogowanie + komunikat),
- firma z Konta = lokal: pierwsze logowanie go zakłada, kolejne nie dubluje; odebranie firmy w Koncie zabiera członkostwo,
- ta sama nazwa menu może być w dwóch lokalach.
"""
import json
from datetime import date, time

import pytest
from django.contrib.auth.models import User

from przyjecia import uslugi
from przyjecia.models import Czlonek, Lokal, Menu, Przyjecie
from tests.conftest import czlonek

PAKIET = json.loads((uslugi.KATALOG / "pakiety/sami-swoi/menu-1.json").read_text())


@pytest.fixture
def dwa(db):
    a, b = Lokal.objects.create(nazwa="A"), Lokal.objects.create(nazwa="B")
    menu_b = uslugi.wczytaj_pakiet(PAKIET, b)
    p_b = Przyjecie.objects.create(lokal=b, data=date(2026, 12, 5), start=time(14), klient="Tajny klient B",
                                   doroslych=10, menu=menu_b, cena_os=menu_b.cena_os)
    ania = czlonek(User.objects.create_user("ania", password="x" * 12), a, kierownik=True)
    bartek = czlonek(User.objects.create_user("bartek", password="x" * 12), b)
    return a, b, menu_b, p_b, ania, bartek


def test_obcy_lokal_niewidoczny_i_nietykalny(client, dwa):
    a, b, menu_b, p_b, ania, bartek = dwa
    client.force_login(ania)
    for url in (f"/przyjecia/{p_b.pk}/", f"/przyjecia/{p_b.pk}/edycja/", f"/przyjecia/{p_b.pk}/agenda.docx",
                f"/menu/{menu_b.pk}/", f"/zespol/{bartek.pk}/"):
        assert client.get(url).status_code == 404, url
    for url in (f"/przyjecia/{p_b.pk}/usun/", f"/menu/{menu_b.pk}/usun/", f"/zespol/{bartek.pk}/usun/"):
        assert client.post(url).status_code == 404, url
    r = client.get("/przyjecia/?m=2026-12", HTTP_X_INERTIA="true")
    assert "Tajny klient B" not in r.content.decode()
    assert Przyjecie.objects.filter(pk=p_b.pk).exists() and Menu.objects.filter(pk=menu_b.pk).exists()
    bartek.refresh_from_db()
    assert bartek.is_active


def test_formularz_nie_przyjmie_menu_obcego_lokalu(client, dwa):
    a, b, menu_b, p_b, ania, bartek = dwa
    client.force_login(ania)
    r = client.post("/przyjecia/nowe/", json.dumps({"data": "2026-12-06", "start": "14:00", "klient": "X",
                                                    "doroslych": 5, "menu": menu_b.pk, "status": "wstepna"}),
                    content_type="application/json", HTTP_X_INERTIA="true")
    assert "menu" in r.json()["props"]["bledy"] and not a.przyjecia.exists()


def test_konto_bez_lokalu_nie_wchodzi(client, db):
    client.force_login(User.objects.create_user("serwis", password="x" * 12))
    r = client.get("/przyjecia/")
    assert r.status_code == 302 and r["Location"] == "/logowanie/"
    assert "_auth_user_id" not in client.session


def test_ta_sama_nazwa_menu_w_dwoch_lokalach(dwa):
    a, b, *_ = dwa
    assert uslugi.wczytaj_pakiet(PAKIET, a) is not None
    _, bledy = uslugi.zapisz_menu({"nazwa": "Menu 1", "cena_os": "1", "etapy": [{"po_min": 0, "dzial": "sala",
                                                                                 "zadanie": "x"}]}, a)
    assert "nazwa" in bledy  # w obrębie jednego lokalu nadal unikalna


def firma(fid, rola="kierownik", nazwa="Firma"):
    return {"id": fid, "nazwa": nazwa, "rola": rola, "wlasciciel": False}


def test_firma_z_konta_zaklada_lokal_raz_i_zabiera_dostep(db):
    u = User.objects.create_user("k")
    uslugi.role_z_konta(u, [firma("f1", nazwa="Hotel Leśna"), firma("f2", "obsluga")])
    uslugi.role_z_konta(u, [firma("f1", nazwa="Hotel Leśna"), firma("f2", "obsluga")])
    assert Lokal.objects.count() == 2 and Lokal.objects.get(firma="f1").nazwa == "Hotel Leśna"
    assert Czlonek.objects.get(user=u, lokal__firma="f1").kierownik
    assert not Czlonek.objects.get(user=u, lokal__firma="f2").kierownik
    uslugi.role_z_konta(u, [firma("f1")])
    assert list(Czlonek.objects.filter(user=u).values_list("lokal__firma", flat=True)) == ["f1"]
    assert Lokal.objects.filter(firma="f2").exists()  # lokal zostaje — inni pracownicy i historia


def test_lokalne_czlonkostwo_nie_znika_przy_logowaniu_przez_konto(db):
    """Lokal bez firmy (np. demo, instalacja przed Kontem) — synchronizacja z Konta go nie rusza."""
    u = User.objects.create_user("k")
    stary = Lokal.objects.create(nazwa="Bez firmy")
    czlonek(u, stary)
    uslugi.role_z_konta(u, [firma("f1")])
    assert Czlonek.objects.filter(user=u, lokal=stary).exists()


# ---------- ustawienia lokalu ----------
KOLORY = {"glowny": "#3a3f44", "akcent": "A3172B", "tlo_naglowka": "#EEF0F1", "linia": "#A3AAB0"}


def png():
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "PNG")
    return SimpleUploadedFile("logo.png", buf.getvalue(), content_type="image/png")


def test_ustawienia_zapisuja_kolory_i_logo(client, dwa, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    a, *_, ania, _ = dwa
    client.force_login(ania)
    r = client.post("/ustawienia/", {"nazwa": "Gospoda A", "kontakt": "tel. 1", "sala": "", **KOLORY, "logo": png()})
    assert r.status_code == 302
    a.refresh_from_db()
    assert a.nazwa == "Gospoda A" and a.kolory["glowny"] == "3A3F44" and a.sala == "Sala" and a.logo
    assert client.get("/logo.png").status_code == 200
    client.post("/ustawienia/", {"nazwa": "Gospoda A", **KOLORY, "usun_logo": "1"})
    a.refresh_from_db()
    assert not a.logo


@pytest.mark.parametrize("zle,pole", [({"nazwa": " "}, "nazwa"), ({"glowny": "czerwony"}, "glowny"),
                                      ({"akcent": "#12345"}, "akcent")])
def test_ustawienia_odrzucaja_zle_dane(dwa, zle, pole):
    a = dwa[0]
    assert pole in uslugi.zapisz_lokal(a, {"nazwa": "X", **KOLORY, **zle})
    a.refresh_from_db()
    assert a.nazwa == "A"


def test_logo_nie_obrazek_i_demo_bez_plikow(dwa, settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile
    settings.MEDIA_ROOT = tmp_path
    a = dwa[0]
    assert "logo" in uslugi.zapisz_lokal(a, {"nazwa": "X", **KOLORY}, SimpleUploadedFile("x.png", b"<?php"))
    a.demo_do = "2099-01-01T00:00Z"
    assert "logo" in uslugi.zapisz_lokal(a, {"nazwa": "X", **KOLORY}, png())


def test_ustawienia_tylko_kierownik(client, dwa):
    *_, bartek = dwa
    client.force_login(bartek)
    assert client.post("/ustawienia/", {"nazwa": "Przejęte", **KOLORY}).status_code == 302
    assert not Lokal.objects.filter(nazwa="Przejęte").exists()
