from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

DZIALY = [("kuchnia", "Kuchnia"), ("sala", "Sala i kelnerzy"), ("bar", "Bar")]
MIARY = [("", "—"), ("g", "g"), ("ml", "ml"), ("szt.", "szt.")]
RODZAJE = [(r, r.capitalize()) for r in
           ["komunia", "chrzciny", "wesele", "urodziny", "jubileusz", "stypa", "spotkanie firmowe",
            "grupa", "pakiet hotelu", "święta", "inne"]]
STATUSY = [("wstepna", "Wstępna"), ("potwierdzona", "Potwierdzona"), ("rezerwowa", "Lista rezerwowa"),
           ("odbyla", "Odbyła się"), ("odwolana", "Odwołana")]
# Słownik Kolorów #030 (Mineral Gray + Pompeian Red), docs/PLAN-wersja-publiczna.md — dopóki lokal nie wybierze swoich
KOLORY_DOMYSLNE = {"glowny": "3A3F44", "akcent": "A3172B", "tlo_naglowka": "EEF0F1", "linia": "A3AAB0"}


def _kolory():
    return dict(KOLORY_DOMYSLNE)


class Lokal(models.Model):
    """Restauracja / hotel = firma z Konta sudomie. Wszystkie dane panelu należą do jednego lokalu."""
    nazwa = models.CharField("nazwa", max_length=120)
    podpis = models.CharField("adres", max_length=200, blank=True)
    kontakt = models.CharField("kontakt", max_length=200, blank=True, help_text="Telefon, e-mail, strona — stopka wydruków")
    firma = models.CharField("firma w Koncie sudomie", max_length=64, unique=True, null=True, blank=True)
    kolory = models.JSONField("kolory", default=_kolory)
    fonty = models.JSONField("fonty wydruków", default=dict, blank=True)
    logo = models.ImageField("logo", upload_to="logo/", blank=True)
    sala = models.CharField("nazwa sali na wydrukach", max_length=60, default="Sala")
    demo_do = models.DateTimeField("demo wygasa", null=True, blank=True)
    czas_rezerwacji = models.PositiveSmallIntegerField("domyślny czas rezerwacji stolika (min)", default=120)
    utworzono = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "lokale"

    def __str__(self):
        return self.nazwa

    def jako_dane(self):
        """Format lokalu dla kalendarz.py (dokumenty .docx)."""
        return {"id": f"lokal-{self.pk}", "nazwa": self.nazwa, "podpis": self.podpis, "kontakt": self.kontakt,
                "kolory": {**KOLORY_DOMYSLNE, **(self.kolory or {})}, "fonty": self.fonty or {},
                "logo": self.logo.path if self.logo else None,  # ścieżka bezwzględna: KATALOG/"lokale"/abs == abs
                "sale": {"sala": self.sala, "kuchnia": "Kuchnia", "bar": "Bar"},
                "dzialy": {"kuchnia": "Kuchnia", "sala": "Sala i kelnerzy", "bar": "Bar"}}


class Czlonek(models.Model):
    """Konto pracownika w lokalu. Rola z Konta sudomie (synchronizowana przy logowaniu) albo nadana w Zespole."""
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="czlonkostwa")
    lokal = models.ForeignKey(Lokal, on_delete=models.CASCADE, related_name="czlonkowie")
    kierownik = models.BooleanField("kierownik", default=False)
    history = HistoricalRecords()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "lokal"], name="czlonek_unikalny")]
ZERO = [MinValueValidator(Decimal("0"))]


