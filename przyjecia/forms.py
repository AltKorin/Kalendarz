from django import forms

from .models import Przyjecie


class PrzyjecieForm(forms.ModelForm):
    """Przyjęcie z menu (restauracja: godzina, dorośli ≥ 1) albo termin bez menu (hotel: liczba osób albo opis)."""

    class Meta:
        model = Przyjecie
        fields = ["data", "koniec", "start", "klient", "telefon", "rodzaj", "doroslych", "dzieci", "osoby_opis", "sale",
                  "menu", "cena_os", "cena_dziecko", "tort", "zadatek", "uwagi", "status"]

    def __init__(self, *a, lokal, **kw):
        super().__init__(*a, **kw)
        self.lokal = lokal
        for pole in ("cena_os", "zadatek", "doroslych", "dzieci"):
            self.fields[pole].required = False
        menu = lokal.menu.all()
        self.fields["menu"].queryset = menu if self.instance.pk else menu.filter(aktywne=True)

    def clean_klient(self):
        klient = self.cleaned_data["klient"].strip()
        if not klient:
            raise forms.ValidationError("Podaj klienta albo nazwę imprezy.")
        return klient

    def clean(self):
        d = super().clean()
        menu = d.get("menu")
        for pole in ("doroslych", "dzieci", "zadatek"):
            if d.get(pole) is None:
                d[pole] = 0
        if menu:
            if d.get("cena_os") is None:
                d["cena_os"] = menu.cena_os
            if not self.instance.pk and d.get("cena_dziecko") is None:
                d["cena_dziecko"] = menu.cena_dziecko
            if not d.get("start"):
                self.add_error("start", "Przyjęcie z menu potrzebuje godziny (z niej liczy się plan obsługi).")
            if d["doroslych"] < 1:
                self.add_error("doroslych", "Przyjęcie z menu: co najmniej 1 dorosły.")
        else:
            if d.get("cena_os") is None:
                d["cena_os"] = 0
            if d["doroslych"] + d["dzieci"] < 1 and not (d.get("osoby_opis") or "").strip():
                self.add_error("osoby_opis", "Podaj liczbę osób albo opis (np. „ok. 90?”, „cały hotel”).")
        if d.get("koniec") and d.get("data") and d["koniec"] < d["data"]:
            self.add_error("koniec", "Wyjazd nie może być przed przyjazdem.")
        if d.get("data") and d.get("klient"):
            podobne = self.lokal.przyjecia.filter(data=d["data"], start=d.get("start"), klient=d["klient"])
            if podobne.exclude(pk=self.instance.pk).exists():
                self.add_error("klient", "To przyjęcie już jest w kalendarzu (ta sama data, godzina i klient).")
        return d

    def save(self, commit=True):
        self.instance.lokal = self.lokal
        return super().save(commit)
