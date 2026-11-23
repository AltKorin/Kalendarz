import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("przyjecia", "0005_dane_do_lokalu")]
    operations = [
        migrations.AlterField("menu", "lokal", models.ForeignKey(
            on_delete=django.db.models.deletion.CASCADE, related_name="menu", to="przyjecia.lokal")),
        migrations.AlterField("przyjecie", "lokal", models.ForeignKey(
            on_delete=django.db.models.deletion.CASCADE, related_name="przyjecia", to="przyjecia.lokal")),
    ]
