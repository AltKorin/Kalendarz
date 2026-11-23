"""Instalacja jednofirmowa (lokale/<KALENDARZ_LOKAL>.json + KALENDARZ_FIRMA z .env) → jeden Lokal w bazie.
Wszystkie istniejące menu, przyjęcia i konta (bez superuserów) trafiają do niego. Pusta baza = nic nie robi."""
import json
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import migrations


def do_lokalu(apps, schema_editor):
    Lokal, Menu, Przyjecie, Czlonek = (apps.get_model("przyjecia", m) for m in ("Lokal", "Menu", "Przyjecie", "Czlonek"))
    User, Group = apps.get_model("auth", "User"), apps.get_model("auth", "Group")
    konta = User.objects.filter(is_superuser=False)
    if not (Menu.objects.exists() or Przyjecie.objects.exists() or konta.exists()):
        return
    plik = Path(settings.BASE_DIR) / "lokale" / f"{getattr(settings, 'KALENDARZ_LOKAL', '') or 'sami-swoi'}.json"
    dane = json.loads(plik.read_text(encoding="utf-8")) if plik.exists() else {"nazwa": "Mój lokal"}
    kolory = {k: v for k, v in dane.get("kolory", {}).items() if not k.startswith("_")}
    fonty = {k: v for k, v in dane.get("fonty", {}).items() if not k.startswith("_")}
    lokal = Lokal.objects.create(nazwa=dane["nazwa"], podpis=dane.get("podpis", ""), kontakt=dane.get("kontakt", ""),
                                 firma=getattr(settings, "KALENDARZ_FIRMA", "") or None, kolory=kolory or None,
                                 fonty=fonty, sala=dane.get("sale", {}).get("sala", "Sala"))
    if not lokal.kolory:
        lokal.kolory = {"glowny": "2F3E46", "akcent": "8C5A3C", "tlo_naglowka": "EEF0EB", "linia": "B9A27A"}
    logo = plik.parent / dane.get("logo", "-")
    if dane.get("logo") and logo.exists():
        lokal.logo.save(logo.name, ContentFile(logo.read_bytes()), save=False)
    lokal.save()
    Menu.objects.update(lokal=lokal)
    Przyjecie.objects.update(lokal=lokal)
    kierownicy = set(Group.objects.filter(name="Kierownik").values_list("user__id", flat=True))
    for u in konta:
        Czlonek.objects.create(user=u, lokal=lokal, kierownik=u.pk in kierownicy)


class Migration(migrations.Migration):
    dependencies = [("przyjecia", "0004_lokale")]
    operations = [migrations.RunPython(do_lokalu, migrations.RunPython.noop)]
