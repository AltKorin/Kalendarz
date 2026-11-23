"""Powiązania kont z Kontem sudomie przechodzą do paczki core_sso (agency-platform-core 0.3.0).

Blue/green (CLAUDE.md): ten krok tylko KOPIUJE wiersze; stara tabela przyjecia_tozsamosczewnetrzna zostaje
nieużywana na jedno wydanie i znika w osobnej migracji (OpenProject). Idempotentne: istniejące (issuer, sub) pomija.
"""
from django.db import migrations


def kopiuj(apps, schema_editor):
    Stara = apps.get_model("przyjecia", "TozsamoscZewnetrzna")
    Nowa = apps.get_model("core_sso", "TozsamoscZewnetrzna")
    for t in Stara.objects.all():
        Nowa.objects.get_or_create(issuer=t.issuer.rstrip("/"), sub=t.sub, defaults={"user_id": t.user_id})


class Migration(migrations.Migration):
    dependencies = [
        ("przyjecia", "0002_tozsamosc_zewnetrzna"),
        ("core_sso", "0001_initial"),
    ]
    operations = [migrations.RunPython(kopiuj, migrations.RunPython.noop)]
