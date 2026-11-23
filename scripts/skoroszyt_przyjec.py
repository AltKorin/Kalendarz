"""Skoroszyt Excel „Kalendarz przyjęć” do samodzielnego wypełniania przez restaurację (wersja przed panelem).

Użycie:  python3 scripts/skoroszyt_przyjec.py demo
Wynik:   dla-klienta/<lokal>/Kalendarz przyjęć – <nazwa>.xlsx

Dane bierze z lokale/<lokal>.json i pakiety/<lokal>/*.json — zmiana menu = zmiana JSON i ponowne uruchomienie
(albo Marcin poprawia zakładkę Menu w Excelu). Formuły tylko z Excela 2007 (INDEX/MATCH/COUNTIFS), bez FILTER/XLOOKUP.
"""
import json
import sys
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.drawing.image import Image as XLImage
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from PIL import Image

KATALOG = Path(__file__).resolve().parent.parent
WIERSZE_PRZYJEC = 200      # ponytail: 200 przyjęć w jednym pliku; więcej → nowy plik na rok albo panel
WIERSZE_MENU = 300
WIERSZE_AGENDY = 40
WIERSZE_PLANU = 70
RODZAJE = ["komunia", "chrzciny", "wesele", "urodziny", "jubileusz", "stypa", "spotkanie firmowe", "inne"]
STATUSY = ["wstępna", "potwierdzona", "odbyła się", "odwołana"]
DNI = '"pon.","wt.","śr.","czw.","pt.","sob.","niedz."'
DATA_PL = '[$-415]dddd, d mmmm yyyy'


