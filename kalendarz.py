"""Kalendarz imprezy: jeden plik danych → agenda dla gości + plan obsługi z obowiązkami.

Użycie:
  python3 kalendarz.py imprezy/<impreza>/impreza.json        → imprezy/<impreza>/dokumenty/*.docx
  python3 kalendarz.py nowa <lokal> <pakiet> <data> <godz> <dorośli> "<klient>" [--dzieci N] [--typ komunia]
        [--tort 17:00] [--zadatek 1000] [--uwagi "bez glutenu: 2 os."]   → nowy imprezy/<data>-<klient>/impreza.json
  python3 kalendarz.py miesiac <lokal> <RRRR-MM>               → imprezy/kalendarz-<lokal>-<RRRR-MM>.docx

Prawa (sprawdza `sprawdz`, testy w tests/test_kalendarz.py):
- każda pozycja ma dzień w zakresie imprezy (od <= dzien <= do),
- czas trwania > 0 i < 24 h (do < od = po północy, np. kolacja 19:30–02:00),
- każda sala / grupa / dział / menu, do którego odwołuje się pozycja, istnieje w danych,
- menu z "dla_gosci": false nigdy nie trafia do agendy dla gości,
- wycena: razem = cena_os × dorośli + cena_dziecko × dzieci, do zapłaty = razem − zadatek, nic nie jest < 0,
- ilość dla kuchni = porcja × (dorośli + dzieci).
"""
import argparse
import json
import re
import sys
import unicodedata
from decimal import Decimal
from datetime import date, datetime, timedelta
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

DNI = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
MIESIACE = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
            "sierpnia", "września", "października", "listopada", "grudnia"]
FONT_TYTUL = "Georgia"
FONT_TEKST = "Century Gothic"
SZARY = RGBColor(0x77, 0x77, 0x77)
KATALOG = Path(__file__).parent


def _ustaw_fonty(lokal):
    # ponytail: globalne fonty na czas generowania jednego dokumentu (CLI, jeden wątek)
    global FONT_TYTUL, FONT_TEKST
    f = lokal.get("fonty", {})
    FONT_TYTUL, FONT_TEKST = f.get("tytul", "Georgia"), f.get("tekst", "Century Gothic")


# ---------- dane ----------

def wczytaj(sciezka_impreza):
    sciezka = Path(sciezka_impreza)
    dane = json.loads(sciezka.read_text(encoding="utf-8"))
    lokal = sciezka.parent.parent.parent / "lokale" / f"{dane['lokal']}.json"
    dane["lokal"] = json.loads(lokal.read_text(encoding="utf-8"))
    return dane


def _minuty(hhmm):
    t = datetime.strptime(hhmm, "%H:%M")
    return t.hour * 60 + t.minute


def czas_trwania(od, do):
    """Minuty między od a do; do < od oznacza po północy."""
    if not do:
        return None
    return (_minuty(do) - _minuty(od)) % (24 * 60)


