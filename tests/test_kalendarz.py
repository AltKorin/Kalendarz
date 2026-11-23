"""Prawa z docstringu kalendarz.py. Uruchom: python3 -m pytest tests/"""
import copy
import sys
from pathlib import Path

from hypothesis import given, strategies as st

sys.path.insert(0, str(Path(__file__).parent.parent))
import kalendarz as k  # noqa: E402

KOLBUDY = Path(__file__).parent.parent / "imprezy/2026-11-21-kolbudy/impreza.json"
godzina = st.builds(lambda h, m: f"{h:02d}:{m:02d}", st.integers(0, 23), st.integers(0, 59))


def dane():
    return copy.deepcopy(k.wczytaj(KOLBUDY))


def test_kolbudy_bez_bledow():
    assert k.sprawdz(dane()) == []


@given(godzina, godzina)
def test_czas_trwania_zawsze_w_dobie(od, do):
    t = k.czas_trwania(od, do)
    assert 0 <= t < 24 * 60
    assert (t == 0) == (od == do)


def test_kolacja_po_polnocy():
    assert k.czas_trwania("19:30", "02:00") == 6 * 60 + 30


@given(st.dates())
def test_dzien_poza_imprezą_to_blad(d):
    x = dane()
    x["obowiazki"][0]["dzien"] = d.isoformat()
    w_zakresie = x["od"] <= d.isoformat() <= x["do"]
    assert any("poza imprezą" in b for b in k.sprawdz(x)) != w_zakresie


def test_zle_odwolania_i_puste_pola():
    x = dane()
    x["obowiazki"][0].update(dzial="nieznany", menu="brak", zadanie="  ")
    x["program"][0]["sesje"][0]["sala"] = "piwnica"
    x["program"][1]["od"] = "25:00"
    bledy = " ".join(k.sprawdz(x))
    for fraza in ("nieznany dział", "nieznane menu", "puste zadanie", "nieznana sala", "zła godzina"):
        assert fraza in bledy


def test_menu_tylko_dla_obslugi_nie_trafia_do_gosci(tmp_path):
    x = dane()
    assert "apartament" not in k.menu_dla_gosci(x)
    k.agenda_docx(x, tmp_path / "a.docx")
    from docx import Document
    tekst = "\n".join(c.text for t in Document(tmp_path / "a.docx").tables for r in t.rows for c in r.cells)
    assert "Jesiotr" not in tekst and "apartament" not in tekst.lower()


# ---------- wycena, ilości, fabryka przyjęć ----------
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

kwota = st.decimals(min_value=0, max_value=10000, places=2)


@given(kwota, st.integers(0, 300), st.integers(0, 50), st.one_of(st.none(), kwota), kwota)
def test_wycena_suma_i_nieujemnosc(cena, dorosli, dzieci, cena_dz, zadatek):
    w = k.wycena({"cena_os": cena, "doroslych": dorosli, "dzieci": dzieci, "cena_dziecko": cena_dz, "zadatek": zadatek})
    oczek = cena * dorosli + (cena_dz * dzieci if cena_dz is not None else 0)
    assert w["razem"] == oczek.quantize(Decimal("0.01"))
    assert w["do_zaplaty"] >= 0
    assert w["do_zaplaty"] == max(w["razem"] - zadatek, Decimal(0))
    assert w["razem"].as_tuple().exponent == -2


@pytest.mark.parametrize("zle", [{"cena_os": -1}, {"cena_os": 10, "zadatek": -5}, {"cena_os": 10, "doroslych": -1}])
def test_wycena_odrzuca_ujemne(zle):
    with pytest.raises(ValueError):
        k.wycena({"doroslych": 1, **zle})


@given(st.integers(1, 1000), st.integers(1, 300))
def test_ilosc_to_porcja_razy_osoby(porcja, osoby):
    tekst = k.ilosc(porcja, "g", osoby)
    assert tekst.startswith(f"{porcja} g")
    wynik = tekst.split("= ")[1]
    liczba, jedn = wynik.split()
    assert Decimal(liczba.replace(",", ".")) * (1000 if jedn == "kg" else 1) == porcja * osoby


@given(st.integers(1, 120), st.integers(0, 30), st.sampled_from(["menu-1", "menu-2"]),
       st.sampled_from(["12:00", "14:00", "17:30"]))
def test_nowa_impreza_zawsze_poprawna(dorosli, dzieci, pakiet, godz):
    d = k.nowa_impreza("sami-swoi", pakiet, "2026-11-22", godz, dorosli, "Test", dzieci=dzieci, tort="18:00")
    d["lokal"] = k.json.loads((k.KATALOG / "lokale/sami-swoi.json").read_text(encoding="utf-8"))
    assert k.sprawdz(d) == []
    assert d["liczba_osob"] == dorosli + dzieci
    assert any(p["tytul"] == "Tort" for p in d["program"])


@pytest.mark.parametrize("dorosli,klient", [(0, "X"), (-3, "X"), (10, "   ")])
def test_nowa_impreza_odrzuca_bzdury(dorosli, klient):
    with pytest.raises(ValueError):
        k.nowa_impreza("sami-swoi", "menu-1", "2026-11-22", "14:00", dorosli, klient)
