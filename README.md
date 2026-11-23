# Kalendarz przyjęć

[![CI](https://github.com/AltKorin/Kalendarz/actions/workflows/ci.yml/badge.svg)](https://github.com/AltKorin/Kalendarz/actions/workflows/ci.yml)

Kalendarz przyjęć i terminów grup dla restauracji i hoteli:

- **przyjęcia z menu** — wycena, ilości dla kuchni (porcja × goście), plan obsługi dla kuchni, sali i baru,
  agenda dla gości na jedną stronę A4 (Word),
- **terminy kilkudniowe** — grupy, pakiety hotelowe, święta; opis liczby osób („ok. 90?”, „cały hotel (planujemy)”),
  wykrywanie nakładających się terminów i wolnych okien,
- **wydruki czarno-białe A4** — lista terminów do rozdania, kalendarz pon–nd, pełne zestawienie z tabelą,
- **wiele lokali na jednej instalacji** — każdy lokal widzi tylko swoje dane; logowanie kontem sudomie (OIDC),
- **demo bez rejestracji** — własna kopia na 24 h na fikcyjnych danych.

Hostowana wersja: <https://kalendarz.sudomie.pl>.

## Stos

Django 6.1, Inertia.js (`inertia-django`) + React 19 + Tailwind + shadcn/ui budowane Vite, SQLite (do przeniesienia),
django-simple-history, PyMuPDF (wydruki), python-docx (Word). CLI `kalendarz.py` generuje te same dokumenty z pliku JSON.

## Uruchomienie lokalnie

```sh
cp .env.example .env        # opcjonalnie: bez niego działają wartości domyślne (dev)
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
.venv/bin/python manage.py migrate
.venv/bin/python manage.py wczytaj_menu       # lokal i menu startowe (tylko pusta baza)
VITE_DEV=0 .venv/bin/python manage.py runserver 127.0.0.1:8010
```

Konta lokalne zakłada się w `/serwis/` (`createsuperuser`). Logowanie przez Konto sudomie włącza się zmiennymi
`OIDC_*` (puste = przycisku nie ma). Wspólna instalacja: `KALENDARZ_PUBLICZNY=1`, `DEMO_MAX=200`.
Pełna lista zmiennych: `deploy/env.production.example`.

Testy: `.venv/bin/python -m pytest -q tests` (prawa modelu + Hypothesis).

## Wdrożenie

Docker: patrz [`WDROZENIE.md`](WDROZENIE.md) — zmienne (`cp .env.example .env`), reverse proxy/TLS,
kopie zapasowe, aktualizacja i typowe problemy.

## Licencja

MIT — plik `LICENSE`. Prawa: Komorowski & Windorpski sp. z o.o.
