"""Prawa przyjecia/terminy.py (docstring modułu) — Hypothesis szuka kontrprzykładu."""
from datetime import date, timedelta

import pytest
from hypothesis import example, given, strategies as st

from przyjecia import terminy as t

DZIEN = st.dates(date(2026, 1, 1), date(2027, 12, 31))


@st.composite
def termin(draw):
    od = draw(DZIEN)
    return od, od + timedelta(days=draw(st.integers(0, 10)))


TERMINY = st.lists(termin(), max_size=12).map(lambda xs: [(i, a, b) for i, (a, b) in enumerate(xs)])


@given(TERMINY)
def test_nakladanie_symetryczne_kazda_para_raz(ts):
    pary = t.nakladania(ts)
    klucze = [frozenset((a, b)) for a, b, *_ in pary]
    assert len(klucze) == len(set(klucze)) and all(len(k) == 2 for k in klucze)
    po_kluczu = {k: (a, b) for k, a, b in ts}
    for i, (ka, *ra) in enumerate(ts):
        for kb, *rb in ts[i + 1:]:
            assert (frozenset((ka, kb)) in klucze) == t.naklada_sie(po_kluczu[ka], po_kluczu[kb])
    for _, _, od, do in pary:
        assert od <= do


@given(TERMINY, DZIEN, st.integers(0, 120))
@example([(0, date(2026, 12, 31), date(2027, 1, 3)), (1, date(2027, 1, 2), date(2027, 1, 6))], date(2026, 12, 28), 14)
def test_wolne_i_zajete_rozlaczne_i_pokrywaja_zakres(ts, od, dlugosc):
    do = od + timedelta(days=dlugosc)
    okna = t.wolne_okna(ts, od, do)
    wolne = set()
    for a, b in okna:
        assert od <= a < b <= do + timedelta(days=1)
        wolne |= {a + timedelta(days=i) for i in range((b - a).days)}
    zakres = {od + timedelta(days=i) for i in range(dlugosc + 1)}
    zajete = set().union(*(t.zajete_dni(a, b) for _, a, b in ts)) & zakres if ts else set()
    assert wolne & zajete == set() and wolne | zajete == zakres
    for (a1, b1), (a2, _) in zip(okna, okna[1:]):
        assert b1 < a2  # posortowane i oddzielone co najmniej jednym zajętym dniem


def test_sylwester_i_trzech_kroli_nakladaja_sie_2_3_stycznia():
    pary = t.nakladania([("Sylwester", date(2026, 12, 31), date(2027, 1, 3)),
                         ("Trzech Króli", date(2027, 1, 2), date(2027, 1, 6))])
    assert pary == [("Sylwester", "Trzech Króli", date(2027, 1, 2), date(2027, 1, 3))]


def test_wyjazd_rano_przyjazd_tego_samego_dnia_to_nakladanie():
    assert t.nakladania([("a", date(2026, 12, 4), date(2026, 12, 6)), ("b", date(2026, 12, 6), date(2026, 12, 8))])


def test_wolne_okna_jak_w_prototypie_niedzwiadka():
    ts = [(1, date(2026, 11, 21), date(2026, 11, 22)), (2, date(2026, 11, 27), date(2026, 11, 29))]
    assert t.wolne_okna(ts, date(2026, 11, 23), date(2026, 11, 30)) == [
        (date(2026, 11, 23), date(2026, 11, 27)), (date(2026, 11, 29), date(2026, 12, 1))]


def test_koniec_przed_poczatkiem_to_blad():
    with pytest.raises(ValueError):
        t.zajete_dni(date(2026, 1, 2), date(2026, 1, 1))
    with pytest.raises(ValueError):
        t.wolne_okna([], date(2026, 1, 2), date(2026, 1, 1))
