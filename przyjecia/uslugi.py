"""Serwisy panelu — UI jest cienką warstwą nad tymi funkcjami (ta sama logika dla panelu, admina i komend).

Prawa (testy: tests/test_panel.py):
- dane przyjęcia z panelu przechodzą kalendarz.sprawdz() bez błędów,
- wycena przyjęcia = kalendarz.wycena() (jedno źródło liczenia pieniędzy),
- import z Excela jest idempotentny: drugi import tego samego pliku nie tworzy nic nowego,
- menu użytego w przyjęciach nie da się usunąć (tylko zarchiwizować),
- dane jednego lokalu nigdy nie są widoczne ani zmieniane z innego (każdy serwis dostaje lokal jawnie).
"""
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Q

import kalendarz as k

from .models import DZIALY, Czlonek, Etap, Lokal, Menu, Pozycja, Przyjecie

KATALOG = Path(settings.BASE_DIR)


def lokal_uzytkownika(user):
    """Lokal, w którym pracuje zalogowany. ponytail: pierwszy z członkostw — przełącznik lokali, gdy ktoś
    realnie pracuje w dwóch firmach naraz."""
    if not user.is_authenticated:
        return None
    c = Czlonek.objects.select_related("lokal").filter(user=user).order_by("id").first()
    return c.lokal if c else None


def lokal_z_pliku(lokal_id, firma=""):
    """lokale/<id>.json (+ logo obok) → nowy Lokal. Pierwsza instalacja jednego lokalu."""
    from django.core.files.base import ContentFile

    plik = KATALOG / "lokale" / f"{lokal_id}.json"
    d = json.loads(plik.read_text(encoding="utf-8"))
    bez_uwag = lambda x: {k: v for k, v in (x or {}).items() if not k.startswith("_")}  # noqa: E731
    lokal = Lokal(nazwa=d["nazwa"], podpis=d.get("podpis", ""), kontakt=d.get("kontakt", ""), firma=firma or None,
                  fonty=bez_uwag(d.get("fonty")), sala=d.get("sale", {}).get("sala", "Sala"))
    if d.get("kolory"):
        lokal.kolory = bez_uwag(d["kolory"])
    if d.get("logo") and (plik.parent / d["logo"]).exists():
        lokal.logo.save(d["logo"], ContentFile((plik.parent / d["logo"]).read_bytes()), save=False)
    lokal.save()
    return lokal


POLA_KOLOROW = ("glowny", "akcent", "tlo_naglowka", "linia")
MAX_LOGO = 2 * 1024 * 1024


def zapisz_lokal(lokal, dane, logo=None, usun_logo=False):
    """Ustawienia lokalu z panelu (nazwa, adres, kontakt, sala, kolory, logo). Zwraca błędy (puste = zapisano)."""
    import re

    from django.core.exceptions import ValidationError
    from django.core.validators import validate_image_file_extension

    bledy = {}
    nazwa = str(dane.get("nazwa", "")).strip()
    if not nazwa:
        bledy["nazwa"] = "Podaj nazwę lokalu."
    kolory = {}
    for k_ in POLA_KOLOROW:
        v = str(dane.get(k_, "")).strip().lstrip("#").upper()
        if not re.fullmatch(r"[0-9A-F]{6}", v):
            bledy[k_] = "Kolor w zapisie #RRGGBB."
        kolory[k_] = v
    if logo is not None:
        if lokal.demo_do:
            bledy["logo"] = "W demo nie wgrywa się plików."
        elif logo.size > MAX_LOGO:
            bledy["logo"] = "Logo do 2 MB."
        else:
            try:
                validate_image_file_extension(logo)
                from PIL import Image
                Image.open(logo).verify()
                logo.seek(0)
            except (ValidationError, Exception):
                bledy["logo"] = "To nie jest obrazek (PNG, JPG, WEBP)."
    if bledy:
        return bledy
    lokal.nazwa, lokal.kolory = nazwa[:120], kolory
    lokal.podpis = str(dane.get("podpis", "")).strip()[:200]
    lokal.kontakt = str(dane.get("kontakt", "")).strip()[:200]
    lokal.sala = str(dane.get("sala", "")).strip()[:60] or "Sala"
    if usun_logo and lokal.logo:
        lokal.logo.delete(save=False)
    if logo is not None:
        if lokal.logo:
            lokal.logo.delete(save=False)
        lokal.logo.save(f"lokal-{lokal.pk}-{logo.name}"[-90:], logo, save=False)
    lokal.save()
    return {}


