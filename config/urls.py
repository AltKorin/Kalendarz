from django.contrib import admin
from django.urls import include, path

from przyjecia import api, views as v

from django.http import HttpResponse

urlpatterns = [
    path("zdrowie/", lambda r: HttpResponse("ok")),
    path("serwis/", admin.site.urls),
    path("api/przyjecia", api.przyjecia),  # serwer–serwer dla Grafiku (#758)
    path("sitemap.xml", v.sitemap_xml),
    path("robots.txt", v.robots_txt),
    path("logowanie/", v.logowanie, name="logowanie"),
    path("wyloguj/", v.wyloguj, name="wyloguj"),
    path("oidc/", include("core_sso.urls")),  # logowanie kontem sudomie; redirect_uri bez zmian: /oidc/callback/
    path("logo.png", v.logo, name="logo"),
    path("demo/<str:wariant>/", v.demo_start, name="demo_start"),
    path("regulamin/", v.regulamin_strona, name="regulamin"),
    path("regulamin/akceptuj/", v.regulamin_akceptuj, name="regulamin_akceptuj"),
    path("", v.start, name="pulpit"),
    path("przyjecia/", v.przyjecia, name="przyjecia"),
    path("przyjecia/nowe/", v.przyjecie_nowe, name="przyjecie_nowe"),
    path("przyjecia/<int:pk>/", v.przyjecie, name="przyjecie"),
    path("przyjecia/<int:pk>/edycja/", v.przyjecie_edycja, name="przyjecie_edycja"),
    path("przyjecia/<int:pk>/usun/", v.przyjecie_usun, name="przyjecie_usun"),
    path("przyjecia/<int:pk>/umowa/", v.przyjecie_umowa, name="przyjecie_umowa"),
    path("przyjecia/<int:pk>/<str:rodzaj>.docx", v.przyjecie_dokument, name="przyjecie_dokument"),
    path("terminy/", v.terminy, name="terminy"),
    path("terminy/<str:widok>.pdf", v.terminy_pdf, name="terminy_pdf"),
    path("rezerwacje/", v.rezerwacje, name="rezerwacje"),
    path("rezerwacje/nowa/", v.rezerwacja_nowa, name="rezerwacja_nowa"),
    path("rezerwacje/<int:pk>/", v.rezerwacja_edycja, name="rezerwacja_edycja"),
    path("rezerwacje/<int:pk>/usun/", v.rezerwacja_usun, name="rezerwacja_usun"),
    path("stoliki/", v.stoliki, name="stoliki"),
    path("stoliki/<int:pk>/usun/", v.stolik_usun, name="stolik_usun"),
    path("menu/", v.menu_lista, name="menu_lista"),
    path("menu/nowe/", v.menu_nowe, name="menu_nowe"),
    path("menu/<int:pk>/", v.menu_edycja, name="menu_edycja"),
    path("menu/<int:pk>/usun/", v.menu_usun, name="menu_usun"),
    path("import/", v.import_excel, name="import"),
    path("ustawienia/", v.ustawienia, name="ustawienia"),
    path("zespol/", v.zespol, name="zespol"),
    path("zespol/nowe/", v.konto_nowe, name="konto_nowe"),
    path("zespol/<int:pk>/", v.konto_edycja, name="konto_edycja"),
    path("zespol/<int:pk>/usun/", v.konto_usun, name="konto_usun"),
]
