# Wdrożenie Kalendarza (Docker)

Instrukcja dla własnego serwera. Potrzebujesz: Docker Engine 24+ z Compose v2, 1 GB RAM, domeny (opcjonalnie,
do pracy bez internetu wystarczy adres IP) i miejsca na kopie zapasowe. Wszystko poniżej robisz w katalogu po `git clone`.

## 1. Przygotowanie

```sh
cp .env.example .env
python3 -c "import secrets;print(secrets.token_urlsafe(50))"   # wklej jako DJANGO_SECRET_KEY
```

W `.env` ustaw co najmniej `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` i `DJANGO_CSRF_TRUSTED_ORIGINS` (z https).
Wybierz tryb pracy:

| Tryb | Ustawienie | Efekt |
|---|---|---|
| jeden lokal (restauracja, hotel) | `KALENDARZ_LOKAL=demo` (albo nazwa Twojego pliku z `lokale/`) | lokal i menu startowe zakładają się przy pierwszym starcie |
| wspólna instancja (wielu klientów) | `KALENDARZ_LOKAL=` (puste), `KALENDARZ_PUBLICZNY=1`, `DEMO_MAX=200` | strona publiczna z demo; lokale zakłada logowanie przez Konto |

Pojedynczy lokal zmieniasz potem w panelu (Ustawienia): nazwa, adres, kontakt, sala, kolory, logo.

Bez HTTPS (pierwsze uruchomienie na laptopie): ustaw `DJANGO_SSL_REDIRECT=0` i `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`.
Z `DJANGO_SSL_REDIRECT=1` bez proxy aplikacja przekieruje na https, którego jeszcze nie ma.
Menu startowe to tylko skrót — wszystko da się edytować i usunąć w panelu.

## 2. Start

```sh
docker compose up -d --build
curl -fsS http://127.0.0.1:8095/zdrowie/    # "ok" = aplikacja odpowiada
```

Kontener sam zrobi migracje i wczyta dane startowe. Baza i logo leżą na wolumenie `kalendarz_data` (`/data`),
więc aktualizacja obrazu ich nie rusza.

Pierwsze konto (administrator serwisowy):

```sh
docker compose exec app python manage.py createsuperuser   # panel: /serwis/
```

W trybie wspólnej instancji użytkownicy wchodzą przyciskiem „Zaloguj kontem sudomie” — patrz sekcja 3.

## 3. Logowanie przez Konto sudomie (opcjonalne)

Potrzebujesz działającego Konta (albo innego dostawcy OIDC). W Koncie zarejestruj aplikację:

```sh
# na serwerze Konta:
docker compose exec app python manage.py klient_oidc kalendarz https://twoja-domena/oidc/callback/ > klient.env
```

Przenieś `OIDC_CLIENT_ID` i `OIDC_CLIENT_SECRET` z tego pliku do `.env` Kalendarza razem z
`OIDC_ISSUER=https://twoja-domena-konta/o`, potem `docker compose up -d`. Puste `OIDC_ISSUER` = przycisku nie ma
i zostaje logowanie lokalne (awaryjne — przydaje się zawsze).

Instalacja jednej firmy: `KALENDARZ_FIRMA=<uuid firmy>` wpuszcza tylko członków tej firmy. Wspólna instancja: puste.

## 4. HTTPS

**Wariant A: reverse proxy** (nginx, Caddy, Traefik). Kontener słucha na `127.0.0.1:8095` (`HTTP_PORT`), proxy
przekazuje `Host`, `X-Forwarded-Proto: https` i `X-Forwarded-For`. Przykład Caddy:

```
kalendarz.example.com {
    reverse_proxy 127.0.0.1:8095
}
```

**Wariant B: Cloudflare Tunnel** (bez otwartego portu). Włóż konfigurację tunelu do `deploy/cloudflared/`
(`config.yml` + poświadczenia) i włącz profil:

```sh
docker compose --profile tunnel up -d
```

W obu wariantach `DJANGO_ALLOWED_HOSTS` i `DJANGO_CSRF_TRUSTED_ORIGINS` muszą wskazywać domenę z https.
Wyloguj się i zaloguj ponownie po zmianie domeny (ciasteczka sesji są przypisane do hosta).

## 5. Kopie zapasowe

```sh
deploy/backup.sh                                  # kopia bazy do deploy/backups/
crontab -e                                        # 20 3 * * * /sciezka/deploy/backup.sh
```

Kopia to jeden plik SQLite — do odtworzenia wystarczy podmienić `/data/db.sqlite3` w wolumenie
(`docker compose cp` albo `docker run --rm -v kalendarz_kalendarz_data:/data ...`). Logo leżą w `/data/media` —
obejmij je kopią katalogu, jeśli wgrywasz własne.

## 6. Aktualizacja

```sh
git pull && docker compose up -d --build
```

Migracje wykonują się przy starcie kontenera. Przed dużą aktualizacją zrób kopię (sekcja 5).

## 7. Typowe problemy

| Objaw | Przyczyna |
|---|---|
| pętla przekierowań (`ERR_TOO_MANY_REDIRECTS`) | proxy nie wysyła `X-Forwarded-Proto: https`; ustaw `DJANGO_SSL_REDIRECT=0` na czas diagnozy |
| `DisallowedHost` (400) | domena brak w `DJANGO_ALLOWED_HOSTS` |
| `CSRF verification failed` (403) | domena bez https w `DJANGO_CSRF_TRUSTED_ORIGINS` |
| kontener „unhealthy” | healthcheck pyta `localhost` — nie zmieniaj nazwy serwisu `app` ani portu 8000 w kontenerze |
| po aktualizacji stary wygląd | przeglądarka trzyma pliki; odśwież z pominięciem cache (statyki mają nazwy z hashem, więc dotyczy to rzadko) |
| pusty panel po pierwszym starcie | brak lokalu: w trybie wspólnej instancji zaloguj się przez Konto (lokal powstaje sam), w trybie jednego lokalu ustaw `KALENDARZ_LOKAL` i uruchom kontener ponownie |
