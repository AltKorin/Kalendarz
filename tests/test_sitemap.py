"""sitemap.xml: publiczne strony serwisu; strona główna tylko przy publicznym wejściu."""
from django.test import override_settings


def test_sitemap_zawiera_publiczne_strony(client):
    with override_settings(KALENDARZ_PUBLICZNY=True):
        r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert r["Content-Type"].startswith("application/xml")
    tresc = r.content.decode()
    assert "https://kalendarz.sudomie.pl/</loc>" in tresc
    assert "https://kalendarz.sudomie.pl/regulamin/</loc>" in tresc
    assert "demo" not in tresc


def test_sitemap_prywatna_instancja_nie_linkuje_strony_glownej(client):
    with override_settings(KALENDARZ_PUBLICZNY=False):
        tresc = client.get("/sitemap.xml").content.decode()
    assert "https://kalendarz.sudomie.pl/</loc>" not in tresc
    assert "https://kalendarz.sudomie.pl/regulamin/</loc>" in tresc


def test_robots_wskazuje_sitemape(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/plain")
    assert "Sitemap: https://kalendarz.sudomie.pl/sitemap.xml" in r.content.decode()
