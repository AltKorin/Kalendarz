"""Rezerwacje à la carte: stolik, dzień, godziny od–do (zgłoszenie Sami Swoi, 26.11.2026, OpenProject #820).

Rezerwacja zajmuje swoje stoliki w przedziale [od, do) jednego dnia. Styk to nie kolizja: stolik zwalnia się o 20:00,
kolejni goście siadają o 20:00. Mała impreza w trakcie à la carte = dłuższy czas i kilka stolików naraz.

Prawa (tests/test_stoliki_laws.py):
- kolizja jest symetryczna,
- rezerwacje bez wspólnego stolika nigdy nie kolidują (także bez stolika w ogóle),
- wspólny stolik + nakładające się godziny = kolizja; styk (koniec = początek) = brak kolizji,
- domyślny koniec jest po początku i tego samego dnia (najpóźniej 23:59).
"""
from datetime import date, datetime, time, timedelta


def koliduje(a, b):
    """a, b = (od, do, stoliki)."""
    return bool(set(a[2]) & set(b[2])) and a[0] < b[1] and b[0] < a[1]


def kolizje(nowa, istniejace):
    """nowa = (od, do, stoliki); istniejace = [(klucz, od, do, stoliki)] → [(klucz, wspólne_stoliki)] wg godziny."""
    return [(k, set(nowa[2]) & set(s)) for k, od, do, s in sorted(istniejace, key=lambda x: x[1])
            if koliduje(nowa, (od, do, s))]


def domyslny_koniec(od: time, minuty: int) -> time:
    # ponytail: rezerwacja kończy się w dniu rozpoczęcia; lokal czynny po północy = osobne pole „do następnego dnia”
    koniec = datetime.combine(date(2000, 1, 1), od) + timedelta(minutes=minuty)
    return koniec.time() if koniec.date() == date(2000, 1, 1) else time(23, 59)


# ---------- baza (cienka warstwa nad modelami) ----------

def czas_tekst(r):
    return f"{r.od:%H:%M}–{r.do:%H:%M}"


def kolizje_rezerwacji(lokal, data, od, do, stoliki, pomin_pk=None):
    """Komunikaty o zajętych stolikach dla nowej/zmienianej rezerwacji (puste = wolne)."""
    if not stoliki:
        return []
    inne = (lokal.rezerwacje.filter(data=data, stoliki__in=stoliki).exclude(status="odwolana")
            .exclude(pk=pomin_pk).distinct().prefetch_related("stoliki"))
    po_pk = {r.pk: r for r in inne}
    wynik = kolizje((od, do, {s.pk for s in stoliki}),
                    [(r.pk, r.od, r.do, {s.pk for s in r.stoliki.all()}) for r in inne])
    numery = {s.pk: s.numer for s in stoliki}
    return [f"Stolik {', '.join(sorted(numery[s] for s in wspolne))} zajęty {czas_tekst(po_pk[pk])} "
            f"({po_pk[pk].klient})." for pk, wspolne in wynik]


def zapisz_stolik(lokal, dane, stolik=None):
    """Dodaj/zmień stolik. Zwraca błąd (None = zapisano)."""
    numer = str(dane.get("numer", "")).strip()[:20]
    try:
        miejsc = int(dane.get("miejsc") or 0)
    except (TypeError, ValueError):
        miejsc = 0
    if not numer:
        return "Podaj numer stolika."
    if not 1 <= miejsc <= 99:
        return "Liczba miejsc od 1 do 99."
    if lokal.stoliki.filter(numer=numer).exclude(pk=stolik.pk if stolik else None).exists():
        return f"Stolik „{numer}” już jest."
    s = stolik or lokal.stoliki.model(lokal=lokal)
    s.numer, s.miejsc = numer, miejsc
    s.save()
    return None


def usun_stolik(stolik, dzis):
    """Usuwa stolik, chyba że ma rezerwacje od dziś. Zwraca błąd (None = usunięto)."""
    przyszle = stolik.rezerwacje.filter(data__gte=dzis).exclude(status="odwolana").count()
    if przyszle:
        return (f"Stolik {stolik.numer} ma {przyszle} rezerwacji od dziś — najpierw przenieś je na inny stolik "
                f"albo odwołaj.")
    stolik.delete()
    return None


def zapisz_czas(lokal, minuty):
    try:
        minuty = int(minuty)
    except (TypeError, ValueError):
        return "Podaj czas w minutach."
    if not 15 <= minuty <= 12 * 60:
        return "Czas rezerwacji od 15 minut do 12 godzin."
    lokal.czas_rezerwacji = minuty
    lokal.save(update_fields=["czas_rezerwacji"])
    return None
