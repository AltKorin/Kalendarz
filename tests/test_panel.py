"""Prawa serwisów panelu (przyjecia/uslugi.py) + bramki widoków."""
import json
from datetime import date, time
from decimal import Decimal
from io import BytesIO

import pytest
from django.contrib.auth.models import User
from hypothesis import given, settings as hsettings, strategies as st
from hypothesis.extra.django import TestCase as HTestCase
from openpyxl import Workbook

import kalendarz as k
from core_audit.models import LoginEvent
from przyjecia import uslugi
from przyjecia.models import Lokal, Menu, Przyjecie
from tests.conftest import czlonek


def menu_1(lokal=None):
    lokal = lokal or Lokal.objects.first() or Lokal.objects.create(nazwa="Restauracja Testowa")
    return uslugi.wczytaj_pakiet(json.loads((uslugi.KATALOG / "pakiety/demo/menu-1.json").read_text()), lokal)


def przyjecie(menu, **kw):
    d = dict(lokal=menu.lokal, data=date(2026, 11, 22), start=time(14), klient="Kowalscy", doroslych=38, dzieci=6, menu=menu,
             cena_os=menu.cena_os, zadatek=Decimal(1000), rodzaj="komunia", tort=time(17, 30))
    d.update(kw)
    return Przyjecie.objects.create(**d)


