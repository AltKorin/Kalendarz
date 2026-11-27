"""Prawa przyjecia/stoliki.py (docstring modułu) — Hypothesis szuka kontrprzykładu."""
from datetime import time

from hypothesis import example, given, strategies as st

from przyjecia import stoliki as s

MINUTA = st.integers(0, 23 * 60 + 58)


def godz(m):
    return time(m // 60, m % 60)


@st.composite
def rezerwacja(draw, stoliki=st.frozensets(st.integers(1, 6), max_size=3)):
    od = draw(MINUTA)
    do = draw(st.integers(od + 1, 23 * 60 + 59))
    return godz(od), godz(do), draw(stoliki)


@given(rezerwacja(), rezerwacja())
def test_kolizja_symetryczna(a, b):
    assert s.koliduje(a, b) == s.koliduje(b, a)


@given(rezerwacja(st.frozensets(st.integers(1, 3), max_size=3)), rezerwacja(st.frozensets(st.integers(4, 6), max_size=3)))
def test_bez_wspolnego_stolika_brak_kolizji(a, b):
    assert not s.koliduje(a, b)


@given(rezerwacja(), rezerwacja())
@example((time(18), time(20), frozenset({5})), (time(20), time(22), frozenset({5})))  # styk: stolik zwolniony o 20
def test_kolizja_dokladnie_gdy_wspolny_stolik_i_godziny(a, b):
    nakladaja = a[0] < b[1] and b[0] < a[1]
    assert s.koliduje(a, b) == (bool(a[2] & b[2]) and nakladaja)


@given(rezerwacja(), st.lists(rezerwacja(), max_size=8))
def test_kolizje_zwracaja_tylko_kolidujace_z_wspolnymi_stolikami(nowa, inne):
    wynik = s.kolizje(nowa, [(i, *r) for i, r in enumerate(inne)])
    assert {k for k, _ in wynik} == {i for i, r in enumerate(inne) if s.koliduje(nowa, r)}
    assert all(wspolne and wspolne <= nowa[2] for _, wspolne in wynik)


@given(MINUTA, st.integers(15, 12 * 60))
@example(23 * 60 + 30, 120)  # po północy → 23:59, nie 01:30
def test_domyslny_koniec_po_poczatku_tego_samego_dnia(od, minuty):
    koniec = s.domyslny_koniec(godz(od), minuty)
    assert godz(od) < koniec <= time(23, 59)


NUMER = st.one_of(st.integers(0, 999).map(str),
                  st.tuples(st.sampled_from(["Ogród ", "T", "taras "]), st.integers(0, 99)).map(lambda t: f"{t[0]}{t[1]}"),
                  st.text(alphabet="abcXYZ 12", min_size=1, max_size=6))


@given(st.lists(NUMER, max_size=15))
@example(["10", "2", "1", "Ogród 10", "Ogród 2"])
def test_kolejnosc_numerow_jak_liczby_i_bez_zgubienia(numery):
    class S:
        def __init__(self, numer):
            self.numer = numer
    wynik = [x.numer for x in s.po_numerze([S(n) for n in numery])]
    assert sorted(wynik) == sorted(numery)  # nic nie ginie, nic nie przybywa
    liczby = [int(n) for n in wynik if n.isdigit()]
    assert liczby == sorted(liczby)  # same liczby: 2 przed 10
    for prefiks in ("Ogród ", "T", "taras "):
        ogon = [int(n[len(prefiks):]) for n in wynik if n.startswith(prefiks) and n[len(prefiks):].isdigit()]
        assert ogon == sorted(ogon)
