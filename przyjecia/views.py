import calendar
import json
from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from inertia import render

import kalendarz as k
from django.conf import settings
from django.db.models import Q

from . import demo, regulamin, stoliki as st, umowa as um, uslugi
from .forms import PrzyjecieForm, RezerwacjaForm
from .models import DZIALY, KSZTALTY, MIARY, RODZAJE, STATUSY, STATUSY_REZERWACJI, UMOWY


MIESIACE = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień",
            "Październik", "Listopad", "Grudzień"]


def panel(widok):
    """Zalogowany i przypisany do lokalu. Konto bez lokalu (np. serwisowe) nie ma czego oglądać."""
    @wraps(widok)
    def opakowany(request, *a, **kw):
        if not request.lokal:
            logout(request)
            messages.error(request, "To konto nie jest przypisane do żadnego lokalu. Poproś właściciela o dostęp "
                                    "w Koncie sudomie.")
            return redirect("logowanie")
        if not regulamin.zaakceptowany(request.lokal):
            return redirect("regulamin_akceptuj")
        return widok(request, *a, **kw)
    return login_required(opakowany)


def _json(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _bledy_formularza(form):
    return {pole: " ".join(str(e) for e in lista) for pole, lista in form.errors.items()}


def _wiersz(p):
    w = uslugi.wycena(p)
    return {"id": p.pk, "data": p.data.isoformat(), "dzien": k.nazwa_dnia(p.data.isoformat()),
            "koniec": p.koniec.isoformat() if p.koniec else None,
            "start": p.start.strftime("%H:%M") if p.start else None, "klient": p.klient,
            "rodzaj": p.get_rodzaj_display(), "goscie": p.goscie, "osoby_opis": p.osoby_opis, "sale": p.sale,
            "menu": p.menu.nazwa if p.menu else None, "razem": str(w["razem"]),
            "zadatek": str(p.zadatek), "do_zaplaty": str(w["do_zaplaty"]), "status": p.status,
            "status_nazwa": p.get_status_display(), "uwagi": p.uwagi,
            "umowa": p.umowa, "umowa_nazwa": p.get_umowa_display()}


def _miesiac(request):
    try:
        rok, mies = map(int, request.GET.get("m", "").split("-"))
        date(rok, mies, 1)
    except ValueError:
        dzis = date.today()
        rok, mies = dzis.year, dzis.month
    return rok, mies


def _info_miesiaca(rok, mies):
    pop = date(rok, mies, 1) - timedelta(days=1)
    nast = date(rok, mies, calendar.monthrange(rok, mies)[1]) + timedelta(days=1)
    return {"klucz": f"{rok}-{mies:02d}", "nazwa": f"{MIESIACE[mies - 1]} {rok}",
            "poprzedni": f"{pop.year}-{pop.month:02d}", "nastepny": f"{nast.year}-{nast.month:02d}",
            "pierwszy_dzien_tygodnia": date(rok, mies, 1).weekday(), "dni": calendar.monthrange(rok, mies)[1]}


# ---------- logowanie ----------

def logowanie(request):
    if request.user.is_authenticated:
        return redirect("pulpit")
    bledy = {}
    if request.method == "POST":
        d = _json(request)
        user = authenticate(request, username=d.get("login", "").strip(), password=d.get("haslo", ""))
        if user:
            login(request, user)
            return redirect(request.GET.get("next") or "pulpit")
        bledy["haslo"] = "Zły login albo hasło."
    return render(request, "Logowanie", {"bledy": bledy,
                                         "sso": {"nazwa": settings.OIDC_NAZWA} if settings.OIDC_ISSUER else None})


@require_POST
def wyloguj(request):
    logout(request)
    return redirect("logowanie")


@login_required
def logo(request):
    if not request.lokal or not request.lokal.logo:
        raise Http404
    return FileResponse(request.lokal.logo.open("rb"))


# ---------- pulpit ----------

def start(request):
    """`/`: pulpit zalogowanego; niezalogowany — strona publiczna (wspólna instancja) albo logowanie."""
    if request.user.is_authenticated:
        return pulpit(request)
    if not settings.KALENDARZ_PUBLICZNY:
        return redirect("logowanie")
    return render(request, "Start", {
        "demo": [{"id": k_, **v} for k_, v in demo.warianty().items()] if settings.DEMO_MAX > 0 else [],
        "demo_godzin": settings.DEMO_HOURS, "sso": bool(settings.OIDC_ISSUER), "ga": settings.GA_MEASUREMENT_ID})


def regulamin_strona(request):
    """Publiczny regulamin (GA po zgodzie, jak strona startowa)."""
    return render(request, "Regulamin", {"html": regulamin.tresc(), "wersja": regulamin.WERSJA,
                                         "ga": settings.GA_MEASUREMENT_ID, "akceptacja": None})


@login_required
def regulamin_akceptuj(request):
    """Jednorazowo dla lokalu: kierownik akceptuje regulamin (umowa firmy). Obsługa czeka na kierownika."""
    l = request.lokal
    if not l:
        return redirect("pulpit")  # panel() wyloguje z komunikatem
    if regulamin.zaakceptowany(l):
        return redirect("pulpit")
    kierownik = uslugi.jest_kierownikiem(request.user, l)
    if request.method == "POST" and kierownik and _json(request).get("akceptuje") is True:
        regulamin.zaakceptuj(l, request.user, demo._ip(request))
        messages.success(request, "Dziękujemy — regulamin zaakceptowany. Kalendarz jest gotowy.")
        return redirect("pulpit")
    return render(request, "Regulamin", {"html": regulamin.tresc(), "wersja": regulamin.WERSJA, "ga": "",
                                         "akceptacja": {"kierownik": kierownik, "lokal": l.nazwa}})


@require_POST
def demo_start(request, wariant):
    if request.user.is_authenticated:
        logout(request)
    try:
        lokal = demo.start(request, wariant)
    except demo.DemoNiedostepne as e:
        if not e.args[0]:
            raise Http404
        messages.error(request, e.args[0])
        return redirect("pulpit")
    messages.success(request, f"To jest demo „{lokal.nazwa}” — zmieniaj śmiało, dane znikną po "
                              f"{settings.DEMO_HOURS} godz.")
    return redirect("pulpit")


@panel
def pulpit(request):
    rok, mies = _miesiac(request)
    dzis = date.today()
    w_miesiacu = list(uslugi.w_miesiacu(request.lokal.przyjecia, rok, mies).select_related("menu"))
    aktywne = [p for p in w_miesiacu if p.status != "odwolana"]
    najblizsze = request.lokal.przyjecia.filter(data__lte=dzis + timedelta(days=7)) \
        .filter(Q(koniec__gte=dzis) | Q(koniec__isnull=True, data__gte=dzis)) \
        .exclude(status="odwolana").select_related("menu")
    return render(request, "Pulpit", {
        "dzis": dzis.isoformat(),
        "miesiac": _info_miesiaca(rok, mies),
        "przyjecia": [_wiersz(p) for p in w_miesiacu],
        "najblizsze": [_wiersz(p) for p in najblizsze],
        "podsumowanie": {
            "przyjec": len(aktywne), "gosci": sum(p.goscie for p in aktywne),
            "wartosc": str(sum((uslugi.wycena(p)["razem"] for p in aktywne), start=k.Decimal(0))),
            "do_potwierdzenia": sum(1 for p in aktywne if p.status == "wstepna"),
        },
        "rezerwacje_dzis": _rezerwacje_dzis(request.lokal, dzis) if settings.REZERWACJE_STOLIKOW else None,
    })


def _rezerwacje_dzis(lokal, dzis):
    rs = lokal.rezerwacje.filter(data=dzis).exclude(status="odwolana")
    wynik = {"liczba": rs.count(), "osob": sum(rs.values_list("osoby", flat=True)), "sala": settings.RZUT_SALI}
    if settings.RZUT_SALI and lokal.stoliki.filter(x__isnull=False).exists():
        sala = _sala_dnia(lokal, dzis)  # karta „Sala dziś” na pulpicie (Konrad 27.11)
        wynik |= {"stoliki": sala["stoliki"], "rezerwacje": sala["rezerwacje"]}
    return wynik


# ---------- przyjęcia ----------

def _opcje_formularza(lokal, przyjecie=None):
    menu = lokal.menu.all() if przyjecie else lokal.menu.filter(aktywne=True)
    return {"rodzaje": [{"id": a, "nazwa": b} for a, b in RODZAJE],
            "statusy": [{"id": a, "nazwa": b} for a, b in STATUSY],
            "menu": [{"id": m.pk, "nazwa": m.nazwa, "cena_os": str(m.cena_os),
                      "cena_dziecko": "" if m.cena_dziecko is None else str(m.cena_dziecko)} for m in menu]}


def _formularz_przyjecia(request, przyjecie=None):
    if request.method == "POST":
        d = _json(request)
        form = PrzyjecieForm({kl: ("" if v is None else v) for kl, v in d.items()}, instance=przyjecie,
                             lokal=request.lokal)
        if form.is_valid():
            p = form.save()
            messages.success(request, f"Zapisano: {p.klient}, {p.data:%d.%m.%Y}.")
            return redirect("przyjecie", pk=p.pk)
        return render(request, "PrzyjecieFormularz", {"przyjecie": d, "bledy": _bledy_formularza(form),
                                                      "edycja": bool(przyjecie),
                                                      **_opcje_formularza(request.lokal, przyjecie)})
    if przyjecie:
        p = przyjecie
        start = {"id": p.pk, "data": p.data.isoformat(), "koniec": p.koniec.isoformat() if p.koniec else "",
                 "start": p.start.strftime("%H:%M") if p.start else "", "klient": p.klient,
                 "telefon": p.telefon, "rodzaj": p.rodzaj, "doroslych": p.doroslych, "dzieci": p.dzieci,
                 "osoby_opis": p.osoby_opis, "sale": p.sale, "menu": p.menu_id or "", "cena_os": str(p.cena_os),
                 "cena_dziecko": "" if p.cena_dziecko is None else str(p.cena_dziecko),
                 "tort": p.tort.strftime("%H:%M") if p.tort else "", "zadatek": str(p.zadatek), "uwagi": p.uwagi,
                 "status": p.status}
    else:
        start = {"data": request.GET.get("data", ""), "start": "14:00", "rodzaj": "inne", "doroslych": "",
                 "dzieci": 0, "status": "wstepna", "zadatek": "0"}
    return render(request, "PrzyjecieFormularz", {"przyjecie": start, "bledy": {}, "edycja": bool(przyjecie),
                                                  **_opcje_formularza(request.lokal, przyjecie)})


@panel
def przyjecia(request):
    rok, mies = _miesiac(request)
    qs = uslugi.w_miesiacu(request.lokal.przyjecia, rok, mies).select_related("menu")
    return render(request, "Przyjecia", {"miesiac": _info_miesiaca(rok, mies), "przyjecia": [_wiersz(p) for p in qs]})


@panel
def przyjecie_nowe(request):
    return _formularz_przyjecia(request)


@panel
def przyjecie_edycja(request, pk):
    return _formularz_przyjecia(request, get_object_or_404(request.lokal.przyjecia, pk=pk))


@panel
def przyjecie(request, pk):
    p = get_object_or_404(request.lokal.przyjecia.select_related("menu", "lokal"), pk=pk)
    dane = uslugi.dane_przyjecia(p) or {"do_potwierdzenia": [], "program": [], "obowiazki": []}
    w = uslugi.wycena(p)
    dzialy = dict(DZIALY)
    return render(request, "Przyjecie", {
        "przyjecie": _wiersz(p) | {"telefon": p.telefon, "doroslych": p.doroslych, "dzieci": p.dzieci,
                                   "tort": p.tort.strftime("%H:%M") if p.tort else None},
        "wycena": w["linie"] if p.menu_id else [],
        "plan": bool(dane["program"] or dane["obowiazki"]),
        "do_potwierdzenia": dane["do_potwierdzenia"],
        "program": [{"od": x["od"], "tytul": x["tytul"], "opis": x.get("opis", [])} for x in dane["program"]],
        "obowiazki": [{"od": o["od"], "dzial": o["dzial"], "dzial_nazwa": dzialy.get(o["dzial"], o["dzial"]),
                       "zadanie": o["zadanie"], "pozycje": o.get("pozycje", [])}
                      for o in sorted(dane["obowiazki"], key=lambda o: k._minuty(o["od"]))],
        "dzialy": [{"id": a, "nazwa": b} for a, b in DZIALY],
        "umowy": [{"id": a, "nazwa": b} for a, b in UMOWY],
    })


@panel
@require_POST
def przyjecie_umowa(request, pk):
    """Stan umowy jednym kliknięciem na stronie przyjęcia (zmiana trafia do historii jak każda inna)."""
    p = get_object_or_404(request.lokal.przyjecia, pk=pk)
    stan = _json(request).get("umowa")
    if stan not in dict(UMOWY):
        messages.error(request, "Nieznany stan umowy.")
    elif stan != p.umowa:
        p.umowa = stan
        p.save(update_fields=["umowa"])
        messages.success(request, f"{p.get_umowa_display()}: {p.klient}.")
    return redirect("przyjecie", pk=pk)


@panel
@require_POST
def przyjecie_usun(request, pk):
    p = get_object_or_404(request.lokal.przyjecia, pk=pk)
    opis = str(p)
    p.delete()
    messages.success(request, f"Usunięto przyjęcie: {opis}.")
    return redirect("przyjecia")


@panel
def przyjecie_dokument(request, pk, rodzaj):
    p = get_object_or_404(request.lokal.przyjecia.select_related("menu", "lokal"), pk=pk)
    if rodzaj not in ("agenda", "plan", "umowa"):
        raise Http404
    try:
        tresc, nazwa = um.umowa_docx(p) if rodzaj == "umowa" else uslugi.dokument(p, rodzaj)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect("przyjecie", pk=pk)
    odp = HttpResponse(tresc, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    odp["Content-Disposition"] = f'attachment; filename="{nazwa}"'
    return odp


# ---------- menu ----------

def _opcje_menu():
    return {"dzialy": [{"id": a, "nazwa": b} for a, b in DZIALY], "miary": [{"id": a, "nazwa": b} for a, b in MIARY]}


@panel
def menu_lista(request):
    return render(request, "MenuLista", {"menu": [
        {"id": m.pk, "nazwa": m.nazwa, "cena_os": str(m.cena_os), "aktywne": m.aktywne,
         "etapow": m.etapy.count(), "przyjec": m.przyjecia.count()} for m in request.lokal.menu.all()]})


def _formularz_menu(request, menu=None):
    if request.method == "POST":
        d = _json(request)
        zapisane, bledy = uslugi.zapisz_menu(d, request.lokal, menu)
        if not bledy:
            messages.success(request, f"Zapisano menu „{zapisane.nazwa}”.")
            return redirect("menu_lista")
        return render(request, "MenuFormularz", {"menu": d, "bledy": bledy, **_opcje_menu()})
    dane = uslugi.menu_do_edycji(menu) if menu else {
        "nazwa": "", "cena_os": "", "cena_dziecko": "", "aktywne": True,
        "etapy": [{"po_min": "0", "tytul": "Powitanie gości", "dzial": "sala", "zadanie": "Powitanie gości, rozsadzenie",
                   "pozycje": []}]}
    return render(request, "MenuFormularz", {"menu": dane, "bledy": {}, **_opcje_menu()})


@panel
def menu_nowe(request):
    return _formularz_menu(request)


@panel
def menu_edycja(request, pk):
    return _formularz_menu(request, get_object_or_404(request.lokal.menu, pk=pk))


@panel
@require_POST
def menu_usun(request, pk):
    menu = get_object_or_404(request.lokal.menu, pk=pk)
    try:
        blad = uslugi.usun_menu(menu)
    except ProtectedError:
        blad = "Menu jest używane w przyjęciach — nie można go usunąć."
    if blad:
        messages.error(request, blad)
    else:
        messages.success(request, "Usunięto menu.")
    return redirect("menu_lista")


# ---------- import z Excela ----------

@panel
def import_excel(request):
    if request.method == "POST":
        plik = request.FILES.get("plik")
        if not plik:
            return render(request, "Import", {"blad": "Wybierz plik Excela.", "wiersze": None})
        try:
            if request.POST.get("zatwierdz") == "1":
                dodane = uslugi.importuj_excel(plik, request.lokal)
                messages.success(request, f"Zaimportowano {dodane} przyjęć.")
                return redirect("przyjecia")
            wiersze = uslugi.czytaj_excel(plik, request.lokal)
        except ValueError as e:
            return render(request, "Import", {"blad": str(e), "wiersze": None})
        return render(request, "Import", {"blad": None, "wiersze": [
            {"nr": w["nr"], "opis": w["opis"], "stan": w["stan"], "bledy": w["bledy"]} for w in wiersze]})
    return render(request, "Import", {"blad": None, "wiersze": None})


# ---------- zespół ----------

def _tylko_kierownik(widok):
    @wraps(widok)
    def opakowany(request, *a, **kw):
        if not uslugi.jest_kierownikiem(request.user, request.lokal):
            messages.error(request, "To może zmienić kierownik.")
            return redirect("pulpit")
        if request.lokal.demo_do and request.method == "POST" and widok.__name__.startswith("konto"):
            messages.error(request, "W demo nie zakłada się kont — załóż własną firmę w Koncie sudomie.")
            return redirect("zespol")
        return widok(request, *a, **kw)
    return panel(opakowany)


def _konto(u, lokal):
    return {"id": u.pk, "login": u.username, "imie": u.first_name, "aktywne": u.is_active,
            "kierownik": uslugi.jest_kierownikiem(u, lokal),
            "ostatnio": u.last_login.strftime("%d.%m.%Y %H:%M") if u.last_login else None}


@_tylko_kierownik
def zespol(request):
    return render(request, "Zespol", {"konta": [_konto(u, request.lokal) for u in uslugi.konta_lokalu(request.lokal)],
                                      "ja": request.user.pk})


def _formularz_konta(request, konto=None):
    if request.method == "POST":
        d = _json(request)
        if konto and konto.pk == request.user.pk:
            d["aktywne"], d["kierownik"] = True, True  # nie da się odciąć samego siebie
        zapisane, bledy = uslugi.zapisz_konto(d, request.lokal, konto)
        if not bledy:
            messages.success(request, f"Zapisano konto „{zapisane.username}”.")
            return redirect("zespol")
        return render(request, "KontoFormularz", {"konto": {**d, "haslo": ""}, "bledy": bledy, "edycja": bool(konto)})
    dane = (_konto(konto, request.lokal) | {"haslo": ""}) if konto else {"login": "", "imie": "", "haslo": "", "aktywne": True, "kierownik": False}
    return render(request, "KontoFormularz", {"konto": dane, "bledy": {}, "edycja": bool(konto)})


@_tylko_kierownik
def konto_nowe(request):
    return _formularz_konta(request)


@_tylko_kierownik
def konto_edycja(request, pk):
    return _formularz_konta(request, get_object_or_404(uslugi.konta_lokalu(request.lokal), pk=pk))


@_tylko_kierownik
@require_POST
def konto_usun(request, pk):
    konto = get_object_or_404(uslugi.konta_lokalu(request.lokal), pk=pk)
    if konto.pk == request.user.pk:
        messages.error(request, "Nie można usunąć własnego konta.")
    elif konto.is_superuser:
        messages.error(request, "To konto serwisowe — usuwa je obsługa techniczna.")
    else:
        # ponytail: wyłączamy zamiast kasować — historia zmian i logowań wskazuje na to konto
        konto.is_active = False
        konto.save(update_fields=["is_active"])
        messages.success(request, f"Konto „{konto.username}” wyłączone — nie zaloguje się, historia zostaje.")
    return redirect("zespol")


# ---------- terminy grup i imprez ----------

@panel
def terminy(request):
    dzis = date.today()
    od, do = uslugi.okres(request.GET.get("od"), request.GET.get("do"), dzis)
    ps = uslugi.terminy_w_okresie(request.lokal, od, do)
    return render(request, "Terminy", {
        "od": od.isoformat(), "do": do.isoformat(), "dzis": dzis.isoformat(), "max_tygodni": uslugi.MAX_TYGODNI,
        "terminy": [_wiersz(p) for p in ps], **uslugi.przeglad_terminow(request.lokal, od, do, dzis)})


@panel
def terminy_pdf(request, widok):
    od, do = uslugi.okres(request.GET.get("od"), request.GET.get("do"), date.today())
    try:
        tresc, nazwa = uslugi.wydruk_terminow(request.lokal, widok, od, do, date.today())
    except ValueError:
        raise Http404
    odp = HttpResponse(tresc, content_type="application/pdf")
    odp["Content-Disposition"] = f'inline; filename="{nazwa}"'
    return odp


# ---------- rezerwacje stolików à la carte (#820) ----------

def _rezerwacje(widok):
    """Panel + feature flag REZERWACJE_STOLIKOW (wyłączona = adresów nie ma)."""
    @wraps(widok)
    def opakowany(request, *a, **kw):
        if not settings.REZERWACJE_STOLIKOW:
            raise Http404
        return widok(request, *a, **kw)
    return panel(opakowany)


def _dzien(tekst):
    try:
        return date.fromisoformat(tekst or "")
    except ValueError:
        return date.today()


def _rezerwacja(r):
    return {"id": r.pk, "data": r.data.isoformat(), "od": f"{r.od:%H:%M}", "do": f"{r.do:%H:%M}", "klient": r.klient,
            "telefon": r.telefon, "osoby": r.osoby, "stoliki": [s.numer for s in r.stoliki.all()],
            "stoliki_id": [s.pk for s in r.stoliki.all()], "uwagi": r.uwagi,
            "status": r.status, "status_nazwa": r.get_status_display()}


@_rezerwacje
def rezerwacje(request):
    return _dzien_rezerwacji(request, sala=False)


@_rezerwacje
def sala(request):
    """Rzut sali z zajętością stolików o wybranej godzinie — osobna pozycja menu (#821, zgłoszenie Konrada 27.11)."""
    if not settings.RZUT_SALI:
        raise Http404
    return _dzien_rezerwacji(request, sala=True)


def _sala_dnia(lokal, d):
    """Rezerwacje dnia i stoliki z ich zajętością — wspólne dla Rezerwacji, Sali i pulpitu."""
    rs = list(lokal.rezerwacje.filter(data=d).prefetch_related("stoliki"))
    aktywne = [r for r in rs if r.status != "odwolana"]
    return {"rezerwacje": [_rezerwacja(r) for r in rs], "osob": sum(r.osoby for r in aktywne),
            "stoliki": [_stolik(s) | {"zajety": [st.czas_tekst(r) for r in aktywne if s in r.stoliki.all()]}
                        for s in lokal.stoliki.all()]}


def _dzien_rezerwacji(request, sala):
    d = _dzien(request.GET.get("d"))
    return render(request, "Rezerwacje", {
        "dzien": d.isoformat(), "nazwa_dnia": k.nazwa_dnia(d.isoformat()), "dzis": date.today().isoformat(),
        "poprzedni": (d - timedelta(days=1)).isoformat(), "nastepny": (d + timedelta(days=1)).isoformat(),
        **_sala_dnia(request.lokal, d), "sala": sala,
    })


def _stolik(s):
    return {"id": s.pk, "numer": s.numer, "miejsc": s.miejsc, "ksztalt": s.ksztalt, "x": s.x, "y": s.y}


def _formularz_rezerwacji(request, rezerwacja=None):
    opcje = {"stoliki": [{"id": s.pk, "numer": s.numer, "miejsc": s.miejsc} for s in request.lokal.stoliki.all()],
             "statusy": [{"id": a, "nazwa": b} for a, b in STATUSY_REZERWACJI],
             "czas": request.lokal.czas_rezerwacji, "edycja": bool(rezerwacja)}
    if request.method == "POST":
        d = _json(request)
        form = RezerwacjaForm({kl: ("" if v is None else v) for kl, v in d.items()}, instance=rezerwacja,
                              lokal=request.lokal)
        if form.is_valid():
            r = form.save()
            messages.success(request, f"Zapisano rezerwację: {r.klient}, {r.data:%d.%m} {st.czas_tekst(r)}.")
            return redirect(f"{reverse('rezerwacje')}?d={r.data.isoformat()}")
        return render(request, "RezerwacjaFormularz", {"rezerwacja": d, "bledy": _bledy_formularza(form), **opcje})
    if rezerwacja:
        dane = _rezerwacja(rezerwacja) | {"stoliki": [s.pk for s in rezerwacja.stoliki.all()]}
    else:
        # z rzutu sali: ?od=19:30&stolik=<id> — kliknięty wolny stolik o wybranej godzinie
        od = request.GET.get("od", "")
        stolik = request.GET.get("stolik", "")
        dane = {"data": _dzien(request.GET.get("d")).isoformat(),
                "od": od if len(od) == 5 and _godzina(od) else "18:00", "do": "", "osoby": 2,
                "stoliki": [int(stolik)] if stolik.isdigit() and request.lokal.stoliki.filter(pk=stolik).exists() else [],
                "status": "potwierdzona"}
    return render(request, "RezerwacjaFormularz", {"rezerwacja": dane, "bledy": {}, **opcje})


def _godzina(tekst):
    try:
        return time.fromisoformat(tekst)
    except ValueError:
        return None


@_rezerwacje
def rezerwacja_nowa(request):
    return _formularz_rezerwacji(request)


@_rezerwacje
def rezerwacja_edycja(request, pk):
    return _formularz_rezerwacji(request, get_object_or_404(request.lokal.rezerwacje, pk=pk))


@_rezerwacje
@require_POST
def rezerwacja_usun(request, pk):
    r = get_object_or_404(request.lokal.rezerwacje, pk=pk)
    dzien, opis = r.data, str(r)
    r.delete()
    messages.success(request, f"Usunięto rezerwację: {opis}.")
    return redirect(f"{reverse('rezerwacje')}?d={dzien.isoformat()}")


@_rezerwacje
def stoliki(request):
    """Lista stolików + dodaj/zmień (POST {id?, numer, miejsc}) + domyślny czas rezerwacji (POST {czas})."""
    l = request.lokal
    if request.method == "POST":
        d = _json(request)
        if "uklad" in d:
            if not settings.RZUT_SALI:
                raise Http404
            blad = st.zapisz_uklad(l, d["uklad"])
            ok = "Zapisano układ sali."
        elif "czas" in d:
            blad = st.zapisz_czas(l, d["czas"])
            ok = "Zapisano domyślny czas rezerwacji."
        else:
            stolik = get_object_or_404(l.stoliki, pk=d["id"]) if d.get("id") else None
            blad = st.zapisz_stolik(l, d, stolik)
            ok = f"Zapisano stolik {str(d.get('numer', '')).strip()}."
        if blad:
            messages.error(request, blad)
        else:
            messages.success(request, ok)
        return redirect("stoliki")
    dzis = date.today()
    return render(request, "Stoliki", {
        "czas": l.czas_rezerwacji, "rzut": settings.RZUT_SALI,
        "ksztalty": [{"id": a, "nazwa": b} for a, b in KSZTALTY],
        "stoliki": [_stolik(s) | {
            "przyszlych": s.rezerwacje.filter(data__gte=dzis).exclude(status="odwolana").count(),
            "wczesniejszych": s.rezerwacje.filter(data__lt=dzis).count()} for s in l.stoliki.all()]})


@_rezerwacje
@require_POST
def stolik_usun(request, pk):
    stolik = get_object_or_404(request.lokal.stoliki, pk=pk)
    numer = stolik.numer
    blad = st.usun_stolik(stolik, date.today())
    if blad:
        messages.error(request, blad)
    else:
        messages.success(request, f"Usunięto stolik {numer}.")
    return redirect("stoliki")


# ---------- ustawienia lokalu ----------

def _lokal_do_formularza(l):
    from .models import KOLORY_DOMYSLNE
    return {"nazwa": l.nazwa, "podpis": l.podpis, "kontakt": l.kontakt, "sala": l.sala,
            **{k_: "#" + v for k_, v in {**KOLORY_DOMYSLNE, **(l.kolory or {})}.items()}}


@_tylko_kierownik
def ustawienia(request):
    l = request.lokal
    if request.method == "POST":
        dane = request.POST
        bledy = uslugi.zapisz_lokal(l, dane, request.FILES.get("logo"), dane.get("usun_logo") == "1")
        if not bledy:
            messages.success(request, "Zapisano ustawienia lokalu.")
            return redirect("ustawienia")
        return render(request, "Ustawienia", {"lokal_dane": {**dane.dict(), "ma_logo": bool(l.logo)}, "bledy": bledy,
                                              "demo": bool(l.demo_do), "firma": bool(l.firma)})
    return render(request, "Ustawienia", {"lokal_dane": {**_lokal_do_formularza(l), "ma_logo": bool(l.logo)},
                                          "bledy": {}, "demo": bool(l.demo_do), "firma": bool(l.firma)})


def sitemap_xml(request):
    """sitemap.xml: publiczne strony serwisu. Strona główna tylko wtedy, gdy instancja ma publiczne wejście."""
    strony = ["https://kalendarz.sudomie.pl/regulamin/"]
    if settings.KALENDARZ_PUBLICZNY:
        strony.insert(0, "https://kalendarz.sudomie.pl/")
    return HttpResponse(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f'  <url><loc>{u}</loc></url>\n' for u in strony)
        + '</urlset>\n',
        content_type="application/xml; charset=utf-8")


def robots_txt(request):
    """robots.txt: Cloudflare dokleja swoje reguły botów, więc Sitemap musi być po stronie aplikacji."""
    return HttpResponse(
        "User-agent: *\nAllow: /\n\nSitemap: https://kalendarz.sudomie.pl/sitemap.xml\n",
        content_type="text/plain; charset=utf-8")
