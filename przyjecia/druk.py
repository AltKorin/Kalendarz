"""Wydruki kalendarza grup i imprez — czarno-białe A4 (kolorowa drukarka w hotelu nie działa, oszczędnie w tonerze).

Wzór: prototyp zaakceptowany przez hotel w listopadzie 2026 (czarno-biały wydruk do rozdania pracownikom).
Trzy widoki:
- `lista`     — A4 pionowo, termin / impreza / osoby (ok.), do rozdania pracownikom,
- `kalendarz` — A4 poziomo, siatka pon–nd (8 tygodni na stronę), paski imprez, „dziś”, wstępne przerywaną linią,
- `pelny`     — kalendarz + tabela (termin, impreza, osoby, status, sale, uwagi), wolne okna, nakładania, linie na zmiany.

Wejście: lista słowników `Termin` (patrz `termin_z_przyjecia`) — moduł nie zna modeli, tylko dane.
"""
from datetime import date, timedelta
from pathlib import Path

import pymupdf as fitz

from . import terminy as t

FONTY = Path(__file__).parent / "fonty"  # Liberation Sans = metryka Ariala z prototypu, licencja OFL
_F = {}


def _font(f):
    if f not in _F:
        _F[f] = fitz.Font(fontfile=str(FONTY / ("LiberationSans-Bold.ttf" if f == "b" else "LiberationSans-Regular.ttf")))
    return _F[f]


WYPELN = {"grupa": (1, 1, 1), "impreza": (0.86, 0.86, 0.86), "swieta": (0.70, 0.70, 0.70)}
DNI = ["PON", "WT", "ŚR", "CZW", "PT", "SOB", "ND"]
MIES = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]
SZARY = (0.3, 0.3, 0.3)
TYGODNI_NA_STRONE = 8


def termin_z_przyjecia(p):
    """Przyjecie (model) → słownik dla wydruków."""
    kategoria = "grupa" if p.rodzaj == "grupa" else "swieta" if p.rodzaj == "święta" else "impreza"
    return {"nazwa": p.klient, "od": p.data, "do": p.ostatni_dzien, "start": f"{p.start:%H:%M}" if p.start else "",
            "kategoria": kategoria, "osoby": p.osoby_opis or (str(p.goscie) if p.goscie else ""),
            "status": p.get_status_display().lower(), "wstepne": p.status == "wstepna", "sale": p.sale,
            "uwagi": p.uwagi}


# ---------- rysowanie ----------

def _tekst(p, x, y, s, f, size, kolor=(0, 0, 0), prawo=False, srodek=False, maxw=None):
    font = _font(f)
    if maxw:
        while font.text_length(s, fontsize=size) > maxw and len(s) > 3:
            s = s[:-2].rstrip() + "…"
    w = font.text_length(s, fontsize=size)
    x -= w if prawo else w / 2 if srodek else 0
    tw = fitz.TextWriter(p.rect, color=kolor)
    tw.append((x, y), s, font=font, fontsize=size)
    tw.write_text(p)
    return w


def _zawin(s, f, size, szer):
    linie, cur = [], ""
    for slowo in s.split():
        test = (cur + " " + slowo).strip()
        if _font(f).text_length(test, fontsize=size) <= szer:
            cur = test
        else:
            linie.append(cur)
            cur = slowo
    return [x for x in linie if x] + ([cur] if cur else [])


def _data(d):
    return f"{d.day}.{d.month:02d}.{d.year}"


def _zakres(od, do):
    if od == do:
        return f"{od.day}.{od.month:02d}"
    if od.month == do.month:
        return f"{od.day}–{do.day}.{do.month:02d}"
    return f"{od.day}.{od.month:02d} – {do.day}.{do.month:02d}"


def _osoby_krotko(os_):
    if not os_:
        return ""
    liczba = any(c.isdigit() for c in os_)
    return os_.rstrip("?") + (" os." if liczba else "") + ("?" if os_.endswith("?") else "")


# ---------- lista (A4 pionowo) ----------

