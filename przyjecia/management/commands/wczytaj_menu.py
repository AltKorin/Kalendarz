"""Instalacja jednego lokalu (KALENDARZ_LOKAL): lokal z lokale/<id>.json + menu z pakiety/<id>/*.json do pustej bazy
(skrót na start — potem lokal i menu edytuje się w panelu). Wspólna instancja (puste KALENDARZ_LOKAL): nic nie robi.

Tylko do pustej bazy (#773): komenda chodzi przy każdym starcie kontenera (CMD w Dockerfile), a menu usunięte albo
przemianowane przez klienta ma zostać usunięte/przemianowane. Prawa: tests/test_wczytaj_menu.py.
"""
import json

from django.conf import settings
from django.core.management.base import BaseCommand

from przyjecia.models import Lokal, Menu
from przyjecia.uslugi import KATALOG, lokal_z_pliku, wczytaj_pakiet


class Command(BaseCommand):
    help = "Wczytaj pakiety menu lokalu do pustej bazy (pierwsza instalacja)."

    def handle(self, *args, **opts):
        if not settings.KALENDARZ_LOKAL:
            self.stdout.write("Wspólna instancja (brak KALENDARZ_LOKAL) — lokale zakłada logowanie przez Konto.")
            return
        # ponytail: klient, który usunie WSZYSTKIE menu, dostanie startowe z powrotem; flaga „zasiano” w bazie, gdyby to przeszkadzało
        if Menu.objects.exists():
            self.stdout.write("Menu już są w bazie — pomijam (klient zarządza nimi w panelu).")
            return
        lokal = Lokal.objects.filter(demo_do__isnull=True).first() or lokal_z_pliku(settings.KALENDARZ_LOKAL,
                                                                                     settings.KALENDARZ_FIRMA)
        for plik in sorted((KATALOG / "pakiety" / settings.KALENDARZ_LOKAL).glob("*.json")):
            menu = wczytaj_pakiet(json.loads(plik.read_text(encoding="utf-8")), lokal)
            self.stdout.write(f"{plik.name}: " + (f"dodano „{menu.nazwa}”" if menu else "już jest"))