def sprawdz(dane):
    """Lista błędów w danych imprezy (pusta = OK)."""
    bledy = []
    lokal = dane["lokal"]
    start, koniec = date.fromisoformat(dane["od"]), date.fromisoformat(dane["do"])
    if koniec < start:
        bledy.append(f"Impreza kończy się ({koniec}) przed początkiem ({start}).")

    def pozycja(p, gdzie):
        try:
            d = date.fromisoformat(p["dzien"])
            if not start <= d <= koniec:
                bledy.append(f"{gdzie}: dzień {d} poza imprezą {start}–{koniec}.")
        except (KeyError, ValueError):
            bledy.append(f"{gdzie}: brak lub zły dzień ({p.get('dzien')!r}).")
        try:
            _minuty(p["od"])  # sama godzina też musi być poprawna (program często nie ma "do")
            trwa = czas_trwania(p["od"], p.get("do"))
            if trwa == 0:
                bledy.append(f"{gdzie}: od = do ({p['od']}).")
        except (KeyError, ValueError, TypeError):
            bledy.append(f"{gdzie}: zła godzina (od={p.get('od')!r}, do={p.get('do')!r}).")
        if "sala" in p and p["sala"] not in lokal["sale"]:
            bledy.append(f"{gdzie}: nieznana sala {p['sala']!r}.")

    for i, p in enumerate(dane.get("program", [])):
        gdzie = f"program[{i}] {p.get('tytul', '')}"
        if not str(p.get("tytul", "")).strip():
            bledy.append(f"{gdzie}: pusty tytuł.")
        pozycja(p, gdzie)
        for s in p.get("sesje", []):
            if s.get("grupa") not in dane.get("grupy", {}):
                bledy.append(f"{gdzie}: nieznana grupa {s.get('grupa')!r}.")
            if s.get("sala") not in lokal["sale"]:
                bledy.append(f"{gdzie}: nieznana sala {s.get('sala')!r}.")

    for i, o in enumerate(dane.get("obowiazki", [])):
        gdzie = f"obowiazki[{i}] {o.get('zadanie', '')}"
        if not str(o.get("zadanie", "")).strip():
            bledy.append(f"{gdzie}: puste zadanie.")
        pozycja(o, gdzie)
        if o.get("dzial") not in lokal["dzialy"]:
            bledy.append(f"{gdzie}: nieznany dział {o.get('dzial')!r}.")
        if o.get("miejsce") and o["miejsce"] not in lokal["sale"]:
            bledy.append(f"{gdzie}: nieznane miejsce {o['miejsce']!r}.")
        if o.get("menu") and o["menu"] not in dane.get("menu", {}):
            bledy.append(f"{gdzie}: nieznane menu {o['menu']!r}.")
    if dane.get("wycena"):
        try:
            wycena(dane["wycena"])
        except (ValueError, KeyError, ArithmeticError) as e:
            bledy.append(f"wycena: {e}")
    return bledy


def dni(dane):
    d, koniec = date.fromisoformat(dane["od"]), date.fromisoformat(dane["do"])
    while d <= koniec:
        yield d.isoformat()
        d += timedelta(days=1)


def nazwa_dnia(iso):
    d = date.fromisoformat(iso)
    return f"{DNI[d.weekday()]}, {d.day} {MIESIACE[d.month - 1]}"


def zakres_dat(dane):
    a, b = date.fromisoformat(dane["od"]), date.fromisoformat(dane["do"])
    if a == b:
        return f"{a.day} {MIESIACE[a.month - 1]} {a.year}"
    if a.month == b.month:
        return f"{a.day}–{b.day} {MIESIACE[a.month - 1]} {a.year}"
    return f"{a.day} {MIESIACE[a.month - 1]} – {b.day} {MIESIACE[b.month - 1]} {b.year}"


def godziny(p):
    return f"{p['od']}–{p['do']}" if p.get("do") else p["od"]


def po_kolei(pozycje, dzien):
    return sorted((p for p in pozycje if p["dzien"] == dzien), key=lambda p: _minuty(p["od"]))


def menu_dla_gosci(dane):
    return {k: m for k, m in dane.get("menu", {}).items() if m.get("dla_gosci", True)}


def menu_jako_linie(m):
    linie = []
    for s in m["sekcje"]:
        naglowek = s.get("nazwa", "")
        if s.get("uwaga"):
            naglowek += f" ({s['uwaga']})"
        pozycje = ", ".join(s["pozycje"])
        linie.append(f"{naglowek}: {pozycje}" if naglowek else pozycje)
    return linie


# ---------- docx: drobne narzędzia ----------

def _rgb(hexkolor):
    return RGBColor.from_string(hexkolor)


def _cien(komorka, hexkolor):
    tc = komorka._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexkolor)
    tc.append(shd)


def _ramki(tabela, hexkolor, wewnetrzne=True):
    tbl = tabela._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for bok in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{bok}")
        widoczna = bok in ("top", "bottom", "insideH") and (wewnetrzne or bok != "insideH")
        e.set(qn("w:val"), "single" if widoczna else "nil")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), hexkolor)
        b.append(e)
    tbl.append(b)