def _lista(doc, lokal, stan, ts, od, do):
    W, H = 595.28, 841.89
    L, R = 48, W - 48
    x_imp = L + 150

    def nowa_strona(pierwsza):
        p = doc.new_page(width=W, height=H)
        _tekst(p, L, 70, "TERMINY GRUP I IMPREZ", "b", 22)
        _tekst(p, L, 90, f"{lokal} · {_data(od)}–{_data(do)} · stan na {_data(stan)}", "r", 11, SZARY, maxw=R - L)
        p.draw_line((L, 102), (R, 102), color=(0, 0, 0), width=1.4)
        y = 118
        p.draw_rect(fitz.Rect(L, y, R, y + 22), color=None, fill=(0.86, 0.86, 0.86))
        _tekst(p, L + 8, y + 15, "TERMIN", "b", 10)
        _tekst(p, x_imp, y + 15, "IMPREZA / GRUPA", "b", 10)
        _tekst(p, R - 8, y + 15, "OSOBY (ok.)", "b", 10, prawo=True)
        return p, y + 22

    p, y = nowa_strona(True)
    for x in ts:
        if y + 50 > H - 70:
            p, y = nowa_strona(False)
        _tekst(p, L + 8, y + 22, _zakres(x["od"], x["do"]), "b", 15)
        dni = DNI[x["od"].weekday()].lower() + ("" if x["od"] == x["do"] else f"–{DNI[x['do'].weekday()].lower()}")
        _tekst(p, L + 8, y + 38, dni + (f" · {x['start']}" if x["start"] else ""), "r", 10, (0.35, 0.35, 0.35))
        _tekst(p, x_imp, y + 22, x["nazwa"], "b", 14, maxw=R - 130 - x_imp)
        dop = "wstępnie" if x["wstepne"] else ("" if x["status"] in ("potwierdzona", "odbyła się") else x["status"])
        if dop:
            _tekst(p, x_imp, y + 38, dop, "b" if x["wstepne"] else "r", 10, (0.35, 0.35, 0.35))
        os_ = x["osoby"]
        if os_ and any(c.isdigit() for c in os_):
            _tekst(p, R - 8, y + 22, os_.replace("ok. ", ""), "b", 15, prawo=True)
        elif os_:
            for k, linia in enumerate(_zawin(os_, "b", 11, 120)[:3]):
                _tekst(p, R - 8, y + 21 + 13 * k, linia, "b", 11, prawo=True)
        else:
            p.draw_line((R - 70, y + 24), (R - 8, y + 24), color=(0.45, 0.45, 0.45), width=0.8)
        y += 50
        p.draw_line((L, y), (R, y), color=(0.6, 0.6, 0.6), width=0.6)
    if not ts:
        _tekst(p, L + 8, y + 26, "Brak terminów w tym okresie.", "r", 12, SZARY)
        y += 40
    _tekst(p, L, y + 26, "Liczby osób są orientacyjne i mogą się zmienić.", "r", 10, SZARY)


# ---------- siatka tygodni (A4 poziomo) ----------

W2, H2 = 841.89, 595.28
L2, R2 = 34, W2 - 34


def _naglowek(p, lokal, stan, podtytul):
    _tekst(p, L2, 46, "KALENDARZ GRUP I IMPREZ", "b", 20)
    _tekst(p, R2, 46, f"{lokal} · stan na {_data(stan)}", "b", 11, prawo=True, maxw=380)
    _tekst(p, L2, 63, podtytul, "r", 10, SZARY)
    p.draw_line((L2, 71), (R2, 71), color=(0, 0, 0), width=1.4)


def _legenda(p, y):
    x = L2
    for nazwa, kat in [("grupa zorganizowana", "grupa"), ("impreza / przyjęcie", "impreza"), ("święta i Nowy Rok", "swieta")]:
        p.draw_rect(fitz.Rect(x, y - 8, x + 16, y + 1), color=(0, 0, 0), fill=WYPELN[kat], width=0.8)
        x += 22 + _tekst(p, x + 22, y, nazwa, "r", 9) + 18
    p.draw_rect(fitz.Rect(x, y - 8, x + 16, y + 1), color=(0, 0, 0), width=0.8, dashes="[2 1.5] 0")
    _tekst(p, x + 22, y, "wstępne (linia przerywana)", "r", 9)