def main(lokal_id):
    lokal = json.loads((KATALOG / "lokale" / f"{lokal_id}.json").read_text(encoding="utf-8"))
    pakiety = [json.loads(p.read_text(encoding="utf-8"))
               for p in sorted((KATALOG / "pakiety" / lokal_id).glob("*.json"))]
    k = lokal["kolory"]
    fT, fX = lokal.get("fonty", {}).get("tytul", "Georgia"), lokal.get("fonty", {}).get("tekst", "Calibri")

    def font(rozmiar=11, bold=False, kolor="000000", tytul=False, italic=False):
        return Font(name=fT if tytul else fX, size=rozmiar, bold=bold, color=kolor, italic=italic)

    WPIS = PatternFill("solid", fgColor="FFF4D6")
    NAGL = PatternFill("solid", fgColor=k["tlo_naglowka"])
    linia = Side(style="thin", color=k["linia"])
    DOL = Border(bottom=linia)
    ZAWIJ = Alignment(wrap_text=True, vertical="top")
    GORA = Alignment(vertical="top")

    wb = Workbook()

    # ---------- Przyjęcia ----------
    ws = wb.active
    ws.title = "Przyjęcia"
    kol = [  # nagłówek, szerokość, wpisuje Marcin?
        ("Nr", 5, False), ("Data", 12, True), ("Dzień", 7, False), ("Start", 7, True), ("Klient", 24, True),
        ("Telefon", 13, True), ("Rodzaj", 15, True), ("Dorośli", 8, True), ("Dzieci", 7, True),
        ("Menu", 11, True), ("Cena/os. wg menu", 10, False), ("Cena/os. inna", 9, True),
        ("Cena dziecko", 9, True), ("Tort (godz.)", 8, True), ("Zadatek", 10, True),
        ("Diety, alergie, uwagi", 34, True), ("Status", 13, True), ("Goście", 7, False),
        ("Razem", 12, False), ("Do zapłaty", 12, False), ("Miesiąc", 9, False),
    ]
    ws["A1"] = f"Kalendarz przyjęć — {lokal['nazwa']}"
    ws["A1"].font = font(18, True, k["glowny"], tytul=True)
    ws["A2"] = ("Żółte kolumny wypełniasz Ty, białe liczą się same. Jeden wiersz = jedno przyjęcie. "
                "Wiersz nr 1 to PRZYKŁAD — nadpisz go. Agendę i plan obsługi drukujesz z kolejnych zakładek: "
                "wpisz tam numer przyjęcia.")
    ws["A2"].font = font(10, italic=True, kolor="555555")
    ws.merge_cells("A2:T2")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 30
    H = 4
    for i, (n, szer, wpis) in enumerate(kol, start=1):
        c = ws.cell(H, i, n)
        c.font = font(10, True, k["glowny"])
        c.fill = WPIS if wpis else NAGL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = DOL
        ws.column_dimensions[c.column_letter].width = szer
    ws.row_dimensions[H].height = 30
    ws["K4"].comment = Comment("Cena z zakładki Menu (cennik). Wpisz „Cena/os. inna”, jeśli ustaliłeś inną.", "Kalendarz")
    ws["M4"].comment = Comment("Puste = dzieci nie są wliczane do kwoty (cena dla dzieci nieustalona w menu).", "Kalendarz")

    pierwszy, ostatni = H + 1, H + WIERSZE_PRZYJEC
    for r in range(pierwszy, ostatni + 1):
        ws[f"A{r}"] = r - H
        ws[f"C{r}"] = f'=IF(B{r}="","",CHOOSE(WEEKDAY(B{r},2),{DNI}))'
        ws[f"K{r}"] = f'=IF(J{r}="","",IFERROR(INDEX(Menu!$N:$N,MATCH(J{r},Menu!$M:$M,0)),""))'
        ws[f"R{r}"] = f'=IF(H{r}="","",H{r}+N(I{r}))'
        ws[f"S{r}"] = f'=IF(H{r}="","",IF(L{r}<>"",L{r},N(K{r}))*H{r}+N(M{r})*N(I{r}))'
        ws[f"T{r}"] = f'=IF(S{r}="","",MAX(S{r}-N(O{r}),0))'
        ws[f"U{r}"] = f'=IF(B{r}="","",YEAR(B{r})&"-"&TEXT(MONTH(B{r}),"00"))'
        ws[f"B{r}"].number_format = "dd.mm.yyyy"
        for c in ("D", "N"):
            ws[f"{c}{r}"].number_format = "hh:mm"
        for c in ("K", "L", "M", "O", "S", "T"):
            ws[f"{c}{r}"].number_format = '#,##0.00 "zł"'
        for c in "ABCDEFGHIJKLMNOPQRSTU":
            ws[f"{c}{r}"].font = font(10)
            ws[f"{c}{r}"].border = DOL
        ws[f"P{r}"].alignment = ZAWIJ

    # przykład (wiersz 1)
    from datetime import date, time
    przyklad = {"B": date(2026, 11, 22), "D": time(14, 0), "E": "PRZYKŁAD Kowalscy", "F": "500 100 200",
                "G": "komunia", "H": 38, "I": 6, "J": pakiety[0]["nazwa"].replace("Menu imprezowe nr ", "Menu "),
                "N": time(17, 30), "O": 1000, "P": "Bez glutenu: 2 os.", "Q": "wstępna"}
    for c, v in przyklad.items():
        ws[f"{c}{pierwszy}"] = v
        ws[f"{c}{pierwszy}"].font = font(10, italic=True, kolor="7F7F7F")

    def lista(komorki, wartosci, arkusz=ws):
        dv = DataValidation(type="list", formula1='"' + ",".join(wartosci) + '"', allow_blank=True)
        dv.error, dv.errorTitle = "Wybierz z listy.", "Kalendarz"
        arkusz.add_data_validation(dv)
        dv.add(komorki)

    nazwy_menu = [p["nazwa"].replace("Menu imprezowe nr ", "Menu ") for p in pakiety]
    lista(f"G{pierwszy}:G{ostatni}", RODZAJE)
    lista(f"Q{pierwszy}:Q{ostatni}", STATUSY)
    dv_menu = DataValidation(type="list", formula1=f"=Menu!$M$5:$M$20", allow_blank=True)
    ws.add_data_validation(dv_menu)
    dv_menu.add(f"J{pierwszy}:J{ostatni}")
    for zakres, typ in ((f"H{pierwszy}:I{ostatni}", "whole"), (f"L{pierwszy}:M{ostatni}", "decimal"),
                        (f"O{pierwszy}:O{ostatni}", "decimal")):
        dv = DataValidation(type=typ, operator="greaterThanOrEqual", formula1="0", allow_blank=True)
        dv.error = "Liczba nie może być ujemna."
        ws.add_data_validation(dv)
        dv.add(zakres)
    ws.freeze_panes = ws[f"E{pierwszy}"]
    ws.auto_filter.ref = f"A{H}:U{ostatni}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{H}:{H}"

    # ---------- Menu ----------
    wm = wb.create_sheet("Menu")
    wm["A1"] = "Menu i przebieg przyjęcia"
    wm["A1"].font = font(16, True, k["glowny"], tytul=True)
    wm["A2"] = ("Możesz zmieniać dania, porcje i minuty. Wiersze jednego menu trzymaj razem i w kolejności godzin. "
                "„Minuty od startu”: -20 = 20 min przed przyjazdem gości. Nowe menu = nowa nazwa w kolumnie A "
                "+ wiersz w cenniku obok. Porcje i godziny to założenia — sprawdź z kuchnią.")
    wm["A2"].font = font(10, italic=True, kolor="555555")
    wm.merge_cells("A2:I2")
    wm["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    wm.row_dimensions[2].height = 45
    nm = ["Menu", "Minuty od startu", "Etap (dla gości)", "Dział", "Zadanie (obsługa)", "Danie / pozycja",
          "Porcja / os.", "Miara", "Dla gości", "_klucz_gosci", "_klucz_wszystko"]
    szer_m = [11, 9, 18, 14, 32, 58, 9, 7, 8, 14, 14]
    for i, (n, s) in enumerate(zip(nm, szer_m), start=1):
        c = wm.cell(4, i, n)
        c.font = font(10, True, k["glowny"])
        c.fill = NAGL if n.startswith("_") else WPIS
        c.border = DOL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        wm.column_dimensions[c.column_letter].width = s
    wm.column_dimensions["J"].hidden = wm.column_dimensions["K"].hidden = True

    r = 5
    dzialy = lokal["dzialy"]
    for p, nazwa in zip(pakiety, nazwy_menu):
        etapy = sorted(p["etapy"], key=lambda e: e["po_min"])
        # dania podane przed startem (zimna płyta) goście widzą pod pierwszym etapem (Powitanie)
        etykieta = next((e["tytul"] for e in etapy if e.get("tytul")), "Na stołach")
        uzyte = set()
        for e in etapy:
            if e.get("tytul"):
                etykieta = e["tytul"]
            wiersze = []
            if e.get("dania"):
                wiersze = [(d["danie"], d["porcja"], d["miara"], "TAK") for d in e["dania"]]
            elif e.get("pozycje"):
                wiersze = [(x.replace("na {goscie} os.", "dla wszystkich gości").replace(" — {goscie} os.", ""),
                            None, None, "NIE") for x in e["pozycje"]]
            if e.get("tytul") and not e.get("dania") and e["tytul"] not in uzyte:
                wiersze = [("", None, None, "TAK")] + wiersze
            if any(w[3] == "TAK" for w in wiersze):
                uzyte.add(etykieta)
            for danie, porcja, miara, gosc in wiersze:
                for col, v in zip("ABCDEFGHI", (nazwa, e["po_min"], etykieta, dzialy.get(e.get("dzial"), ""),
                                                e.get("zadanie", ""), danie, porcja, miara, gosc)):
                    wm[f"{col}{r}"] = v
                r += 1
    for rr in range(5, 5 + WIERSZE_MENU):
        wm[f"J{rr}"] = f'=IF(AND(A{rr}<>"",I{rr}="TAK"),A{rr}&"|"&COUNTIFS(A$5:A{rr},A{rr},I$5:I{rr},"TAK"),"")'
        wm[f"K{rr}"] = f'=IF(A{rr}<>"",A{rr}&"|"&COUNTIF(A$5:A{rr},A{rr}),"")'
        for col in "ABCDEFGHI":
            wm[f"{col}{rr}"].font = font(10)
            wm[f"{col}{rr}"].border = DOL
        wm[f"F{rr}"].alignment = ZAWIJ
    lista(f"I5:I{4 + WIERSZE_MENU}", ["TAK", "NIE"], wm)
    lista(f"D5:D{4 + WIERSZE_MENU}", list(dzialy.values()), wm)
    lista(f"H5:H{4 + WIERSZE_MENU}", ["g", "ml", "szt."], wm)

    # cennik
    for i, (n, s) in enumerate(zip(["Menu (nazwa)", "Cena / os.", "Skąd"], [12, 10, 40]), start=13):
        c = wm.cell(4, i, n)
        c.font = font(10, True, k["glowny"])
        c.fill = WPIS
        c.border = DOL
        wm.column_dimensions[c.column_letter].width = s
    wm["M3"] = "Cennik"
    wm["M3"].font = font(12, True, k["glowny"], tytul=True)
    for i, (p, nazwa) in enumerate(zip(pakiety, nazwy_menu)):
        wm[f"M{5 + i}"], wm[f"N{5 + i}"] = nazwa, p["cena_os"]
        wm[f"O{5 + i}"] = "oferta restauracji (kartka kuchni 18.11.2026)"
        wm[f"N{5 + i}"].number_format = '#,##0.00 "zł"'
    wm.freeze_panes = "A5"

    # ---------- wspólne: wybór przyjęcia ----------
    P = "Przyjęcia"

    def z_przyjecia(kolumna, wiersz_wyb="$Z$1"):
        return f'INDEX({P}!${kolumna}:${kolumna},{wiersz_wyb})'

    def naglowek_wydruku(wsx, tytul_mały, poziomo):
        wsx["Y1"], wsx["Z1"] = "_wiersz", f'=IFERROR(MATCH($C$2,{P}!$A:$A,0),"")'
        wsx["Y2"], wsx["Z2"] = "_menu", f'=IF($Z$1="","",{z_przyjecia("J")})'
        wsx["Y3"], wsx["Z3"] = "_start", f'=IF($Z$1="","",{z_przyjecia("D")})'
        wsx["Y4"], wsx["Z4"] = "_goscie", f'=IF($Z$1="","",N({z_przyjecia("R")}))'
        wsx.column_dimensions["Y"].hidden = wsx.column_dimensions["Z"].hidden = True
        wsx["B1"] = "Wpisz numer przyjęcia z zakładki Przyjęcia ↓  (ta część się nie drukuje)"
        wsx["B1"].font = font(10, True, k["akcent"])
        wsx["C2"] = 1
        wsx["C2"].fill = WPIS
        wsx["C2"].font = font(12, True)
        wsx["D2"] = f'=IF($Z$1="","← nie ma takiego numeru",{z_przyjecia("E")}&"  ·  "&TEXT({z_przyjecia("B")},"dd.mm.yyyy"))'
        wsx["D2"].font = font(10, kolor="7F7F7F")
        logo = KATALOG / "lokale" / lokal["logo"] if lokal.get("logo") else None
        if logo:
            im = Image.open(logo)
            im.thumbnail((400, 400))
            buf = BytesIO()
            im.save(buf, "PNG")
            xl = XLImage(buf)
            xl.height, xl.width = 110, int(110 * im.width / im.height)
            wsx.add_image(xl, "C4")
        wsx["B11"] = tytul_mały
        wsx["B11"].font = font(9, True, k["akcent"])
        wsx["B12"] = f'=IF($Z$1="","Nie ma przyjęcia o tym numerze",PROPER({z_przyjecia("G")})&" — "&{z_przyjecia("E")})'
        wsx["B12"].font = font(20, True, k["glowny"], tytul=True)
        wsx["B13"] = f'=IF($Z$1="","",{z_przyjecia("B")})'
        wsx["B13"].number_format = DATA_PL
        wsx["B13"].font = font(11, kolor="555555")
        wsx["B13"].alignment = Alignment(horizontal="left")
        wsx.merge_cells("B13:F13")
        wsx.oddFooter.left.text = f"{lokal['nazwa']} · {lokal['kontakt']}"
        wsx.oddFooter.left.size = 8
        wsx.oddFooter.right.text = "&P / &N"
        wsx.oddFooter.right.size = 8
        wsx.page_setup.orientation = "landscape" if poziomo else "portrait"
        wsx.page_setup.paperSize = wsx.PAPERSIZE_A4
        wsx.page_setup.fitToWidth, wsx.page_setup.fitToHeight = 1, 0
        wsx.sheet_properties.pageSetUpPr.fitToPage = True
        wsx.sheet_view.showGridLines = False
        dv = DataValidation(type="whole", operator="between", formula1="1", formula2=str(WIERSZE_PRZYJEC))
        dv.error = f"Numer przyjęcia 1–{WIERSZE_PRZYJEC}."
        wsx.add_data_validation(dv)
        dv.add("C2")

    def obszar(wsx, formula, zapas):
        """Obszar wydruku rośnie z liczbą pozycji wybranego menu (bez pustych stron).
        ponytail: dynamiczny Print_Area działa w Excelu; gdyby ktoś go nadpisał w Ustawieniach strony, zostaje stały."""
        wsx.defined_names["_xlnm.Print_Area"] = DefinedName("_xlnm.Print_Area", attr_text=formula)

    # ---------- Agenda ----------
    wa = wb.create_sheet("Agenda")
    naglowek_wydruku(wa, "AGENDA", poziomo=False)
    for col, s in zip("ABCDEFG", [2, 9, 20, 62, 2, 2, 2]):
        wa.column_dimensions[col].width = s
    wa["B13"].value = f'=IF($Z$1="","",{z_przyjecia("B")})'
    wa["B14"] = f'=IF(N({z_przyjecia("N")})=0,"","Tort: "&TEXT({z_przyjecia("N")},"hh:mm"))'
    wa["B14"].font = font(11, True, k["akcent"])
    start = 16
    for col, n in zip("BCD", ["Godz.", "", ""]):
        wa[f"{col}{start - 1}"].border = Border(bottom=linia)
    for i in range(1, WIERSZE_AGENDY + 1):
        r = start + i - 1
        # ukryte: indeks w Menu i etykieta etapu
        wa[f"X{r}"] = f'=IFERROR(MATCH($Z$2&"|"&{i},Menu!$J:$J,0),"")'
        wa[f"W{r}"] = f'=IF(X{r}="","",INDEX(Menu!$C:$C,X{r}))'
        nowy = f'AND(X{r}<>"",W{r}<>' + (f'W{r - 1}' if i > 1 else '"#"') + ')'
        wa[f"B{r}"] = f'=IF({nowy},MOD($Z$3+MAX(0,INDEX(Menu!$B:$B,X{r}))/1440,1),"")'
        wa[f"C{r}"] = f'=IF({nowy},W{r},"")'
        wa[f"D{r}"] = f'=IF(X{r}="","",INDEX(Menu!$F:$F,X{r})&"")'
        wa[f"B{r}"].number_format = "hh:mm"
        wa[f"B{r}"].font = font(11, True, k["glowny"])
        wa[f"C{r}"].font = font(11, True, k["glowny"], tytul=True)
        wa[f"D{r}"].font = font(10)
        wa[f"D{r}"].alignment = ZAWIJ
        for col in "BC":
            wa[f"{col}{r}"].alignment = GORA
    wa.column_dimensions["W"].hidden = wa.column_dimensions["X"].hidden = True
    wa["Y5"], wa["Z5"] = "_wierszy", '=IF($Z$2="",1,MAX(1,COUNTIFS(Menu!$A:$A,$Z$2,Menu!$I:$I,"TAK")))'
    obszar(wa, f"OFFSET('Agenda'!$B$4,0,0,{start - 4}+'Agenda'!$Z$5,3)", f"B4:D{start + WIERSZE_AGENDY}")

    # ---------- Plan obsługi ----------
    wp = wb.create_sheet("Plan obsługi")
    naglowek_wydruku(wp, "PLAN OBSŁUGI", poziomo=True)
    for col, s in zip("ABCDEFGHIJ", [2, 4, 8, 15, 34, 58, 9, 6, 11, 2]):
        wp.column_dimensions[col].width = s
    info = [
        ("Goście", f'=IF($Z$1="","",{z_przyjecia("H")}&" dorosłych + "&N({z_przyjecia("I")})&" dzieci = "&$Z$4)'),
        ("Menu", f'=IF($Z$1="","",$Z$2&" · "&TEXT(IF({z_przyjecia("L")}<>"",{z_przyjecia("L")},N({z_przyjecia("K")})),"0")&" zł/os.")'),
        ("Razem", f'=IF($Z$1="","",{z_przyjecia("S")})'),
        ("Zadatek", f'=IF($Z$1="","",N({z_przyjecia("O")}))'),
        ("Do zapłaty", f'=IF($Z$1="","",{z_przyjecia("T")})'),
        ("Tort", f'=IF(N({z_przyjecia("N")})=0,"—",TEXT({z_przyjecia("N")},"hh:mm"))'),
        ("Telefon", f'=IF($Z$1="","",{z_przyjecia("F")}&"")'),
    ]
    for i, (n, f) in enumerate(info):
        wp[f"E{4 + i}"], wp[f"F{4 + i}"] = n, f
        wp[f"E{4 + i}"].font = font(10, True, k["glowny"])
        wp[f"F{4 + i}"].font = font(10, n in ("Razem", "Do zapłaty"))
        wp[f"F{4 + i}"].alignment = Alignment(horizontal="left")
        if n in ("Razem", "Zadatek", "Do zapłaty"):
            wp[f"F{4 + i}"].number_format = '#,##0.00 "zł"'
    wp["E14"] = "DIETY / ALERGIE / UWAGI"
    wp["E14"].font = font(10, True, "C00000")
    wp["F14"] = f'=IF($Z$1="","",IF({z_przyjecia("P")}="","—",{z_przyjecia("P")}))'
    wp["F14"].font = font(11, True, "C00000")
    wp["F14"].alignment = ZAWIJ
    wp["E15"] = "Porcje i godziny to założenia z zakładki Menu — ilość = porcja × wszyscy goście (dzieci jak dorośli)."
    wp["E15"].font = font(8, italic=True, kolor="7F7F7F")
    H2 = 17
    for col, n in zip("BCDEFGHI", ["", "Godz.", "Dział", "Zadanie", "Pozycja", "Ilość", "", "Porcja"]):
        c = wp[f"{col}{H2}"]
        c.value = n
        c.font = font(10, True, k["glowny"])
        c.fill = NAGL
        c.border = DOL
    for i in range(1, WIERSZE_PLANU + 1):
        r = H2 + i
        wp[f"X{r}"] = f'=IFERROR(MATCH($Z$2&"|"&{i},Menu!$K:$K,0),"")'
        wp[f"W{r}"] = f'=IF(X{r}="","",INDEX(Menu!$E:$E,X{r})&"|"&INDEX(Menu!$B:$B,X{r}))'
        nowy = f'AND(X{r}<>"",W{r}<>' + (f'W{r - 1}' if i > 1 else '"#"') + ')'
        wp[f"B{r}"] = f'=IF({nowy},"☐","")'
        wp[f"C{r}"] = f'=IF({nowy},MOD($Z$3+INDEX(Menu!$B:$B,X{r})/1440,1),"")'
        wp[f"D{r}"] = f'=IF({nowy},INDEX(Menu!$D:$D,X{r})&"","")'
        wp[f"E{r}"] = f'=IF({nowy},INDEX(Menu!$E:$E,X{r})&"","")'
        wp[f"F{r}"] = f'=IF(X{r}="","",INDEX(Menu!$F:$F,X{r})&"")'
        porcja, miara = f"INDEX(Menu!$G:$G,X{r})", f"INDEX(Menu!$H:$H,X{r})"
        duza = f'OR(AND({miara}="g",{porcja}*$Z$4>=1000),AND({miara}="ml",{porcja}*$Z$4>=1000))'
        wp[f"G{r}"] = f'=IF(X{r}="","",IF(N({porcja})=0,"",IF({duza},{porcja}*$Z$4/1000,{porcja}*$Z$4)))'
        wp[f"H{r}"] = (f'=IF(G{r}="","",IF({duza},IF({miara}="g","kg","l"),{miara}&""))')
        wp[f"I{r}"] = f'=IF(X{r}="","",IF(N({porcja})=0,"",{porcja}&" "&{miara}&"/os."))'
        wp[f"C{r}"].number_format = "hh:mm"
        wp[f"G{r}"].number_format = "#,##0.0#"
        for col in "BCDEFGHI":
            wp[f"{col}{r}"].font = font(10, col in ("C", "E", "G"), k["glowny"] if col in ("C",) else "000000")
            wp[f"{col}{r}"].alignment = ZAWIJ if col in ("E", "F") else GORA
        wp[f"B{r}"].font = font(13)
    wp.column_dimensions["W"].hidden = wp.column_dimensions["X"].hidden = True
    wp["Y5"], wp["Z5"] = "_wierszy", '=IF($Z$2="",1,MAX(1,COUNTIF(Menu!$A:$A,$Z$2)))'
    obszar(wp, f"OFFSET('Plan obsługi'!$B$4,0,0,{H2 - 3}+'Plan obsługi'!$Z$5,8)", f"B4:I{H2 + WIERSZE_PLANU}")
    wp.oddFooter.center.text = "☐ = odhacz po wykonaniu"
    wp.oddFooter.center.size = 8
    wp.print_title_rows = f"{H2}:{H2}"

    wyjscie = KATALOG / "dla-klienta" / lokal_id / f"Kalendarz przyjęć – {lokal['nazwa']}.xlsx"
    wyjscie.parent.mkdir(parents=True, exist_ok=True)
    wb.save(wyjscie)
    print(wyjscie)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo")
