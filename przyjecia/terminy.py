"""Terminy grup i imprez (wzór: kalendarz Hotelu Niedźwiadek, 19.11.2026) — czyste funkcje na (od, do).

Termin = (od, do), do >= od. Jednodniowe przyjęcie: od == do. Kilkudniowy pobyt zajmuje NOCE od..do-1
(do = dzień wyjazdu); jednodniowy zajmuje swój dzień.

Prawa (tests/test_terminy_laws.py):
- nakładanie jest symetryczne i każdą parę zgłasza raz; termin nie nakłada się sam ze sobą,
- wyjazd i przyjazd tego samego dnia (Sylwester do 3.01, Trzech Króli od 2.01) to nakładanie — pokoje i obsada,
- wolne okna i zajęte dni są rozłączne, a razem dają cały zakres; okna są posortowane i się nie stykają,
- dzień zajęty przez odwołany termin jest wolny (wołający podaje tylko aktywne terminy).
"""
from datetime import date, timedelta


def zajete_dni(od, do):
    """Dni (noce) zajęte przez termin."""
    if do < od:
        raise ValueError("Koniec przed początkiem.")
    if do == od:
        return {od}
    return {od + timedelta(days=i) for i in range((do - od).days)}


def naklada_sie(a, b):
    """a, b = (od, do). Wspólny dzień kalendarza (także wyjazd jednego = przyjazd drugiego)."""
    return a[0] <= b[1] and b[0] <= a[1]


def nakladania(terminy):
    """terminy: [(klucz, od, do)] → [(klucz_a, klucz_b, od_wspolne, do_wspolne)], każda para raz, wg daty."""
    t = sorted(terminy, key=lambda x: (x[1], x[2]))
    wynik = []
    for i, (ka, oda, doa) in enumerate(t):
        for kb, odb, dob in t[i + 1:]:
            if odb > doa:
                break  # posortowane po od — dalsze zaczynają się jeszcze później
            wynik.append((ka, kb, max(oda, odb), min(doa, dob)))
    return wynik


def wolne_okna(terminy, od, do):
    """Wolne dni w [od, do] (włącznie) jako [(pierwszy_wolny, dzien_po_ostatnim_wolnym)] — jak „przyjazd – wyjazd”."""
    if do < od:
        raise ValueError("Koniec zakresu przed początkiem.")
    zajete = set().union(*(zajete_dni(a, b) for _, a, b in terminy)) if terminy else set()
    okna, poczatek, d = [], None, od
    while d <= do:
        if d not in zajete:
            poczatek = poczatek or d
        elif poczatek:
            okna.append((poczatek, d))
            poczatek = None
        d += timedelta(days=1)
    if poczatek:
        okna.append((poczatek, do + timedelta(days=1)))
    return okna


def poniedzialek(d: date) -> date:
    return d - timedelta(days=d.weekday())