def _szerokosci(tabela, cm):
    """Word i LibreOffice biorą szerokość z tblGrid, nie z komórek — ustawiamy oba."""
    tabela.autofit = False
    for kol, szer in zip(tabela._tbl.tblGrid.findall(qn("w:gridCol")), cm):
        kol.set(qn("w:w"), str(int(Cm(szer).twips)))
    for wiersz in tabela.rows:
        for kom, szer in zip(wiersz.cells, cm):
            kom.width = Cm(szer)


def _naglowek_tabeli_powtarzany(wiersz):
    trPr = wiersz._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader")
    e.set(qn("w:val"), "true")
    trPr.append(e)


def _nie_dziel_wiersza(wiersz):
    trPr = wiersz._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:cantSplit"))


def _tekst(akapit, tekst, rozmiar=10, pogrubiony=False, kolor=None, font=None, kursywa=False):
    r = akapit.add_run(tekst)
    r.font.name = font or FONT_TEKST
    r.font.size = Pt(rozmiar)
    r.bold = pogrubiony
    r.italic = kursywa
    if kolor is not None:
        r.font.color.rgb = kolor
    return r


def _akapit(kontener, odstep_po=0):
    p = kontener.add_paragraph()
    p.paragraph_format.space_after = Pt(odstep_po)
    p.paragraph_format.space_before = Pt(0)
    return p


def _nowy_dokument(poziomo=False):
    doc = Document()
    s = doc.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21.0)
    if poziomo:
        s.orientation = WD_ORIENT.LANDSCAPE
        s.page_width, s.page_height = Cm(29.7), Cm(21.0)
    for m in ("left_margin", "right_margin"):
        setattr(s, m, Cm(1.8))
    s.top_margin, s.bottom_margin = Cm(1.5), Cm(1.5)
    styl = doc.styles["Normal"]
    styl.font.name = FONT_TEKST
    styl.font.size = Pt(10)
    styl.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_TEKST)
    return doc


def _stopka(doc, tekst):
    p = doc.sections[0].footer.paragraphs[0]
    _tekst(p, tekst, 8, kolor=SZARY)


# ---------- agenda dla gości ----------