def _siatka(doc, lokal, stan, ts, start, tygodnie):
    p = doc.new_page(width=W2, height=H2)
    _naglowek(p, lokal, stan, "Liczby osób orientacyjne; „?” = niepewne.")
    xk = L2 + 52
    kol = (R2 - xk) / 7
    y = 82
    for i, d in enumerate(DNI):
        x = xk + i * kol
        if i >= 5:
            p.draw_rect(fitz.Rect(x, y, x + kol, y + 16), color=None, fill=(0.9, 0.9, 0.9))
        _tekst(p, x + kol / 2, y + 11.5, d, "b", 9, srodek=True)
    y += 16
    wys = (H2 - 40 - y) / TYGODNI_NA_STRONE
    for tydz in range(tygodnie):
        w0 = start + timedelta(days=7 * tydz)
        w1 = w0 + timedelta(days=6)
        y0 = y + tydz * wys
        for i in range(7):
            dzien = w0 + timedelta(days=i)
            x = xk + i * kol
            if i >= 5:
                p.draw_rect(fitz.Rect(x, y0, x + kol, y0 + wys), color=None, fill=(0.93, 0.93, 0.93))
            lab = f"{dzien.day}" + (f" {MIES[dzien.month - 1]}" if dzien.day == 1 or (tydz == 0 and i == 0) else "")
            _tekst(p, x + 4, y0 + 11, lab, "b" if dzien.day == 1 else "r", 8.5)
            if dzien == stan:
                p.draw_rect(fitz.Rect(x + 1, y0 + 1, x + kol - 1, y0 + wys - 1), color=(0, 0, 0), width=1.6)
                _tekst(p, x + kol - 4, y0 + 11, "dziś", "b", 8, prawo=True)
        _tekst(p, L2, y0 + 11, f"{w0.day} {MIES[w0.month - 1]}", "b", 8.5)
        pasy, ukryte = [], 0
        h = min(19, (wys - 20) / 2 - 2)
        for x_ in ts:
            od, do = x_["od"], x_["do"]
            if od > w1 or do < w0:
                continue
            c0, c1 = (max(od, w0) - w0).days, (min(do, w1) - w0).days
            pas = next((k for k, koniec in enumerate(pasy) if koniec < c0), None)
            if pas is None:
                pas = len(pasy)
                pasy.append(c1)
            else:
                pasy[pas] = c1
            yb = y0 + 16 + pas * (h + 3)
            if yb + h > y0 + wys - 1:  # ponytail: więcej niż mieszczą się pasy — licznik „+N”, szczegóły w tabeli
                ukryte += 1
                continue
            x0 = xk + c0 * kol + (3 if od >= w0 else 0)
            x1 = xk + (c1 + 1) * kol - (3 if do <= w1 else 0)
            p.draw_rect(fitz.Rect(x0, yb, x1, yb + h), color=(0, 0, 0), fill=WYPELN[x_["kategoria"]],
                        width=1.0 if x_["wstepne"] else 1.1, dashes="[3 2] 0" if x_["wstepne"] else None)
            opis = (f"{x_['start']} " if x_["start"] and od == do else "") + x_["nazwa"]
            if x_["osoby"]:
                opis += "  ·  " + _osoby_krotko(x_["osoby"])
            if x_["wstepne"]:
                opis += "  ·  wstępnie"
            if od < w0:
                opis = "← " + opis
            _tekst(p, x0 + 5, yb + h / 2 + 3.3, opis, "b", 8.8, maxw=x1 - x0 - 10)
        if ukryte:
            _tekst(p, L2, y0 + wys - 5, f"+{ukryte} więcej", "b", 7.5, SZARY)
        p.draw_line((L2, y0), (R2, y0), color=(0.55, 0.55, 0.55), width=0.6)
    dol = y + tygodnie * wys
    p.draw_line((L2, dol), (R2, dol), color=(0.55, 0.55, 0.55), width=0.6)
    for i in range(8):
        p.draw_line((xk + i * kol, y - 16), (xk + i * kol, dol), color=(0.7, 0.7, 0.7), width=0.5)
    _legenda(p, H2 - 22)


def _kalendarz(doc, lokal, stan, ts, od, do):
    start, koniec = t.poniedzialek(od), t.poniedzialek(do) + timedelta(days=6)
    wszystkie = (koniec - start).days // 7 + 1
    for s in range(0, wszystkie, TYGODNI_NA_STRONE):
        _siatka(doc, lokal, stan, ts, start + timedelta(days=7 * s), min(TYGODNI_NA_STRONE, wszystkie - s))


# ---------- tabela (pełny) ----------

def _opis_terminu(od, do, start):
    dni = DNI[od.weekday()].lower()
    if od == do:
        return _zakres(od, do), dni + (f" · {start}" if start else "")
    noce = (do - od).days
    return _zakres(od, do), f"{dni}–{DNI[do.weekday()].lower()} · {noce} {'noc' if noce == 1 else 'noce' if noce < 5 else 'nocy'}"