def w_miesiacu(qs, rok, mies):
    """Przyjęcia/terminy, które zahaczają o miesiąc (termin kilkudniowy z końca listopada widać też w grudniu)."""
    od = date(rok, mies, 1)
    do = date(rok + mies // 12, mies % 12 + 1, 1)
    return qs.filter(data__lt=do).filter(Q(koniec__gte=od) | Q(koniec__isnull=True, data__gte=od))


# ---------- menu ⇄ pakiet (format kalendarz.py) ----------

def menu_jako_pakiet(menu, cena_os=None, cena_dziecko=None):
    etapy = []
    for e in menu.etapy.prefetch_related("pozycje"):
        poz = list(e.pozycje.all())
        etapy.append({
            "po_min": e.po_min, "tytul": e.tytul or None, "dzial": e.dzial, "miejsce": "sala", "zadanie": e.zadanie,
            "dania": [{"danie": p.nazwa, "porcja": float(p.porcja) if p.porcja is not None else None,
                       "miara": p.miara} for p in poz if p.dla_gosci],
            "pozycje": [p.nazwa for p in poz if not p.dla_gosci],
        })
    return {"id": f"menu-{menu.pk}", "nazwa": menu.nazwa,
            "cena_os": float(cena_os if cena_os is not None else menu.cena_os),
            "cena_dziecko": None if cena_dziecko is None else float(cena_dziecko), "etapy": etapy}


def menu_do_edycji(menu):
    return {"id": menu.pk, "nazwa": menu.nazwa, "cena_os": str(menu.cena_os),
            "cena_dziecko": "" if menu.cena_dziecko is None else str(menu.cena_dziecko), "aktywne": menu.aktywne,
            "etapy": [{"po_min": e.po_min, "tytul": e.tytul, "dzial": e.dzial, "zadanie": e.zadanie,
                       "pozycje": [{"nazwa": p.nazwa, "dla_gosci": p.dla_gosci,
                                    "porcja": "" if p.porcja is None else str(p.porcja), "miara": p.miara}
                                   for p in e.pozycje.all()]}
                      for e in menu.etapy.prefetch_related("pozycje")]}


def _liczba(tekst, pole, bledy, wymagana=False, calkowita=False):
    tekst = str(tekst if tekst is not None else "").strip().replace(",", ".")
    if not tekst:
        if wymagana:
            bledy[pole] = "Wpisz liczbę."
        return None
    try:
        wartosc = int(tekst) if calkowita else Decimal(tekst)
    except (ValueError, InvalidOperation):
        bledy[pole] = "To nie jest liczba."
        return None
    if not calkowita and wartosc < 0:
        bledy[pole] = "Nie może być ujemna."
        return None
    return wartosc


def zapisz_menu(dane, lokal, menu=None):
    """Tworzy albo podmienia całe menu (z etapami i pozycjami). Zwraca (menu, błędy)."""
    bledy = {}
    nazwa = str(dane.get("nazwa", "")).strip()
    if not nazwa:
        bledy["nazwa"] = "Podaj nazwę menu."
    elif lokal.menu.filter(nazwa__iexact=nazwa).exclude(pk=getattr(menu, "pk", None)).exists():
        bledy["nazwa"] = "Menu o tej nazwie już jest."
    cena = _liczba(dane.get("cena_os"), "cena_os", bledy, wymagana=True)
    cena_dz = _liczba(dane.get("cena_dziecko"), "cena_dziecko", bledy)
    dzialy = {d for d, _ in DZIALY}
    etapy = dane.get("etapy") or []
    if not etapy:
        bledy["etapy"] = "Dodaj co najmniej jeden etap."
    for i, e in enumerate(etapy):
        po = _liczba(e.get("po_min"), f"etapy.{i}.po_min", bledy, wymagana=True, calkowita=True)
        if po is not None and not -24 * 60 < po < 24 * 60:
            bledy[f"etapy.{i}.po_min"] = "Od -1439 do 1439 minut."
        if e.get("dzial") not in dzialy:
            bledy[f"etapy.{i}.dzial"] = "Wybierz dział."
        if not str(e.get("zadanie", "")).strip():
            bledy[f"etapy.{i}.zadanie"] = "Opisz zadanie."
        for j, p in enumerate(e.get("pozycje") or []):
            if not str(p.get("nazwa", "")).strip():
                bledy[f"etapy.{i}.pozycje.{j}.nazwa"] = "Wpisz nazwę albo usuń wiersz."
            porcja = _liczba(p.get("porcja"), f"etapy.{i}.pozycje.{j}.porcja", bledy)
            if porcja is not None and p.get("miara") not in ("g", "ml", "szt."):
                bledy[f"etapy.{i}.pozycje.{j}.miara"] = "Miara?"
    if bledy:
        return menu, bledy

    with transaction.atomic():
        menu = menu or Menu(lokal=lokal)
        menu.nazwa, menu.cena_os, menu.cena_dziecko = nazwa, cena, cena_dz
        menu.aktywne = bool(dane.get("aktywne", True))
        menu.save()
        menu.etapy.all().delete()
        for e in etapy:
            etap = Etap.objects.create(menu=menu, po_min=int(str(e["po_min"]).strip()), tytul=str(e.get("tytul", "")).strip(),
                                       dzial=e["dzial"], zadanie=str(e["zadanie"]).strip())
            for j, p in enumerate(e.get("pozycje") or []):
                porcja = _liczba(p.get("porcja"), "x", {})
                Pozycja.objects.create(etap=etap, nazwa=str(p["nazwa"]).strip(), dla_gosci=bool(p.get("dla_gosci")),
                                       porcja=porcja, miara=p.get("miara") or "" if porcja is not None else "",
                                       kolejnosc=j)
    return menu, {}


def usun_menu(menu):
    """Zwraca komunikat błędu albo None. Użyte menu tylko archiwizujemy (historia przyjęć zostaje)."""
    ile = menu.przyjecia.count()
    if ile:
        return f"Menu „{menu.nazwa}” jest w {ile} przyjęciach — nie można go usunąć. Ukryj je („niedostępne”)."
    menu.delete()
    return None


def wczytaj_pakiet(pakiet, lokal, nazwa=None):
    """Seed: pakiet JSON (pakiety/<lokal>/*.json) → Menu lokalu. Idempotentne po nazwie."""
    nazwa = nazwa or pakiet["nazwa"].replace("Menu imprezowe nr ", "Menu ")
    if lokal.menu.filter(nazwa=nazwa).exists():
        return None
    etapy = []
    for e in sorted(pakiet["etapy"], key=lambda e: e["po_min"]):
        if not e.get("dzial"):
            continue
        poz = [{"nazwa": d["danie"], "dla_gosci": True, "porcja": d.get("porcja"), "miara": d.get("miara", "")}
               for d in e.get("dania", [])]
        poz += [{"nazwa": p.replace("na {goscie} os.", "dla wszystkich gości").replace(" — {goscie} os.", ""),
                 "dla_gosci": False} for p in e.get("pozycje", [])]
        etapy.append({"po_min": e["po_min"], "tytul": e.get("tytul", ""), "dzial": e["dzial"],
                      "zadanie": e["zadanie"], "pozycje": poz})
    menu, bledy = zapisz_menu({"nazwa": nazwa, "cena_os": pakiet["cena_os"],
                               "cena_dziecko": pakiet.get("cena_dziecko"), "etapy": etapy}, lokal)
    if bledy:
        raise ValueError(bledy)
    return menu


# ---------- przyjęcie ----------

def dane_przyjecia(p):
    """Przyjęcie z menu → pełne dane w formacie kalendarz.py (program, obowiązki, wycena, do potwierdzenia).
    Termin bez menu (np. grupa hotelowa) nie ma planu obsługi — None."""
    if not p.menu_id or not p.start or p.doroslych < 1:
        return None
    lokal = p.lokal.jako_dane()
    pakiet = menu_jako_pakiet(p.menu, p.cena_os, p.cena_dziecko)
    dane = k.rozpisz_przyjecie(
        lokal["id"], pakiet, p.data.isoformat(), p.start.strftime("%H:%M"), p.doroslych, p.klient,
        dzieci=p.dzieci, typ=p.get_rodzaj_display().lower(), tort=p.tort.strftime("%H:%M") if p.tort else None,
        zadatek=str(p.zadatek), uwagi=p.uwagi or None)
    dane["do_potwierdzenia"] = [d.replace(" i popraw w impreza.json", "").replace("z pakietu", "z menu")
                                .replace("z kalkulatora", "z menu") for d in dane["do_potwierdzenia"]]
    dane["lokal"] = lokal
    return dane


def wycena(p):
    return k.wycena({"cena_os": p.cena_os, "doroslych": p.doroslych, "dzieci": p.dzieci,
                     "cena_dziecko": p.cena_dziecko, "zadatek": p.zadatek})


def dokument(p, rodzaj):
    """rodzaj: 'agenda' | 'plan' → (bajty .docx, nazwa pliku)."""
    dane = dane_przyjecia(p)
    if dane is None:
        raise ValueError("Termin bez menu i godziny nie ma agendy ani planu obsługi.")
    buf = BytesIO()
    (k.agenda_docx if rodzaj == "agenda" else k.plan_obslugi_docx)(dane, buf)
    nazwa = f"{p.data:%Y-%m-%d} {k._slug(p.klient)} - {'agenda' if rodzaj == 'agenda' else 'plan obslugi'}.docx"
    return buf.getvalue(), nazwa


# ---------- import z Excela Marcina ----------

KOLUMNY_EXCELA = {"data": 2, "start": 4, "klient": 5, "telefon": 6, "rodzaj": 7, "doroslych": 8, "dzieci": 9,
                  "menu": 10, "cena_inna": 12, "cena_dziecko": 13, "tort": 14, "zadatek": 15, "uwagi": 16, "status": 17}
STATUS_Z_EXCELA = {"wstępna": "wstepna", "potwierdzona": "potwierdzona", "odbyła się": "odbyla", "odwołana": "odwolana"}


def _czas(v):
    if isinstance(v, datetime):
        return v.time()
    if isinstance(v, time):
        return v
    if isinstance(v, (int, float)) and 0 <= v < 1:  # ułamek doby z Excela
        m = round(v * 24 * 60)
        return time(m // 60, m % 60)
    if isinstance(v, str) and v.strip():
        return datetime.strptime(v.strip(), "%H:%M").time()
    return None


def czytaj_excel(plik, lokal):
    """Arkusz 'Przyjęcia' → lista wierszy {nr, dane|None, bledy[], stan: nowe|jest|blad}. Nic nie zapisuje."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(plik, data_only=True, read_only=True)
        ws = wb["Przyjęcia"]
    except Exception:
        raise ValueError("To nie jest plik „Kalendarz przyjęć” (brak zakładki Przyjęcia).")
    menu_po_nazwie = {m.nazwa.lower(): m for m in lokal.menu.all()}
    wiersze = []
    for nr, row in enumerate(ws.iter_rows(min_row=5, max_col=21, values_only=True), start=1):
        v = {pole: row[i - 1] for pole, i in KOLUMNY_EXCELA.items()}
        if not v["data"] and not v["klient"]:
            continue
        klient = str(v["klient"] or "").strip()
        if klient.upper().startswith("PRZYKŁAD"):
            continue
        bledy = []
        dzien = v["data"].date() if isinstance(v["data"], datetime) else v["data"] if isinstance(v["data"], date) else None
        if not dzien:
            bledy.append("brak daty")
        try:
            start, tort = _czas(v["start"]), _czas(v["tort"])
        except ValueError:
            start, tort = None, None
            bledy.append("zła godzina")
        if not start:
            bledy.append("brak godziny startu")
        if not klient:
            bledy.append("brak klienta")
        menu = menu_po_nazwie.get(str(v["menu"] or "").strip().lower())
        if not menu:
            bledy.append(f"nieznane menu „{v['menu'] or ''}”")
        try:
            doroslych, dzieci = int(v["doroslych"] or 0), int(v["dzieci"] or 0)
            if doroslych < 1 or dzieci < 0:
                bledy.append("liczba gości")
        except (TypeError, ValueError):
            doroslych, dzieci = 0, 0
            bledy.append("liczba gości")

        def kw(x):
            return None if x in (None, "") else Decimal(str(x))
        try:
            cena_inna, cena_dz, zadatek = kw(v["cena_inna"]), kw(v["cena_dziecko"]), kw(v["zadatek"]) or Decimal(0)
        except InvalidOperation:
            cena_inna = cena_dz = None
            zadatek = Decimal(0)
            bledy.append("kwota")
        rodzaj = str(v["rodzaj"] or "inne").strip().lower()
        dane = None
        if not bledy:
            dane = dict(data=dzien, start=start, klient=klient, telefon=str(v["telefon"] or "").strip(),
                        rodzaj=rodzaj if rodzaj in dict(Przyjecie._meta.get_field("rodzaj").choices) else "inne",
                        doroslych=doroslych, dzieci=dzieci, menu=menu,
                        cena_os=cena_inna if cena_inna is not None else menu.cena_os,
                        cena_dziecko=cena_dz if cena_dz is not None else menu.cena_dziecko, tort=tort,
                        zadatek=zadatek, uwagi=str(v["uwagi"] or "").strip(),
                        status=STATUS_Z_EXCELA.get(str(v["status"] or "").strip().lower(), "wstepna"))
        jest = bool(dane) and lokal.przyjecia.filter(data=dzien, start=start, klient=klient).exists()
        wiersze.append({"nr": nr, "dane": dane, "bledy": bledy, "stan": "blad" if bledy else "jest" if jest else "nowe",
                        "opis": f"{dzien or '?'} {start.strftime('%H:%M') if start else '?'} · {klient or '?'} · "
                                f"{doroslych}+{dzieci} os. · {v['menu'] or '?'}"})
    return wiersze


def importuj_excel(plik, lokal):
    """Zapisuje nowe przyjęcia z Excela; istniejące (data+start+klient) pomija. Zwraca liczbę dodanych."""
    dodane = 0
    with transaction.atomic():
        for w in czytaj_excel(plik, lokal):
            if w["stan"] == "nowe":
                _, utworzone = lokal.przyjecia.get_or_create(
                    data=w["dane"]["data"], start=w["dane"]["start"], klient=w["dane"]["klient"], defaults=w["dane"])
                dodane += utworzone
    return dodane


# ---------- zespół (konta w panelu klienta) ----------

def jest_kierownikiem(user, lokal):
    return bool(user.is_authenticated and lokal and Czlonek.objects.filter(user=user, lokal=lokal, kierownik=True).exists())


def konta_lokalu(lokal):
    from django.contrib.auth.models import User
    return User.objects.filter(czlonkostwa__lokal=lokal, is_superuser=False).order_by("-is_active", "username")


def zapisz_konto(dane, lokal, konto=None):
    """Dodaje albo zmienia konto pracownika. Zwraca (konto, błędy). Hasło puste przy zmianie = bez zmiany."""
    from django.contrib.auth.models import User
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    bledy = {}
    login = str(dane.get("login", "")).strip().lower()
    haslo = str(dane.get("haslo", ""))
    if not konto:
        if not login:
            bledy["login"] = "Podaj login."
        elif User.objects.filter(username__iexact=login).exists():
            bledy["login"] = "Taki login już jest."
        if not haslo:
            bledy["haslo"] = "Podaj hasło."
    if haslo:
        try:
            validate_password(haslo, konto)
        except ValidationError as e:
            bledy["haslo"] = " ".join(e.messages)
    if bledy:
        return konto, bledy
    with transaction.atomic():
        konto = konto or User(username=login)
        konto.first_name = str(dane.get("imie", "")).strip()[:150]
        konto.is_active = bool(dane.get("aktywne", True))
        if haslo:
            konto.set_password(haslo)
        konto.save()
        Czlonek.objects.update_or_create(user=konto, lokal=lokal, defaults={"kierownik": bool(dane.get("kierownik"))})
    return konto, {}


# ---------- logowanie przez Konto sudomie (paczka core_sso, kontrakt claimów: Konto/docs/PROJEKT.md) ----------

ROLA_KIEROWNIK = "kierownik"  # role Kalendarza w Koncie (Konto/produkty.json): kierownik | obsluga


def role_z_konta(user, firmy):
    """Hak core_sso (SSO_PO_ZALOGOWANIU), wołany przy KAŻDYM logowaniu: firma z Konta = lokal (powstaje przy pierwszym
    logowaniu kogokolwiek z firmy), rola kierownik/obsluga → Czlonek.kierownik. Członkostwa w lokalach z Konta,
    których nie ma już w claimach, znikają — odebranie dostępu w Koncie działa od razu."""
    ids = []
    for f in firmy:
        # nazwa z Konta tylko na start — potem lokal zmienia ją w Ustawieniach (nazwa na wydrukach ≠ nazwa firmy)
        lokal, _ = Lokal.objects.get_or_create(firma=f["id"], defaults={"nazwa": f["nazwa"] or "Mój lokal"})
        Czlonek.objects.update_or_create(user=user, lokal=lokal, defaults={"kierownik": f["rola"] == ROLA_KIEROWNIK})
        ids.append(lokal.pk)
    Czlonek.objects.filter(user=user, lokal__firma__isnull=False).exclude(lokal__in=ids).delete()


def konto_z_oidc(claims, issuer, firma_id):
    """Zgodność wsteczna dla testów: (konto, None) albo (None, komunikat). Logika i prawa — core_sso.uslugi."""
    from core_sso import uslugi as sso

    user, _, blad = sso.konto_z_oidc(claims, issuer, "kalendarz", firma_id)
    return user, blad


# ---------- API dla innych produktów (Grafik, #758) ----------

def przyjecia_w_zakresie(lokal, od, do):
    """Przyjęcia do grafiku zmian: bez odwołanych (nikt ich nie obsługuje) i bez danych klienta —
    grafik widzi cały zespół, a do planowania zmian wystarczy rodzaj, godzina i liczba gości (RODO: minimalizacja).
    Termin kilkudniowy zahaczający o zakres też wchodzi (`koniec`; puste = jeden dzień)."""
    qs = lokal.przyjecia.filter(data__lte=do).filter(Q(koniec__gte=od) | Q(koniec__isnull=True, data__gte=od))
    return [{"id": p.pk, "data": p.data.isoformat(), "koniec": p.ostatni_dzien.isoformat(),
             "start": f"{p.start:%H:%M}" if p.start else None, "rodzaj": p.get_rodzaj_display(),
             "goscie": p.goscie, "osoby_opis": p.osoby_opis, "status": p.status}
            for p in qs.exclude(status="odwolana")]


# ---------- terminy grup i imprez (wydruki, kolizje, wolne okna) ----------

MAX_TYGODNI = 26  # backpressure: najdłuższy okres jednego wydruku/widoku


def okres(od_txt, do_txt, dzis):
    """Okres widoku terminów z parametrów (puste/złe = od poniedziałku tego tygodnia, 8 tygodni). Przycięty do
    MAX_TYGODNI; do < od zamienia miejscami."""
    from . import terminy as t
    try:
        od = date.fromisoformat(od_txt)
    except (TypeError, ValueError):
        od = t.poniedzialek(dzis)
    try:
        do = date.fromisoformat(do_txt)
    except (TypeError, ValueError):
        do = od + timedelta(days=8 * 7 - 1)
    od, do = min(od, do), max(od, do)
    return od, min(do, od + timedelta(days=MAX_TYGODNI * 7 - 1))


def terminy_w_okresie(lokal, od, do):
    """Aktywne (bez odwołanych) przyjęcia i terminy zahaczające o [od, do]."""
    return list(lokal.przyjecia.filter(data__lte=do).filter(Q(koniec__gte=od) | Q(koniec__isnull=True, data__gte=od))
                .exclude(status="odwolana").select_related("menu"))


def przeglad_terminow(lokal, od, do, dzis):
    """Nakładające się terminy i wolne okna w okresie — to, co hotel sprawdza przed sprzedażą kolejnej grupy."""
    from . import terminy as t
    ps = terminy_w_okresie(lokal, od, do)
    po_id = {p.pk: p for p in ps}
    zakres = [(p.pk, p.data, p.ostatni_dzien) for p in ps]
    return {
        "nakladania": [{"a": po_id[a].klient, "b": po_id[b].klient, "a_id": a, "b_id": b, "od": o.isoformat(),
                        "do": d.isoformat()} for a, b, o, d in t.nakladania(zakres)],
        "wolne": [{"od": a.isoformat(), "do": b.isoformat()} for a, b in t.wolne_okna(zakres, max(od, dzis), do)]
                 if do >= dzis else [],
    }


def wydruk_terminow(lokal, widok, od, do, dzis):
    from . import druk
    return druk.pdf(widok, lokal.nazwa, dzis, [druk.termin_z_przyjecia(p) for p in terminy_w_okresie(lokal, od, do)],
                    od, do)
