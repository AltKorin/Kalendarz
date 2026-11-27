"""Umowa o organizację imprezy okolicznościowej (.docx) wypełniona danymi przyjęcia.

Treść: przyjecia/dane/umowa_impreza.json (wzór z projektu Malbork, bez danych tamtej restauracji). Pola {…} bierzemy
z przyjęcia i lokalu; czego system nie wie (dane rejestrowe firmy, adres klienta, godzina końca), zostaje w [nawiasach].
Na górze ramka „WZÓR — dostosuj do swojego lokalu”, bo to punkt wyjścia, nie sprawdzona umowa.

Prawa:
- każde pole {…} z pliku treści dostaje wartość albo „[...]” — nigdy nie zostaje surowe {pole} ani pusty tekst;
- kwoty jak w wycenie przyjęcia (kalendarz.wycena), zero = „[...] zł” (cena nieustalona, nie „0,00 zł”).
"""
import json
import os
import re
from functools import cache
from io import BytesIO
from pathlib import Path

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

import kalendarz as k

from . import uslugi

TRESC = Path(__file__).parent / "dane" / "umowa_impreza.json"
NR = "[IMP/RRRR/NN]"
NIEZNANE = "[...]"
RAMKA = ("**WZÓR — przed wysłaniem dostosuj do swojego lokalu.** Umowę wypełniono danymi przyjęcia z Kalendarza. "
         "Uzupełnij pola w [nawiasach] (dane firmy, adres klienta, godzina zakończenia), sprawdź zasady (alkohol, "
         "dekoracje, odwołanie) i dopasuj je do swojego lokalu, a w razie wątpliwości daj umowę do sprawdzenia prawnikowi. "
         "Tę ramkę usuń przed wysłaniem.")


@cache
def tresc():
    return json.loads(TRESC.read_text(encoding="utf-8"))


def _zl(kwota):
    return k.zl(kwota) if kwota else f"{NIEZNANE} zł"


def pola(p):
    """Przyjęcie → wartości pól {…} z pliku treści."""
    lokal, w = p.lokal, uslugi.wycena(p)
    data = f"{p.data:%d.%m.%Y}" + (f"–{p.koniec:%d.%m.%Y}" if p.koniec and p.koniec != p.data else "")
    jest_liczba = p.doroslych > 0
    return {
        "rodzaj": "[rodzaj imprezy]" if p.rodzaj == "inne" else p.get_rodzaj_display().lower(),
        "data": data,
        "od": p.start.strftime("%H:%M") if p.start else "[GG:MM]",
        "sala": p.sale or "[nazwa]",
        "lokal": ", ".join(x for x in (lokal.nazwa, lokal.podpis) if x),
        "doroslych": str(p.doroslych) if jest_liczba else NIEZNANE,
        "dzieci": str(p.dzieci) if jest_liczba else NIEZNANE,
        "cena_os": _zl(p.cena_os),
        "cena_dziecko": f"{NIEZNANE} zł" if p.cena_dziecko is None else k.zl(p.cena_dziecko),
        "menu": f" (menu „{p.menu.nazwa}”)" if p.menu_id else "",
        "razem": _zl(w["razem"]),
        "zadatek": _zl(p.zadatek),
        "kontakt": lokal.kontakt or "[e-mail]",
    }


# ---------- docx ----------

def _tekst(akapit, s, rozmiar=10):
    """Tekst z **pogrubieniami**."""
    for i, kawalek in enumerate(re.split(r"\*\*", s)):
        if kawalek:
            k._tekst(akapit, kawalek, rozmiar, pogrubiony=i % 2 == 1)
    return akapit


def _akapit(doc, s="", rozmiar=10, po=4, wyrownanie=WD_ALIGN_PARAGRAPH.JUSTIFY):
    a = k._akapit(doc, po)
    a.alignment = wyrownanie
    return _tekst(a, s, rozmiar)


def _naglowek(doc, s, kolor, rozmiar=11.5, przed=10):
    a = k._akapit(doc, 4)
    a.paragraph_format.space_before = Pt(przed)
    a.paragraph_format.keep_with_next = True
    k._tekst(a, s, rozmiar, pogrubiony=True, kolor=kolor, font=k.FONT_TYTUL)
    return a


def _punkt(doc, nr, s):
    a = _akapit(doc, f"{nr}.\t{s}", po=2)
    pf = a.paragraph_format
    pf.left_indent, pf.first_line_indent = Pt(18), Pt(-18)
    pf.tab_stops.add_tab_stop(Pt(18))
    return a


def _ramka(akapit, kolor):
    pbdr = OxmlElement("w:pBdr")
    for bok in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{bok}")
        for kl, v in (("val", "single"), ("sz", "12"), ("space", "4"), ("color", kolor)):
            b.set(qn(f"w:{kl}"), v)
        pbdr.append(b)
    akapit._p.get_or_add_pPr().append(pbdr)


def _numer_strony(doc, etykieta):
    a = doc.sections[0].footer.paragraphs[0]
    a.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for txt, pole in ((f"{etykieta} – strona ", "PAGE"), (" z ", "NUMPAGES")):
        k._tekst(a, txt, 8, kolor=k.SZARY)
        r = k._tekst(a, "", 8, kolor=k.SZARY)
        for typ, el in (("begin", None), (None, pole), ("separate", None), (None, "1"), ("end", None)):
            if typ:
                e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), typ)
            elif el == pole:
                e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = f" {pole} "
            else:
                e = OxmlElement("w:t"); e.text = el
            r._r.append(e)