def _tabela(doc, lokal, stan, ts, od, do):
    kols = [("TERMIN", 108), ("IMPREZA", 152), ("OSOBY", 62), ("STATUS", 82), ("SALE", 140), ("UWAGI", None)]
    xs, x = [], L2
    for _, w in kols:
        xs.append(x)
        x += w or 0
    szer_uwagi = R2 - xs[-1] - 6

    def nowa(tabela=True):
        p = doc.new_page(width=W2, height=H2)
        _naglowek(p, lokal, stan, "Terminy po kolei. Puste pole = do uzupełnienia.")
        y = 86
        if not tabela:
            return p, y
        p.draw_rect(fitz.Rect(L2, y, R2, y + 20), color=None, fill=(0.85, 0.85, 0.85))
        for (n, _), x in zip(kols, xs):
            _tekst(p, x + 5, y + 13.5, n, "b", 9)
        _legenda(p, H2 - 22)
        return p, y + 20

    p, y = nowa()
    for x_ in ts:
        t1, t2 = _opis_terminu(x_["od"], x_["do"], x_["start"])
        lu = _zawin(x_["uwagi"], "r", 9.5, szer_uwagi)[:6] if x_["uwagi"] else []
        ls = _zawin(x_["sale"], "r", 9.5, 130) if x_["sale"] else []
        lo = _zawin(x_["osoby"], "b", 10.5, 52)[:3] if x_["osoby"] else []
        h = max(34, 14 + 13 * max(len(lu), len(ls), len(lo), 2))
        if y + h > H2 - 40:
            p, y = nowa()
        p.draw_rect(fitz.Rect(L2, y, L2 + 5, y + h), color=(0, 0, 0), fill=WYPELN[x_["kategoria"]], width=0.6,
                    dashes="[2 1.5] 0" if x_["wstepne"] else None)
        _tekst(p, xs[0] + 9, y + 15, t1, "b", 11)
        _tekst(p, xs[0] + 9, y + 28, t2, "r", 9, SZARY)
        _tekst(p, xs[1] + 5, y + 15, x_["nazwa"], "b", 10.5, maxw=kols[1][1] - 8)
        if lo:
            for k, linia in enumerate(lo):
                _tekst(p, xs[2] + 5, y + 15 + 13 * k, linia, "b", 10.5)
        else:
            p.draw_line((xs[2] + 5, y + 17), (xs[2] + 44, y + 17), color=(0.5, 0.5, 0.5), width=0.6)
        _tekst(p, xs[3] + 5, y + 15, x_["status"], "b" if x_["wstepne"] or x_["status"] == "potwierdzona" else "r", 10,
               maxw=kols[3][1] - 8)
        for k, linia in enumerate(ls):
            _tekst(p, xs[4] + 5, y + 15 + 13 * k, linia, "r", 9.5)
        for k, linia in enumerate(lu):
            _tekst(p, xs[5] + 5, y + 15 + 13 * k, linia, "r", 9.5)
        y += h
        p.draw_line((L2, y), (R2, y), color=(0.6, 0.6, 0.6), width=0.6)

    def akapit(tytul, tekst):
        nonlocal p, y
        linie = _zawin(tekst, "r", 9.5, R2 - L2)
        if y + 40 + 13 * len(linie) > H2 - 40:
            p, y = nowa(tabela=False)
        y += 22
        _tekst(p, L2, y, tytul, "b", 10)
        for k, linia in enumerate(linie):
            _tekst(p, L2, y + 15 + 13 * k, linia, "r", 9.5)
        y += 13 * len(linie) + 4

    klucze = {i: x_ for i, x_ in enumerate(ts)}
    nak = t.nakladania([(i, x_["od"], x_["do"]) for i, x_ in klucze.items()])
    if nak:
        akapit("Nakładające się terminy (pokoje i obsada):", "   ·   ".join(
            f"{klucze[a]['nazwa']} + {klucze[b]['nazwa']}: {_zakres(o, d)}" for a, b, o, d in nak))
    okna = t.wolne_okna([(i, x_["od"], x_["do"]) for i, x_ in klucze.items()], max(od, stan), do)
    akapit("Wolne terminy (przyjazd – wyjazd):",
           "   ·   ".join(f"{a.day}.{a.month:02d}–{b.day}.{b.month:02d}" for a, b in okna) or "brak")
    if y + 90 > H2 - 40:
        p, y = nowa(tabela=False)
    y += 22
    _tekst(p, L2, y, "Zmiany i uwagi:", "b", 10)
    for k in range(3):
        p.draw_line((L2, y + 22 + k * 20), (R2, y + 22 + k * 20), color=(0.5, 0.5, 0.5), width=0.6)


WIDOKI = {"lista": "terminy-grup-i-imprez", "kalendarz": "kalendarz-terminy-pon-nd", "pelny": "kalendarz-grup-i-imprez"}


def pdf(widok, lokal, stan, ts, od, do):
    """→ (bajty PDF, nazwa pliku). ts — słowniki z `termin_z_przyjecia`, posortowane po dacie."""
    if widok not in WIDOKI:
        raise ValueError(f"Nieznany wydruk: {widok}")
    if do < od:
        raise ValueError("Koniec okresu przed początkiem.")
    ts = sorted(ts, key=lambda x: (x["od"], x["start"] or "", x["nazwa"]))
    doc = fitz.open()
    if widok == "lista":
        _lista(doc, lokal, stan, ts, od, do)
    else:
        _kalendarz(doc, lokal, stan, ts, od, do)
        if widok == "pelny":
            _tabela(doc, lokal, stan, ts, od, do)
    doc.set_metadata({"title": f"Kalendarz grup i imprez – stan na {_data(stan)}", "author": lokal})
    return doc.tobytes(garbage=3, deflate=True), f"{WIDOKI[widok]}_{stan.isoformat()}_A4.pdf"
