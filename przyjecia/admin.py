from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Etap, Menu, Pozycja, Przyjecie, Rezerwacja, Stolik


class EtapInline(admin.TabularInline):
    model = Etap
    extra = 0


@admin.register(Menu)
class MenuAdmin(SimpleHistoryAdmin):
    list_display = ["nazwa", "cena_os", "aktywne"]
    inlines = [EtapInline]


@admin.register(Pozycja)
class PozycjaAdmin(SimpleHistoryAdmin):
    list_display = ["nazwa", "etap", "dla_gosci", "porcja", "miara"]
    list_filter = ["etap__menu"]


@admin.register(Przyjecie)
class PrzyjecieAdmin(SimpleHistoryAdmin):
    list_display = ["data", "start", "klient", "rodzaj", "doroslych", "dzieci", "menu", "status"]
    list_filter = ["status", "rodzaj", "menu"]
    date_hierarchy = "data"
    search_fields = ["klient", "telefon"]


from .models import AkceptacjaRegulaminu  # noqa: E402


@admin.register(AkceptacjaRegulaminu)
class AkceptacjaRegulaminuAdmin(admin.ModelAdmin):
    list_display = ["lokal", "user", "wersja", "czas", "ip"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Stolik)
class StolikAdmin(SimpleHistoryAdmin):
    list_display = ["numer", "miejsc", "lokal"]
    list_filter = ["lokal"]


@admin.register(Rezerwacja)
class RezerwacjaAdmin(SimpleHistoryAdmin):
    list_display = ["data", "od", "do", "klient", "osoby", "status", "lokal"]
    list_filter = ["status", "lokal"]
    date_hierarchy = "data"
    search_fields = ["klient", "telefon"]