def agenda_docx(dane, wyjscie):
    lokal, k = dane["lokal"], dane["lokal"]["kolory"]
    _ustaw_fonty(lokal)
    doc = _nowy_dokument()

    p = _akapit(doc, 2)
    if lokal.get("logo"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(KATALOG / "lokale" / lokal["logo"]), height=Cm(3.2))
    else:
        _tekst(p, lokal["nazwa"].upper(), 9, True, _rgb(k["akcent"]))
    p = _akapit(doc, 0)
    _tekst(p, "AGENDA", 9, True, _rgb(k["akcent"]))
    p = _akapit(doc, 2)
    _tekst(p, dane["nazwa"], 26, True, _rgb(k["glowny"]), FONT_TYTUL)
    p = _akapit(doc, 10)
    _tekst(p, f"{zakres_dat(dane)} · {lokal['nazwa']}", 11, kolor=SZARY)

    for dzien in dni(dane):
        pozycje = po_kolei(dane["program"], dzien)
        if not pozycje:
            continue
        p = _akapit(doc, 4)
        p.paragraph_format.space_before = Pt(8)
        _tekst(p, nazwa_dnia(dzien), 15, True, _rgb(k["glowny"]), FONT_TYTUL)

        t = doc.add_table(rows=0, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        _ramki(t, k["linia"])
        for poz in pozycje:
            w = t.add_row()
            _nie_dziel_wiersza(w)
            _tekst(w.cells[0].paragraphs[0], godziny(poz), 11, True, _rgb(k["glowny"]))
            c = w.cells[1].paragraphs[0]
            _tekst(c, poz["tytul"], 11, True, _rgb(k["glowny"]))
            if poz.get("sala") and not poz.get("sesje"):
                _tekst(c, f"  ·  {lokal['sale'][poz['sala']]}", 9, kolor=_rgb(k["akcent"]))
            for linia in poz.get("opis", []):
                _tekst(w.cells[1].add_paragraph(), linia, 10)
            for s in poz.get("sesje", []):
                ps = w.cells[1].add_paragraph()
                ps.paragraph_format.space_before = Pt(3)
                _tekst(ps, dane["grupy"][s["grupa"]], 10, True)
                _tekst(ps, f" – „{s['temat']}”  ", 10)
                _tekst(ps, lokal["sale"][s["sala"]].upper(), 8, True, _rgb(k["akcent"]))
            for kom in w.cells:
                kom.paragraphs[-1].paragraph_format.space_after = Pt(5)
                kom.paragraphs[0].paragraph_format.space_before = Pt(5)
        _szerokosci(t, [3.4, 14.0])

    _stopka(doc, f"{lokal['nazwa']} · {lokal['kontakt']}")
    doc.save(wyjscie)


# ---------- plan obsługi (kalendarz obowiązków) ----------

def _szczegoly(o, dane):
    linie = []
    if o.get("osoby"):
        linie.append(f"Osoby: {o['osoby']}")
    linie += o.get("pozycje", [])
    if o.get("menu"):
        linie += menu_jako_linie(dane["menu"][o["menu"]])
    return linie


def _tabela_obowiazkow(doc, dane, wiersze, z_dzialem):
    lokal, k = dane["lokal"], dane["lokal"]["kolory"]
    kolumny = ["", "Godz.", "Dział", "Gdzie", "Co", "Szczegóły"] if z_dzialem else \
              ["", "Godz.", "Gdzie", "Co", "Szczegóły"]
    szer = [0.8, 2.2, 3.2, 3.0, 5.6, 11.3] if z_dzialem else [0.8, 2.2, 3.2, 6.4, 13.5]
    t = doc.add_table(rows=1, cols=len(kolumny))
    _ramki(t, k["linia"])
    _naglowek_tabeli_powtarzany(t.rows[0])
    for i, nazwa in enumerate(kolumny):
        kom = t.rows[0].cells[i]
        _cien(kom, k["tlo_naglowka"])
        _tekst(kom.paragraphs[0], nazwa, 9, True, _rgb(k["glowny"]))

    for typ, poz in wiersze:
        w = t.add_row()
        _nie_dziel_wiersza(w)
        c = iter(w.cells)
        if typ == "program":
            next(c)
            _tekst(next(c).paragraphs[0], godziny(poz), 9, kolor=SZARY, kursywa=True)
            if z_dzialem:
                _tekst(next(c).paragraphs[0], "Program gości", 8, kolor=SZARY, kursywa=True)
            sala = lokal["sale"].get(poz.get("sala"), "")
            if poz.get("sesje"):
                sala = ", ".join(dict.fromkeys(lokal["sale"][s["sala"]] for s in poz["sesje"]))
            _tekst(next(c).paragraphs[0], sala, 9, kolor=SZARY, kursywa=True)
            _tekst(next(c).paragraphs[0], poz["tytul"], 9, kolor=SZARY, kursywa=True)
            continue
        _tekst(next(c).paragraphs[0], "☐", 12)
        _tekst(next(c).paragraphs[0], godziny(poz), 10, True, _rgb(k["glowny"]))
        if z_dzialem:
            _tekst(next(c).paragraphs[0], lokal["dzialy"][poz["dzial"]], 9, True)
        _tekst(next(c).paragraphs[0], lokal["sale"].get(poz.get("miejsce"), ""), 9)
        _tekst(next(c).paragraphs[0], poz["zadanie"], 10, True)
        kom = next(c)
        for j, linia in enumerate(_szczegoly(poz, dane)):
            p = kom.paragraphs[0] if j == 0 else kom.add_paragraph()
            p.paragraph_format.space_after = Pt(1)
            _tekst(p, f"• {linia}", 9)
    _szerokosci(t, szer)
    return t


def plan_obslugi_docx(dane, wyjscie):
    lokal, k = dane["lokal"], dane["lokal"]["kolory"]
    _ustaw_fonty(lokal)
    doc = _nowy_dokument(poziomo=True)

    p = _akapit(doc, 0)
    _tekst(p, "PLAN OBSŁUGI", 9, True, _rgb(k["akcent"]))
    p = _akapit(doc, 2)
    _tekst(p, dane["nazwa"], 20, True, _rgb(k["glowny"]), FONT_TYTUL)
    p = _akapit(doc, 8)
    _tekst(p, f"{dane['klient']} · {zakres_dat(dane)} · {dane['liczba_osob']} os. · {lokal['nazwa']}", 10, kolor=SZARY)

    if dane.get("wycena"):
        w = wycena(dane["wycena"])
        t = doc.add_table(rows=1, cols=1)
        kom = t.rows[0].cells[0]
        _cien(kom, k["tlo_naglowka"])
        _tekst(kom.paragraphs[0], f"Wycena — {dane['wycena'].get('pakiet', '')}", 10, True, _rgb(k["glowny"]))
        for linia in w["linie"]:
            p = kom.add_paragraph()
            p.paragraph_format.space_after = Pt(1)
            _tekst(p, linia, 10, linia.startswith(("Razem", "Do zapłaty")))
        _akapit(doc, 4)

    if dane.get("do_potwierdzenia"):
        t = doc.add_table(rows=1, cols=1)
        kom = t.rows[0].cells[0]
        _cien(kom, "FFF4D6")
        _tekst(kom.paragraphs[0], "Do potwierdzenia przed imprezą", 10, True, _rgb(k["glowny"]))
        for punkt in dane["do_potwierdzenia"]:
            p = kom.add_paragraph()
            p.paragraph_format.space_after = Pt(1)
            _tekst(p, f"☐  {punkt}", 9)
        _akapit(doc, 4)

    def wiersze_dnia(dzien, dzial=None):
        obow = [o for o in dane["obowiazki"] if dzial is None or o["dzial"] == dzial]
        w = [("zadanie", o) for o in po_kolei(obow, dzien)]
        if dzial is None:
            w += [("program", p) for p in po_kolei(dane["program"], dzien)]
            # program przed obowiązkiem o tej samej godzinie — obsługa widzi, co dzieje się u gości
            w.sort(key=lambda x: (_minuty(x[1]["od"]), x[0] != "program"))
        return w

    for dzien in dni(dane):
        p = _akapit(doc, 3)
        p.paragraph_format.space_before = Pt(6)
        _tekst(p, f"{nazwa_dnia(dzien)} — wszystkie działy", 13, True, _rgb(k["glowny"]), FONT_TYTUL)
        _tabela_obowiazkow(doc, dane, wiersze_dnia(dzien), z_dzialem=True)

    for dzial, nazwa in lokal["dzialy"].items():
        if not any(o["dzial"] == dzial for o in dane["obowiazki"]):
            continue
        doc.add_page_break()
        p = _akapit(doc, 0)
        _tekst(p, f"PLAN OBSŁUGI · {dane['nazwa'].upper()}", 8, True, _rgb(k["akcent"]))
        p = _akapit(doc, 4)
        _tekst(p, nazwa, 20, True, _rgb(k["glowny"]), FONT_TYTUL)
        for dzien in dni(dane):
            w = wiersze_dnia(dzien, dzial)
            if not w:
                continue
            p = _akapit(doc, 3)
            p.paragraph_format.space_before = Pt(6)
            _tekst(p, nazwa_dnia(dzien), 13, True, _rgb(k["glowny"]), FONT_TYTUL)
            _tabela_obowiazkow(doc, dane, w, z_dzialem=False)

    _stopka(doc, f"{lokal['nazwa']} · plan obsługi: {dane['nazwa']} · ☐ = odhacz po wykonaniu")
    doc.save(wyjscie)


# ---------- wycena i ilości ----------

def zl(kwota):
    return f"{Decimal(kwota):,.2f}".replace(",", " ").replace(".", ",") + " zł"


def wycena(w):
    """Wycena przyjęcia z pakietu. Kwoty w Decimal, zaokrąglone do groszy."""
    dorosli, dzieci = int(w.get("doroslych", 0)), int(w.get("dzieci", 0))
    if dorosli < 0 or dzieci < 0:
        raise ValueError("Liczba gości nie może być ujemna.")
    cena = Decimal(str(w["cena_os"]))
    cena_dz = w.get("cena_dziecko")
    zadatek = Decimal(str(w.get("zadatek") or 0))
    if cena < 0 or zadatek < 0 or (cena_dz is not None and Decimal(str(cena_dz)) < 0):
        raise ValueError("Cena i zadatek nie mogą być ujemne.")
    razem = cena * dorosli
    linie = [f"Dorośli: {dorosli} × {zl(cena)} = {zl(razem)}"]
    if dzieci:
        if cena_dz is None:
            linie.append(f"Dzieci: {dzieci} × cena do ustalenia (nie wliczone)")
        else:
            kw = Decimal(str(cena_dz)) * dzieci
            razem += kw
            linie.append(f"Dzieci: {dzieci} × {zl(cena_dz)} = {zl(kw)}")
    razem = razem.quantize(Decimal("0.01"))
    do_zaplaty = max(razem - zadatek, Decimal("0.00")).quantize(Decimal("0.01"))
    linie += [f"Razem: {zl(razem)}", f"Zadatek: {zl(zadatek)}", f"Do zapłaty: {zl(do_zaplaty)}"]
    return {"razem": razem, "do_zaplaty": do_zaplaty, "linie": linie}


def ilosc(porcja, miara, osoby):
    """'300 ml × 45 os. = 13,5 l' — ilość dla kuchni."""
    suma = Decimal(str(porcja)) * osoby
    duza = {"g": "kg", "ml": "l"}.get(miara)
    if duza and suma >= 1000:
        wynik = f"{(suma / 1000).normalize():f} {duza}".replace(".", ",")
    else:
        wynik = f"{suma.normalize():f} {miara}".replace(".", ",")
    porcja_txt = f"{Decimal(str(porcja)).normalize():f}".replace(".", ",")
    return f"{porcja_txt} {miara} × {osoby} os. = {wynik}"


# ---------- fabryka: nowe przyjęcie z pakietu ----------

def _slug(tekst):
    t = unicodedata.normalize("NFKD", tekst.replace("ł", "l").replace("Ł", "L"))
    t = t.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40]