def _podpisy(doc, strony=("Restauracja", "Zamawiający")):
    t = doc.add_table(rows=2, cols=2)
    for i, kto in enumerate(strony):
        for wiersz, txt, rozmiar in ((0, "." * 48, 10), (1, f"{kto} (data i podpis)", 8.5)):
            a = t.cell(wiersz, i).paragraphs[0]
            a.alignment = WD_ALIGN_PARAGRAPH.CENTER
            a.paragraph_format.space_before = Pt(24 if wiersz == 0 else 0)
            a.paragraph_format.keep_with_next = wiersz == 0  # linia i podpis pod nią na jednej stronie
            k._tekst(a, txt, rozmiar)
    for w in t.rows:
        k._nie_dziel_wiersza(w)


def _tabela(doc, naglowki, wiersze, szer, kolor, tlo):
    t = doc.add_table(rows=1, cols=len(naglowki))
    for c, h in zip(t.rows[0].cells, naglowki):
        k._tekst(c.paragraphs[0], h, 9, pogrubiony=True)
        k._cien(c, tlo)
    for w in wiersze:
        for c, v in zip(t.add_row().cells, w):
            k._tekst(c.paragraphs[0], v, 9)
    k._ramki(t, kolor)
    k._szerokosci(t, szer)
    return t


def _menu(dane, goscie, wzor):
    """Wiersze Załącznika 1: etapy z agendy gości (tytuł + dania) albo puste pozycje z wzoru."""
    puste = [(x, NIEZNANE, NIEZNANE, f"{NIEZNANE} zł") for x in wzor]
    if not dane:
        return puste
    dania = [(x["tytul"], ", ".join(x["opis"]), goscie, "w cenie menu") for x in dane["program"] if x.get("opis")]
    return dania + [w for w in puste if w[0] in ("Napoje bez alkoholu", "Alkohol", "Usługi dodatkowe")]


def umowa_docx(p):
    """Przyjęcie → (bajty .docx, nazwa pliku)."""
    t, f = tresc(), pola(p)
    lokal = p.lokal.jako_dane()
    k._ustaw_fonty(lokal)
    kolor = k._rgb(lokal["kolory"]["glowny"])
    doc = k._nowy_dokument()
    _numer_strony(doc, f"Umowa nr {NR}")

    if lokal["logo"] and os.path.exists(lokal["logo"]):
        a = k._akapit(doc, 6)
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        a.add_run().add_picture(lokal["logo"], height=Cm(2.2))
    _ramka(_akapit(doc, RAMKA, 9, po=12), lokal["kolory"]["akcent"])
    tytul = _akapit(doc, wyrownanie=WD_ALIGN_PARAGRAPH.CENTER, po=0)
    k._tekst(tytul, f"Umowa nr {NR}", 18, pogrubiony=True, kolor=kolor, font=k.FONT_TYTUL)
    _akapit(doc, "o organizację imprezy okolicznościowej", 12, po=12, wyrownanie=WD_ALIGN_PARAGRAPH.CENTER)
    _akapit(doc, "zawarta w dniu [DD.MM.RRRR] w [miejscowość] pomiędzy:")
    _akapit(doc, f"**{p.lokal.nazwa}** — [nazwa firmy albo imię i nazwisko przedsiębiorcy], [adres siedziby], NIP [...], "
                 "REGON [...][, KRS ...], reprezentowaną przez [imię i nazwisko – funkcja], zwaną dalej **Restauracją**,")
    _akapit(doc, "a")
    _akapit(doc, f"{p.klient}, [adres], [NIP – tylko jeśli potrzebny do faktury], tel. {p.telefon or NIEZNANE}, "
                 "e-mail [...], zwanym dalej **Zamawiającym**.", po=6)

    for i, par in enumerate(t["paragrafy"]):
        _naglowek(doc, par["naglowek"], kolor)
        ostatni = i == len(t["paragrafy"]) - 1
        for nr, s in enumerate(par["punkty"], 1):
            _punkt(doc, nr, s.format(**f)).paragraph_format.keep_with_next = ostatni
    _podpisy(doc)

    z = _naglowek(doc, "Załącznik nr 1 – menu, usługi dodatkowe, harmonogram", kolor, 12)
    z.paragraph_format.page_break_before = True
    goscie = f"{p.goscie} os." if p.doroslych else NIEZNANE
    tlo = lokal["kolory"].get("tlo_naglowka", "EEEEEE")
    dane = uslugi.dane_przyjecia(p)
    _tabela(doc, ["Pozycja", "Opis", "Ilość / osoby", "Cena brutto"], _menu(dane, goscie, t["menu_wiersze"]),
            [3.6, 8.0, 2.6, 3.2], lokal["kolory"]["linia"], tlo)
    _naglowek(doc, "Harmonogram", kolor)
    program = [(x["od"], x["tytul"]) for x in dane["program"]] if dane else [("[GG:MM]", h) for h in t["harmonogram"]]
    _tabela(doc, ["Godzina", "Punkt programu"], program, [2.6, 14.8], lokal["kolory"]["linia"], tlo)
    _akapit(doc, "", po=6)
    _akapit(doc, "Uwagi (diety, alergie, dekoracje):", po=2)
    if p.uwagi:
        _akapit(doc, p.uwagi, po=2)
    for _ in range(2):
        _akapit(doc, "." * 110, po=2).paragraph_format.keep_with_next = True
    _podpisy(doc)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue(), f"{p.data:%Y-%m-%d} {k._slug(p.klient)} - umowa.docx"
