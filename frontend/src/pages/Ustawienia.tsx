import { useForm } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { Pole } from "@/components/Pole";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { Bledy } from "@/lib/typy";

type Dane = { nazwa: string; podpis: string; kontakt: string; sala: string; glowny: string; akcent: string;
  tlo_naglowka: string; linia: string; ma_logo: boolean };

const KOLORY: { pole: "glowny" | "akcent" | "tlo_naglowka" | "linia"; nazwa: string; opis: string }[] = [
  { pole: "glowny", nazwa: "Główny", opis: "Nagłówki, przyciski, menu" },
  { pole: "akcent", nazwa: "Akcent", opis: "Wyróżnienia na wydrukach Word" },
  { pole: "tlo_naglowka", nazwa: "Tło nagłówków", opis: "Jasne tło tabel i kafli" },
  { pole: "linia", nazwa: "Linie", opis: "Ramki i obramowania" },
];

export default function Ustawienia({ lokal_dane, bledy, demo, firma }: { lokal_dane: Dane; bledy: Bledy; demo: boolean; firma: boolean }) {
  const form = useForm<Omit<Dane, "ma_logo"> & { logo: File | null; usun_logo: string }>({
    nazwa: lokal_dane.nazwa ?? "", podpis: lokal_dane.podpis ?? "", kontakt: lokal_dane.kontakt ?? "",
    sala: lokal_dane.sala ?? "", glowny: lokal_dane.glowny, akcent: lokal_dane.akcent,
    tlo_naglowka: lokal_dane.tlo_naglowka, linia: lokal_dane.linia, logo: null, usun_logo: "",
  });
  const tekst = (pole: "nazwa" | "podpis" | "kontakt" | "sala") => ({
    value: form.data[pole], onChange: (e: { target: { value: string } }) => form.setData(pole, e.target.value),
  });
  return (
    <Layout tytul="Ustawienia lokalu">
      <form className="grid gap-5 lg:grid-cols-2"
        onSubmit={(e) => { e.preventDefault(); form.post("/ustawienia/", { forceFormData: true, preserveScroll: true }); }}>
        <Card>
          <CardHeader><CardTitle>Na wydrukach i w panelu</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <Pole etykieta="Nazwa lokalu" blad={bledy.nazwa}><Input {...tekst("nazwa")} /></Pole>
            <Pole etykieta="Adres" blad={bledy.podpis}><Input placeholder="ul. Lipowa 1, Miasto" {...tekst("podpis")} /></Pole>
            <Pole etykieta="Kontakt w stopce" blad={bledy.kontakt}><Input placeholder="tel. · e-mail · strona" {...tekst("kontakt")} /></Pole>
            <Pole etykieta="Nazwa sali na agendzie" blad={bledy.sala}><Input placeholder="Sala" {...tekst("sala")} /></Pole>
            {firma && <p className="text-xs text-muted-foreground">Pracowników zapraszasz i zmieniasz im role w Koncie sudomie.</p>}
          </CardContent>
        </Card>
        <div className="space-y-5">
          <Card>
            <CardHeader><CardTitle>Kolory</CardTitle></CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              {KOLORY.map((k) => (
                <Pole key={k.pole} etykieta={k.nazwa} blad={bledy[k.pole]} podpowiedz={k.opis}>
                  <div className="flex items-center gap-2">
                    <input type="color" aria-label={k.nazwa} className="h-9 w-12 cursor-pointer rounded border"
                      value={form.data[k.pole]} onChange={(e) => form.setData(k.pole, e.target.value)} />
                    <Input value={form.data[k.pole]} onChange={(e) => form.setData(k.pole, e.target.value)} className="font-mono" />
                  </div>
                </Pole>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Logo</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {demo ? <p className="text-sm text-muted-foreground">W demo nie wgrywa się plików.</p> : (
                <Pole etykieta="Plik PNG, JPG albo WEBP (do 2 MB)" blad={bledy.logo}>
                  <Input type="file" accept="image/png,image/jpeg,image/webp"
                    onChange={(e) => form.setData("logo", e.target.files?.[0] ?? null)} />
                </Pole>
              )}
              {lokal_dane.ma_logo && (
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" className="size-4" checked={form.data.usun_logo === "1"}
                    onChange={(e) => form.setData("usun_logo", e.target.checked ? "1" : "")} />
                  Usuń obecne logo
                </label>
              )}
            </CardContent>
          </Card>
          {Object.keys(bledy).length > 0 && (
            <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">Popraw zaznaczone pola.</p>
          )}
          <Button type="submit" disabled={form.processing}>Zapisz ustawienia</Button>
        </div>
      </form>
    </Layout>
  );
}