def _godz(start_min, po_min):
    m = (start_min + po_min) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def nowa_impreza(lokal_id, pakiet_id, dzien, godz, doroslych, klient, **opcje):
    """Zwraca dane nowego przyjęcia (dict) rozpisane z pakietu menu z pliku. Nic nie zapisuje."""
    pakiet = json.loads((KATALOG / "pakiety" / lokal_id / f"{pakiet_id}.json").read_text(encoding="utf-8"))
    return rozpisz_przyjecie(lokal_id, pakiet, dzien, godz, doroslych, klient, **opcje)


def rozpisz_przyjecie(lokal_id, pakiet, dzien, godz, doroslych, klient, dzieci=0, typ=None,
                      tort=None, zadatek=0, uwagi=None):
    """Fabryka: pakiet menu (dict) + parametry przyjęcia → pełne dane imprezy (program, obowiązki, wycena).
    Używają jej CLI (pakiety JSON) i panel (menu z bazy)."""
    pakiet_id = pakiet.get("id", "")
    if doroslych < 1 or dzieci < 0:
        raise ValueError("Przyjęcie musi mieć co najmniej 1 dorosłego, dzieci >= 0.")
    if not klient.strip():
        raise ValueError("Podaj klienta.")
    date.fromisoformat(dzien)
    start = _minuty(godz)
    goscie = doroslych + dzieci
    etapy = sorted(pakiet["etapy"], key=lambda e: e["po_min"])

    program, obowiazki, przed_startem = [], [], []
    for e in etapy:
        dania = e.get("dania", [])
        if e.get("tytul"):
            program.append({"dzien": dzien, "od": _godz(start, e["po_min"]), "tytul": e["tytul"], "sala": "sala", "opis": []})
            if przed_startem:
                program[-1]["opis"].append("Na stołach: " + " · ".join(przed_startem))
                przed_startem = []
        if dania:
            nazwy = " · ".join(d["danie"] for d in dania)
            if program:
                program[-1]["opis"].append(nazwy)
            else:
                przed_startem.append(nazwy)
        if e.get("dzial"):
            obowiazki.append({
                "dzien": dzien, "od": _godz(start, e["po_min"]), "dzial": e["dzial"], "miejsce": e.get("miejsce"),
                "zadanie": e["zadanie"], "osoby": f"{goscie} os.",
                "pozycje": [p.format(goscie=goscie) for p in e.get("pozycje", [])]
                           + [f"{d['danie']}: {ilosc(d['porcja'], d['miara'], goscie)}" if d.get("porcja")
                              else d["danie"] for d in dania],
            })

    if tort:
        program.append({"dzien": dzien, "od": tort, "tytul": "Tort", "sala": "sala"})
        obowiazki.append({"dzien": dzien, "od": _godz(_minuty(tort), -15), "dzial": "sala", "miejsce": "sala",
                          "zadanie": f"Tort o {tort} — przygotować podanie",
                          "pozycje": [f"Talerzyki deserowe i widelczyki — {goscie} os.", "Nóż i łopatka do tortu",
                                      "Kto dostarcza tort i o której — do potwierdzenia"]})
    if uwagi:
        obowiazki.append({"dzien": dzien, "od": _godz(start, -120), "dzial": "kuchnia", "miejsce": "kuchnia",
                          "zadanie": "Diety i alergie — UWAGA", "pozycje": [uwagi]})

    do_potw = ["Godziny etapów to propozycja z pakietu — ustal z klientem i popraw w impreza.json.",
               "Porcje na osobę to założenia z kalkulatora — potwierdź z kuchnią."]
    if dzieci:
        do_potw.append("Dzieci liczone w ilościach jako pełna porcja.")
        if pakiet.get("cena_dziecko") is None:
            do_potw.append("Cena dla dzieci nieustalona — nie wliczona do wyceny.")
    if any(d.get("porcja") is None for e in etapy for d in e.get("dania", [])):
        do_potw.append("Część dań nie ma porcji — kuchnia ustala ilość sama.")
    if any("do ustalenia" in d["danie"] for e in etapy for d in e.get("dania", [])):
        do_potw.append("W menu są pozycje „do ustalenia” — dobierz z kuchnią.")

    nazwa = f"{typ.capitalize()} — {klient}" if typ else f"Przyjęcie — {klient}"
    return {
        "lokal": lokal_id, "nazwa": nazwa, "klient": klient, "typ": typ,
        "od": dzien, "do": dzien, "liczba_osob": goscie,
        "zrodla": [f"Menu: {pakiet['nazwa']}" + (f" ({pakiet['_zrodlo']})" if pakiet.get("_zrodlo") else "")],
        "grupy": {}, "program": sorted(program, key=lambda p: _minuty(p["od"])), "menu": {},
        "obowiazki": obowiazki,
        "wycena": {"pakiet": f"{pakiet['nazwa']} – {pakiet['cena_os']} zł/os.", "cena_os": pakiet["cena_os"],
                   "cena_dziecko": pakiet.get("cena_dziecko"), "doroslych": doroslych, "dzieci": dzieci,
                   "zadatek": zadatek},
        "do_potwierdzenia": do_potw,
    }