class Menu(models.Model):
    lokal = models.ForeignKey(Lokal, on_delete=models.CASCADE, related_name="menu")
    nazwa = models.CharField("nazwa", max_length=80)
    cena_os = models.DecimalField("cena za osobę", max_digits=8, decimal_places=2, validators=ZERO)
    cena_dziecko = models.DecimalField("cena za dziecko", max_digits=8, decimal_places=2, null=True, blank=True,
                                       validators=ZERO, help_text="Puste = dzieci nie są wliczane do kwoty.")
    aktywne = models.BooleanField("dostępne przy nowych przyjęciach", default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-aktywne", "nazwa"]
        verbose_name_plural = "menu"
        constraints = [models.UniqueConstraint(fields=["lokal", "nazwa"], name="menu_unikalne_w_lokalu")]

    def __str__(self):
        return self.nazwa


class Etap(models.Model):
    """Krok przebiegu przyjęcia: kiedy (minuty od startu), kto, co robi, jakie pozycje."""
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="etapy")
    po_min = models.IntegerField("minuty od startu", help_text="-20 = 20 minut przed przyjściem gości")
    tytul = models.CharField("etap w agendzie gości", max_length=80, blank=True,
                             help_text="Puste = etap tylko dla obsługi")
    dzial = models.CharField("dział", max_length=20, choices=DZIALY)
    zadanie = models.CharField("zadanie dla obsługi", max_length=120)
    history = HistoricalRecords()

    class Meta:
        ordering = ["menu", "po_min", "id"]

    def __str__(self):
        return f"{self.menu} · {self.po_min:+d} min · {self.zadanie}"


class Pozycja(models.Model):
    """Danie (dla gości, z porcją) albo punkt do zrobienia (np. 'Obrusy, nakrycia')."""
    etap = models.ForeignKey(Etap, on_delete=models.CASCADE, related_name="pozycje")
    nazwa = models.CharField("nazwa", max_length=200)
    dla_gosci = models.BooleanField("danie widoczne w agendzie", default=True)
    porcja = models.DecimalField("porcja na osobę", max_digits=8, decimal_places=1, null=True, blank=True,
                                 validators=ZERO)
    miara = models.CharField("miara", max_length=5, choices=MIARY, blank=True)
    kolejnosc = models.PositiveSmallIntegerField(default=0)
    history = HistoricalRecords()

    class Meta:
        ordering = ["etap", "kolejnosc", "id"]

    def clean(self):
        if self.porcja is not None and not self.miara:
            raise ValidationError({"miara": "Podaj miarę porcji (g, ml, szt.)."})


class Przyjecie(models.Model):
    """Przyjęcie jednodniowe (restauracja: menu → plan obsługi) albo termin kilkudniowy (hotel: grupa, pakiet, święta)."""
    lokal = models.ForeignKey(Lokal, on_delete=models.CASCADE, related_name="przyjecia")
    data = models.DateField("data")
    koniec = models.DateField("do (wyjazd)", null=True, blank=True, help_text="Puste = jeden dzień")
    start = models.TimeField("godzina rozpoczęcia", null=True, blank=True)
    klient = models.CharField("klient", max_length=120)
    telefon = models.CharField("telefon", max_length=40, blank=True)
    rodzaj = models.CharField("rodzaj", max_length=30, choices=RODZAJE, default="inne")
    doroslych = models.PositiveIntegerField("dorośli", default=0)
    dzieci = models.PositiveIntegerField("dzieci", default=0)
    osoby_opis = models.CharField("osoby (opis)", max_length=80, blank=True,
                                  help_text="Zamiast liczby: „ok. 90?”, „cały hotel (planujemy)”")
    sale = models.CharField("sale", max_length=200, blank=True)
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT, related_name="przyjecia", verbose_name="menu",
                             null=True, blank=True)
    cena_os = models.DecimalField("cena za osobę", max_digits=8, decimal_places=2, validators=ZERO, default=0,
                                  help_text="Domyślnie z menu; zostaje taka, jak w dniu przyjęcia rezerwacji.")
    cena_dziecko = models.DecimalField("cena za dziecko", max_digits=8, decimal_places=2, null=True, blank=True,
                                       validators=ZERO)
    tort = models.TimeField("tort o godzinie", null=True, blank=True)
    zadatek = models.DecimalField("zadatek", max_digits=10, decimal_places=2, default=0, validators=ZERO)
    uwagi = models.TextField("diety, alergie, uwagi", blank=True)
    status = models.CharField("status", max_length=20, choices=STATUSY, default="wstepna")
    utworzono = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["data", "start"]
        verbose_name_plural = "przyjęcia"
        constraints = [
            models.UniqueConstraint(fields=["lokal", "data", "start", "klient"], name="przyjecie_unikalne_w_lokalu"),
            models.CheckConstraint(condition=models.Q(koniec__isnull=True) | models.Q(koniec__gte=models.F("data")),
                                   name="koniec_po_poczatku"),
        ]

    def __str__(self):
        return f"{self.data:%d.%m.%Y}{self.start and f' {self.start:%H:%M}' or ''} — {self.klient}"

    @property
    def ostatni_dzien(self):
        return self.koniec or self.data

    @property
    def goscie(self):
        return self.doroslych + self.dzieci