class PrawaPrzyjecia(HTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.menu = menu_1()

    @hsettings(max_examples=40, deadline=None)
    @given(st.integers(1, 150), st.integers(0, 40), st.times(), st.decimals(0, 5000, places=2))
    def test_dane_z_panelu_zawsze_poprawne_i_wycena_zgodna(self, dorosli, dzieci, start, zadatek):
        p = przyjecie(self.menu, doroslych=dorosli, dzieci=dzieci, start=start.replace(microsecond=0, second=0),
                      zadatek=zadatek, klient=f"K{dorosli}-{dzieci}-{start}")
        dane = uslugi.dane_przyjecia(p)
        assert k.sprawdz(dane) == []
        w = uslugi.wycena(p)
        assert w["razem"] == (self.menu.cena_os * dorosli).quantize(Decimal("0.01"))
        assert w["do_zaplaty"] == max(w["razem"] - zadatek, 0)


@pytest.mark.django_db
def test_dokumenty_docx_generuja_sie():
    p = przyjecie(menu_1())
    for rodzaj in ("agenda", "plan"):
        tresc, nazwa = uslugi.dokument(p, rodzaj)
        assert tresc[:2] == b"PK" and nazwa.endswith(".docx")


@pytest.mark.django_db
def test_menu_w_uzyciu_nie_do_usuniecia():
    m = menu_1()
    przyjecie(m)
    assert "nie można go usunąć" in uslugi.usun_menu(m)
    assert Menu.objects.filter(pk=m.pk).exists()


@pytest.mark.django_db
def test_seed_menu_idempotentny():
    menu_1()
    assert uslugi.wczytaj_pakiet(json.loads((uslugi.KATALOG / "pakiety/demo/menu-1.json").read_text()),
                                 Lokal.objects.get()) is None
    assert Menu.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("dane,pole", [
    ({"nazwa": "", "cena_os": "10", "etapy": [{"po_min": 0, "dzial": "sala", "zadanie": "x"}]}, "nazwa"),
    ({"nazwa": "A", "cena_os": "-5", "etapy": [{"po_min": 0, "dzial": "sala", "zadanie": "x"}]}, "cena_os"),
    ({"nazwa": "A", "cena_os": "abc", "etapy": [{"po_min": 0, "dzial": "sala", "zadanie": "x"}]}, "cena_os"),
    ({"nazwa": "A", "cena_os": "10", "etapy": []}, "etapy"),
    ({"nazwa": "A", "cena_os": "10", "etapy": [{"po_min": "x", "dzial": "sala", "zadanie": "x"}]}, "etapy.0.po_min"),
    ({"nazwa": "A", "cena_os": "10", "etapy": [{"po_min": 0, "dzial": "piwnica", "zadanie": "x"}]}, "etapy.0.dzial"),
    ({"nazwa": "A", "cena_os": "10", "etapy": [{"po_min": 0, "dzial": "sala", "zadanie": "  "}]}, "etapy.0.zadanie"),
    ({"nazwa": "A", "cena_os": "10", "etapy": [{"po_min": 0, "dzial": "sala", "zadanie": "x",
                                                "pozycje": [{"nazwa": "Rosół", "porcja": "300", "miara": ""}]}]},
     "etapy.0.pozycje.0.miara"),
])
def test_zapisz_menu_odrzuca_zle_dane(dane, pole, lokal):
    menu, bledy = uslugi.zapisz_menu(dane, lokal)
    assert pole in bledy and Menu.objects.count() == 0


def excel(wiersze):
    wb = Workbook()
    ws = wb.active
    ws.title = "Przyjęcia"
    for i, w in enumerate(wiersze, start=5):
        for kol, v in w.items():
            ws.cell(i, uslugi.KOLUMNY_EXCELA[kol], v)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@pytest.mark.django_db
def test_import_excela_idempotentny_i_odrzuca_bledy():
    lokal = menu_1().lokal
    wiersze = [
        {"data": date(2026, 11, 28), "start": time(15), "klient": "Nowakowie", "doroslych": 40, "menu": "Menu 1",
         "status": "potwierdzona", "zadatek": 500},
        {"data": date(2026, 11, 22), "start": time(14), "klient": "PRZYKŁAD Kowalscy", "doroslych": 10, "menu": "Menu 1"},
        {"data": date(2026, 11, 29), "start": time(13), "klient": "Zły", "doroslych": 0, "menu": "Menu 9"},
    ]
    podglad = uslugi.czytaj_excel(excel(wiersze), lokal)
    assert [w["stan"] for w in podglad] == ["nowe", "blad"]
    assert uslugi.importuj_excel(excel(wiersze), lokal) == 1
    assert uslugi.importuj_excel(excel(wiersze), lokal) == 0
    p = Przyjecie.objects.get()
    assert p.status == "potwierdzona" and p.cena_os == Decimal("180") and p.zadatek == 500


@pytest.mark.django_db
def test_nie_excel_daje_czytelny_blad(lokal):
    with pytest.raises(ValueError, match="Kalendarz przyjęć"):
        uslugi.czytaj_excel(BytesIO(b"to nie jest xlsx"), lokal)


@pytest.mark.django_db
def test_widoki_wymagaja_logowania(client):
    for url in ("/", "/przyjecia/", "/menu/", "/import/"):
        assert client.get(url).status_code == 302


@pytest.mark.django_db
def test_logowanie_zapisuje_zdarzenia(client):
    User.objects.create_user("marcin", password="dlugie-haslo-123")
    zle = client.post("/logowanie/", json.dumps({"login": "marcin", "haslo": "x"}), content_type="application/json")
    assert zle.status_code == 200
    ok = client.post("/logowanie/", json.dumps({"login": "marcin", "haslo": "dlugie-haslo-123"}),
                     content_type="application/json")
    assert ok.status_code == 302
    assert set(LoginEvent.objects.values_list("event_type", flat=True)) == {"failed", "login"}


@pytest.mark.django_db
def test_formularz_przyjecia_cena_z_menu_i_walidacja(client):
    m = menu_1()
    client.force_login(czlonek(User.objects.create_user("m", password="x" * 12), m.lokal))
    zle = client.post("/przyjecia/nowe/", json.dumps({"klient": " ", "menu": m.pk, "doroslych": 0}),
                      content_type="application/json", HTTP_X_INERTIA="true")
    props = zle.json()["props"]
    assert {"klient", "doroslych", "data", "start"} <= set(props["bledy"])
    ok = client.post("/przyjecia/nowe/", json.dumps({"data": "2026-11-28", "start": "15:00", "klient": "Nowakowie",
                                                     "rodzaj": "urodziny", "doroslych": 20, "dzieci": 0, "menu": m.pk,
                                                     "status": "wstepna"}), content_type="application/json")
    assert ok.status_code == 302
    assert Przyjecie.objects.get().cena_os == m.cena_os


@pytest.mark.django_db
def test_zespol_tylko_dla_kierownika_i_walidacja(client, lokal):
    zwykly = czlonek(User.objects.create_user("ania", password="x" * 12), lokal)
    client.force_login(zwykly)
    assert client.get("/zespol/").status_code == 302
    szef, _ = uslugi.zapisz_konto({"login": "Marcin", "haslo": "dlugie-haslo-123", "kierownik": True}, lokal)
    client.force_login(szef)
    assert client.get("/zespol/").status_code == 200
    _, bledy = uslugi.zapisz_konto({"login": "marcin", "haslo": "krotkie"}, lokal)
    assert {"login", "haslo"} <= set(bledy)
    client.post(f"/zespol/{zwykly.pk}/usun/")
    zwykly.refresh_from_db()
    assert not zwykly.is_active and User.objects.filter(pk=zwykly.pk).exists()
    client.post(f"/zespol/{szef.pk}/", json.dumps({"imie": "M", "aktywne": False, "kierownik": False}),
                content_type="application/json")
    szef.refresh_from_db()
    assert szef.is_active and uslugi.jest_kierownikiem(szef, lokal)


# ---------- logowanie przez dostawcę OIDC ----------
ISS, FIRMA = "https://konto.test/o", "11111111-2222-3333-4444-555555555555"


def claims(**kw):
    c = {"sub": "42", "preferred_username": "marcin", "name": "Marcin", "email": "m@x.pl",
         "firmy": [{"id": FIRMA, "nazwa": "Sami Swoi", "wlasciciel": True, "produkty": {"kalendarz": "kierownik"}}]}
    c.update(kw)
    return c


@pytest.mark.django_db
def test_oidc_pierwsze_logowanie_zaklada_konto_z_rola():
    u, blad = uslugi.konto_z_oidc(claims(), ISS, FIRMA)
    lokal = Lokal.objects.get(firma=FIRMA)
    assert blad is None and uslugi.jest_kierownikiem(u, lokal) and not u.has_usable_password()
    assert lokal.nazwa == "Sami Swoi"
    assert u.first_name == "Marcin"


@pytest.mark.django_db
def test_oidc_nie_przejmuje_lokalnego_konta_o_tym_samym_loginie():
    lokalny = User.objects.create_user("marcin", password="x" * 12)
    u, _ = uslugi.konto_z_oidc(claims(), ISS, FIRMA)
    assert u.pk != lokalny.pk and u.username == "marcin2"
    assert lokalny.check_password("x" * 12)


@pytest.mark.django_db
def test_oidc_drugie_logowanie_to_samo_konto_i_synchronizacja_roli():
    u1, _ = uslugi.konto_z_oidc(claims(), ISS, FIRMA)
    u2, _ = uslugi.konto_z_oidc(claims(firmy=[{"id": FIRMA, "produkty": {"kalendarz": "obsluga"}}], name="Marcin K."), ISS, FIRMA)
    assert u1.pk == u2.pk and not uslugi.jest_kierownikiem(u2, Lokal.objects.get()) and u2.first_name == "Marcin K."


@pytest.mark.django_db
@pytest.mark.parametrize("zle", [
    {"firmy": []}, {"firmy": [{"id": "inna-firma", "rola": "dyrektor"}]}, {"firmy": None},
    {"firmy": ["napis"]}, {"sub": ""}, {"sub": None},
    {"firmy": [{"id": FIRMA, "produkty": {"grafik": "dyrektor"}}]},  # firma tak, ale bez Kalendarza
    {"firmy": [{"id": FIRMA, "produkty": None}]}, {"firmy": [{"id": FIRMA, "rola": "kierownik"}]},  # stary kontrakt
])
def test_oidc_bez_czlonkostwa_lub_sub_nie_wchodzi_i_nie_zaklada_konta(zle):
    u, blad = uslugi.konto_z_oidc(claims(**zle), ISS, FIRMA)
    assert u is None and blad and User.objects.count() == 0


@pytest.mark.django_db
def test_oidc_ten_sam_sub_innego_dostawcy_to_inne_konto():
    u1, _ = uslugi.konto_z_oidc(claims(), ISS, FIRMA)
    u2, _ = uslugi.konto_z_oidc(claims(), "https://konto.sudomie.test", FIRMA)
    assert u1.pk != u2.pk


@pytest.mark.django_db
def test_oidc_konto_wylaczone_w_zespole_nie_wejdzie():
    u, _ = uslugi.konto_z_oidc(claims(), ISS, FIRMA)
    u.is_active = False
    u.save()
    assert uslugi.konto_z_oidc(claims(), ISS, FIRMA) == (None, "Twoje konto w kalendarzu jest wyłączone. Skontaktuj się z kierownikiem.")


@pytest.mark.django_db
def test_oidc_wylaczone_bez_issuera(client, settings):
    settings.OIDC_ISSUER = ""
    assert client.get("/oidc/login/")["Location"] == "/logowanie/"
    assert client.get("/logowanie/", HTTP_X_INERTIA="true").json()["props"]["sso"] is None