def zapisz_nowa(dane):
    katalog = KATALOG / "imprezy" / f"{dane['od']}-{_slug(dane['klient'])}"
    plik = katalog / "impreza.json"
    if plik.exists():
        raise SystemExit(f"Już istnieje: {plik} — nie nadpisuję (popraw go albo usuń).")
    katalog.mkdir(parents=True)
    plik.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    return plik


# ---------- kalendarz miesiąca ----------

def imprezy_miesiaca(lokal_id, miesiac):
    wynik = []
    for plik in sorted((KATALOG / "imprezy").glob("*/impreza.json")):
        d = json.loads(plik.read_text(encoding="utf-8"))
        if d["lokal"] == lokal_id and d["od"].startswith(miesiac):
            wynik.append(d)
    return sorted(wynik, key=lambda d: (d["od"], min((p["od"] for p in d["program"]), default="")))


def kalendarz_miesiaca_docx(lokal_id, miesiac, wyjscie):
    lokal = json.loads((KATALOG / "lokale" / f"{lokal_id}.json").read_text(encoding="utf-8"))
    k = lokal["kolory"]
    _ustaw_fonty(lokal)
    doc = _nowy_dokument(poziomo=True)
    rok, mies = map(int, miesiac.split("-"))
    nazwy_mies = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień",
                  "Wrzesień", "Październik", "Listopad", "Grudzień"]
    p = _akapit(doc, 0)
    _tekst(p, f"KALENDARZ PRZYJĘĆ · {lokal['nazwa'].upper()}", 9, True, _rgb(k["akcent"]))
    p = _akapit(doc, 8)
    _tekst(p, f"{nazwy_mies[mies - 1]} {rok}", 22, True, _rgb(k["glowny"]), FONT_TYTUL)

    imprezy = imprezy_miesiaca(lokal_id, miesiac)
    kolumny = ["Dzień", "Start", "Przyjęcie", "Goście", "Pakiet", "Razem", "Zadatek", "Do potwierdzenia"]
    szer = [3.6, 1.6, 6.0, 1.8, 4.6, 2.6, 2.4, 3.5]
    t = doc.add_table(rows=1, cols=len(kolumny))
    _ramki(t, k["linia"])
    _naglowek_tabeli_powtarzany(t.rows[0])
    for i, n in enumerate(kolumny):
        _cien(t.rows[0].cells[i], k["tlo_naglowka"])
        _tekst(t.rows[0].cells[i].paragraphs[0], n, 9, True, _rgb(k["glowny"]))
    for d in imprezy:
        w = wycena(d["wycena"]) if d.get("wycena") else None
        wartosci = [nazwa_dnia(d["od"]), min((p["od"] for p in d["program"]), default="—"), d["nazwa"],
                    str(d["liczba_osob"]), d.get("wycena", {}).get("pakiet", "—"),
                    zl(w["razem"]) if w else "—", zl(d["wycena"].get("zadatek") or 0) if w else "—",
                    f"{len(d.get('do_potwierdzenia', []))} spraw" if d.get("do_potwierdzenia") else "—"]
        r = t.add_row()
        _nie_dziel_wiersza(r)
        for i, v in enumerate(wartosci):
            _tekst(r.cells[i].paragraphs[0], v, 10, i in (0, 2))
    if not imprezy:
        _tekst(_akapit(doc), "Brak przyjęć w tym miesiącu.", 10, kolor=SZARY)
    _szerokosci(t, szer)
    _stopka(doc, f"{lokal['nazwa']} · kalendarz przyjęć · wygenerowano {date.today().isoformat()}")
    doc.save(wyjscie)