class Stolik(models.Model):
    """Stolik w restauracji (rezerwacje à la carte). Pozycja na rzucie sali — później (#821)."""
    lokal = models.ForeignKey(Lokal, on_delete=models.CASCADE, related_name="stoliki")
    numer = models.CharField("numer", max_length=20, help_text="np. 5, T2, Ogród 3")
    miejsc = models.PositiveSmallIntegerField("miejsc", default=4)
    history = HistoricalRecords()

    class Meta:
        ordering = ["numer"]
        verbose_name_plural = "stoliki"
        constraints = [models.UniqueConstraint(fields=["lokal", "numer"], name="stolik_unikalny_w_lokalu")]

    def __str__(self):
        return f"Stolik {self.numer}"


STATUSY_REZERWACJI = [("potwierdzona", "Potwierdzona"), ("odwolana", "Odwołana")]


class Rezerwacja(models.Model):
    """Rezerwacja à la carte: kto, kiedy (od–do), ile osób, które stoliki. Mała impreza = dłużej i kilka stolików."""
    lokal = models.ForeignKey(Lokal, on_delete=models.CASCADE, related_name="rezerwacje")
    data = models.DateField("data")
    od = models.TimeField("od godziny")
    do = models.TimeField("do godziny")
    klient = models.CharField("nazwisko", max_length=120)
    telefon = models.CharField("telefon", max_length=40, blank=True)
    osoby = models.PositiveSmallIntegerField("osób")
    stoliki = models.ManyToManyField(Stolik, related_name="rezerwacje", blank=True, verbose_name="stoliki")
    uwagi = models.TextField("uwagi", blank=True)
    status = models.CharField("status", max_length=20, choices=STATUSY_REZERWACJI, default="potwierdzona")
    utworzono = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords(m2m_fields=[stoliki])

    class Meta:
        ordering = ["data", "od"]
        verbose_name_plural = "rezerwacje stolików"
        constraints = [models.CheckConstraint(condition=models.Q(do__gt=models.F("od")), name="rezerwacja_do_po_od")]

    def __str__(self):
        return f"{self.data:%d.%m.%Y} {self.od:%H:%M} — {self.klient}"


class TozsamoscZewnetrzna(models.Model):
    """Konto u dostawcy logowania (OIDC: dziś Grafik, docelowo centralny login) przypięte do konta w Kalendarzu.
    Klucz = (issuer, sub) — login/e-mail u dostawcy może się zmienić, sub nie."""
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="tozsamosci")
    issuer = models.CharField(max_length=200)
    sub = models.CharField(max_length=200)
    utworzono = models.DateTimeField(auto_now_add=True)
    ostatnio = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["issuer", "sub"], name="tozsamosc_unikalna")]

    def __str__(self):
        return f"{self.user} ← {self.issuer} #{self.sub}"


class AkceptacjaRegulaminu(models.Model):
    """Dowód: kto, kiedy, z jakiego IP zaakceptował którą wersję regulaminu (i jaki dokładnie tekst — sha256).
    Niezmienialny jak LoginEvent: tylko dopisywanie."""
    lokal = models.ForeignKey(Lokal, on_delete=models.CASCADE, related_name="akceptacje")
    user = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="+")
    wersja = models.CharField(max_length=20)
    sha256 = models.CharField(max_length=64)
    ip = models.GenericIPAddressField(null=True, blank=True)
    czas = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "akceptacje regulaminu"

    def save(self, *a, **kw):
        if self.pk:
            raise PermissionError("Akceptacji regulaminu nie zmienia się.")
        super().save(*a, **kw)

    def delete(self, *a, **kw):
        raise PermissionError("Akceptacji regulaminu nie usuwa się (znika tylko razem z lokalem).")
