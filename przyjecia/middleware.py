from django.conf import settings
from django.contrib import messages
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.functional import SimpleLazyObject
from inertia import share

from .models import KOLORY_DOMYSLNE
from .uslugi import jest_kierownikiem, lokal_uzytkownika


class WspolneDaneMiddleware:
    """request.lokal (lokal zalogowanego) + dane dostępne na każdej stronie: lokal (nazwa, kolory), użytkownik,
    komunikaty, demo. Niezalogowany widzi barwy produktu."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        get_token(request)  # ustawia ciasteczko XSRF-TOKEN, z którego axios (Inertia) bierze token
        request.lokal = SimpleLazyObject(lambda: lokal_uzytkownika(request.user)) if request.user.is_authenticated else None

        def lokal():
            l = request.lokal
            if not l:
                return {"nazwa": "Kalendarz przyjęć", "kolory": KOLORY_DOMYSLNE, "logo": None, "demo_do": None}
            return {"nazwa": l.nazwa, "kolory": {**KOLORY_DOMYSLNE, **(l.kolory or {})}, "fonty": l.fonty or {},
                    "logo": reverse("logo") + f"?v={l.logo.name.rsplit('/', 1)[-1]}" if l.logo else None,
                    "demo_do": l.demo_do.isoformat() if l.demo_do else None}

        share(request,
              lokal=lokal,
              uzytkownik=lambda: ({"nazwa": request.user.get_full_name() or request.user.username,
                                   "kierownik": jest_kierownikiem(request.user, request.lokal)}
                                  if request.user.is_authenticated else None),
              komunikaty=lambda: [{"tekst": str(m), "poziom": m.level_tag} for m in messages.get_messages(request)],
              konto_url=lambda: settings.KONTO_URL,
              rezerwacje=lambda: settings.REZERWACJE_STOLIKOW,
              sala=lambda: settings.REZERWACJE_STOLIKOW and settings.RZUT_SALI)
        return self.get_response(request)
