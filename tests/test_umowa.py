"""Umowa o imprezę z danych przyjęcia (przyjecia/umowa.py) + stan umowy w panelu."""
import json
import string
from datetime import date
from decimal import Decimal
from io import BytesIO

import docx
import pytest
from django.contrib.auth.models import User
from hypothesis import given, settings as hsettings, strategies as st
from hypothesis.extra.django import TestCase as HTestCase

from przyjecia import umowa
from przyjecia.models import Lokal, Przyjecie
from tests.conftest import czlonek
from tests.test_panel import menu_1, przyjecie

POLA = {f for par in umowa.tresc()["paragrafy"] for s in par["punkty"]
        for _, f, _, _ in string.Formatter().parse(s) if f}


def tekst(bajty):
    d = docx.Document(BytesIO(bajty))
    return "\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells])


def test_plik_tresci_ma_tylko_znane_pola_i_zadnych_danych_malborka():
    surowy = json.dumps(umowa.tresc()["paragrafy"], ensure_ascii=False)
    assert POLA == {"rodzaj", "data", "od", "sala", "lokal", "doroslych", "dzieci", "cena_os", "cena_dziecko", "menu",
                    "razem", "zadatek", "kontakt"}
    for z in ("Sami Swoi", "Wielbark", "Malbork", "przystanek", "Zielińsk", "5862353087"):
        assert z not in surowy


@pytest.mark.django_db
def test_umowa_z_menu_wypelniona_danymi_przyjecia():
    m = menu_1()
    m.lokal.kontakt = "rezerwacje@lokal.test"
    m.lokal.save()
    p = przyjecie(m, sale="Sala Kominkowa", cena_dziecko=Decimal("80"), uwagi="bez glutenu: 2 os.")
    bajty, nazwa = umowa.umowa_docx(p)
    t = tekst(bajty)
    assert nazwa.startswith("2026-11-22 ") and nazwa.endswith(" - umowa.docx")
    for oczekiwane in ("WZÓR", "Kowalscy", "22.11.2026", "14:00", "Sala Kominkowa", "38 dorosłych i 6 dzieci",
                       "komunia", "1 000,00 zł", "80,00 zł", "rezerwacje@lokal.test", f"menu „{m.nazwa}”",
                       "bez glutenu: 2 os.", "w cenie menu"):
        assert oczekiwane in t, oczekiwane
    assert "{" not in t


@pytest.mark.django_db
def test_termin_bez_menu_zostawia_nawiasy_zamiast_zer():
    lokal = Lokal.objects.create(nazwa="Hotel Testowy")
    p = Przyjecie.objects.create(lokal=lokal, data=date(2026, 12, 4), koniec=date(2026, 12, 6), klient="Grupa X",
                                 rodzaj="inne", osoby_opis="ok. 40")
    t = tekst(umowa.umowa_docx(p)[0])
    assert "04.12.2026–06.12.2026" in t and "[rodzaj imprezy]" in t and "[GG:MM]" in t
    assert "0,00 zł" not in t and "[...] zł" in t and "{" not in t


class PrawaPol(HTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.menu = menu_1()

    @hsettings(max_examples=30, deadline=None)
    @given(st.integers(0, 150), st.integers(0, 40), st.decimals(0, 5000, places=2),
           st.one_of(st.none(), st.decimals(0, 500, places=2)), st.booleans())
    def test_kazde_pole_ma_wartosc(self, dorosli, dzieci, zadatek, cena_dz, z_menu):
        p = przyjecie(self.menu, doroslych=dorosli, dzieci=dzieci, zadatek=zadatek, cena_dziecko=cena_dz,
                      klient=f"K{dorosli}-{dzieci}-{zadatek}-{cena_dz}-{z_menu}")
        if not z_menu:
            p.menu = None
        f = umowa.pola(p)
        assert POLA <= f.keys()
        assert all(isinstance(v, str) and (v.strip() or k == "menu") for k, v in f.items())
        assert "0,00 zł" not in (f["cena_os"], f["razem"], f["zadatek"])


@pytest.mark.django_db
def test_stan_umowy_klikany_tylko_dla_swojego_lokalu(client):
    m = menu_1()
    p = przyjecie(m)
    client.force_login(czlonek(User.objects.create_user("m", password="x" * 12), m.lokal))
    post = lambda pk, stan: client.post(f"/przyjecia/{pk}/umowa/", json.dumps({"umowa": stan}),
                                        content_type="application/json")
    assert post(p.pk, "wyslana").status_code == 302
    p.refresh_from_db()
    assert p.umowa == "wyslana" and p.history.first().umowa == "wyslana"
    post(p.pk, "podrobiona")
    p.refresh_from_db()
    assert p.umowa == "wyslana"
    obcy = przyjecie(menu_1(Lokal.objects.create(nazwa="Obcy")), klient="Obcy")
    assert post(obcy.pk, "podpisana").status_code == 404
    assert client.get(f"/przyjecia/{p.pk}/umowa.docx").status_code == 200
    assert client.get(f"/przyjecia/{obcy.pk}/umowa.docx").status_code == 404