def generuj(sciezka_impreza):
    dane = wczytaj(sciezka_impreza)
    bledy = sprawdz(dane)
    if bledy:
        raise SystemExit("Błędy w danych imprezy:\n- " + "\n- ".join(bledy))
    katalog = Path(sciezka_impreza).parent / "dokumenty"
    katalog.mkdir(exist_ok=True)
    agenda_docx(dane, katalog / "agenda.docx")
    plan_obslugi_docx(dane, katalog / "plan-obslugi.docx")
    return katalog


def main(argv):
    if len(argv) == 1 and argv[0].endswith(".json"):
        return print(generuj(argv[0]))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("nowa")
    for a in ("lokal", "pakiet", "data", "godz"):
        n.add_argument(a)
    n.add_argument("doroslych", type=int)
    n.add_argument("klient")
    n.add_argument("--dzieci", type=int, default=0)
    n.add_argument("--typ")
    n.add_argument("--tort")
    n.add_argument("--zadatek", type=Decimal, default=Decimal(0))
    n.add_argument("--uwagi")
    m = sub.add_parser("miesiac")
    m.add_argument("lokal")
    m.add_argument("miesiac")
    a = ap.parse_args(argv)
    if a.cmd == "nowa":
        dane = nowa_impreza(a.lokal, a.pakiet, a.data, a.godz, a.doroslych, a.klient, a.dzieci, a.typ,
                            a.tort, str(a.zadatek), a.uwagi)
        plik = zapisz_nowa(dane)
        print(plik)
        print(generuj(plik))
    else:
        wyj = KATALOG / "imprezy" / f"kalendarz-{a.lokal}-{a.miesiac}.docx"
        kalendarz_miesiaca_docx(a.lokal, a.miesiac, wyj)
        print(wyj)


if __name__ == "__main__":
    main(sys.argv[1:])
