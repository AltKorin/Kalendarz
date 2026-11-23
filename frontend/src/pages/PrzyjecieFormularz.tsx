import { Link, useForm } from "@inertiajs/react";
import { useState } from "react";
import Layout from "@/components/Layout";
import { klasaSelect, Pole } from "@/components/Pole";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { type Bledy, type Opcja, zl } from "@/lib/typy";

type MenuOpcja = { id: number; nazwa: string; cena_os: string; cena_dziecko: string };
type Props = {
  przyjecie: Record<string, string | number>; bledy: Bledy; edycja: boolean;
  rodzaje: Opcja[]; statusy: Opcja[]; menu: MenuOpcja[];
};

export default function PrzyjecieFormularz({ przyjecie, bledy, edycja, rodzaje, statusy, menu }: Props) {
  const form = useForm({
    data: "", koniec: "", start: "", klient: "", telefon: "", rodzaj: "inne", doroslych: "", dzieci: "0",
    osoby_opis: "", sale: "", menu: "",
    cena_os: "", cena_dziecko: "", tort: "", zadatek: "0", uwagi: "", status: "wstepna",
    ...Object.fromEntries(Object.entries(przyjecie).map(([k, v]) => [k, v == null ? "" : String(v)])),
  });
  const d = form.data;
  const [kilkaDni, setKilkaDni] = useState(Boolean(przyjecie.koniec));
  const wybraneMenu = menu.find((m) => String(m.id) === d.menu);
  const cena = Number(d.cena_os || wybraneMenu?.cena_os || 0);
  const cenaDz = d.cena_dziecko !== "" ? Number(d.cena_dziecko) : wybraneMenu?.cena_dziecko ? Number(wybraneMenu.cena_dziecko) : null;
  const razem = cena * Number(d.doroslych || 0) + (cenaDz ?? 0) * Number(d.dzieci || 0);
  const pole = (nazwa: keyof typeof d) => ({
    value: d[nazwa], onChange: (e: { target: { value: string } }) => form.setData(nazwa, e.target.value),
  });
  const zapisz = (e: React.FormEvent) => {
    e.preventDefault();
    form.post(edycja ? `/przyjecia/${przyjecie.id}/edycja/` : "/przyjecia/nowe/", { preserveState: true, preserveScroll: true });
  };
  return (
    <Layout tytul={edycja ? `Zmień — ${przyjecie.klient}` : "Nowe przyjęcie lub termin"}>
      <form onSubmit={zapisz} className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardHeader><CardTitle>Kiedy i kto</CardTitle></CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <label className="flex items-center gap-2 text-sm sm:col-span-2">
                <input type="checkbox" className="size-4" checked={kilkaDni}
                  onChange={(e) => { setKilkaDni(e.target.checked); if (!e.target.checked) form.setData("koniec", ""); }} />
                Kilka dni (grupa, pobyt, pakiet hotelowy)
              </label>
              <Pole etykieta={kilkaDni ? "Przyjazd" : "Data"} blad={bledy.data}><Input type="date" {...pole("data")} /></Pole>
              {kilkaDni
                ? <Pole etykieta="Wyjazd" blad={bledy.koniec}><Input type="date" min={d.data} {...pole("koniec")} /></Pole>
                : <Pole etykieta="Godzina rozpoczęcia" blad={bledy.start}><Input type="time" {...pole("start")} /></Pole>}
              <Pole etykieta="Klient / nazwa imprezy" blad={bledy.klient} className="sm:col-span-2">
                <Input placeholder="np. Kowalscy, Gmina X – szkolenie, Sylwester" {...pole("klient")} />
              </Pole>
              <Pole etykieta="Telefon" blad={bledy.telefon}><Input type="tel" {...pole("telefon")} /></Pole>
              <Pole etykieta="Rodzaj przyjęcia" blad={bledy.rodzaj}>
                <select className={klasaSelect} {...pole("rodzaj")}>
                  {rodzaje.map((r) => <option key={r.id} value={r.id}>{r.nazwa}</option>)}
                </select>
              </Pole>
              <Pole etykieta="Dorośli" blad={bledy.doroslych}><Input type="number" min={0} {...pole("doroslych")} /></Pole>
              <Pole etykieta="Dzieci" blad={bledy.dzieci}><Input type="number" min={0} {...pole("dzieci")} /></Pole>
              <Pole etykieta="Osoby — opis" blad={bledy.osoby_opis}
                podpowiedz="Zamiast dokładnej liczby: „ok. 90?”, „cały hotel (planujemy)”. Trafia na wydruki.">
                <Input {...pole("osoby_opis")} />
              </Pole>
              <Pole etykieta="Sale" blad={bledy.sale}><Input placeholder="np. Restauracja, Sala Kominkowa" {...pole("sale")} /></Pole>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Menu i dodatki</CardTitle></CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <Pole etykieta="Menu" blad={bledy.menu} className="sm:col-span-2"
                podpowiedz="Z menu liczy się plan obsługi, ilości dla kuchni i wycena. Bez menu = sam termin w kalendarzu.">
                <select className={klasaSelect} {...pole("menu")}>
                  <option value="">— bez menu —</option>
                  {menu.map((m) => <option key={m.id} value={m.id}>{m.nazwa} — {zl(m.cena_os)}/os.</option>)}
                </select>
              </Pole>
              <Pole etykieta="Cena za osobę" blad={bledy.cena_os}
                podpowiedz={wybraneMenu ? `Puste = cena z menu (${zl(wybraneMenu.cena_os)})` : undefined}>
                <Input type="number" step="0.01" min={0} placeholder={wybraneMenu?.cena_os} {...pole("cena_os")} />
              </Pole>
              <Pole etykieta="Cena za dziecko" blad={bledy.cena_dziecko} podpowiedz="Puste = dzieci nie są wliczane do kwoty">
                <Input type="number" step="0.01" min={0} placeholder={wybraneMenu?.cena_dziecko} {...pole("cena_dziecko")} />
              </Pole>
              <Pole etykieta="Tort o godzinie" blad={bledy.tort} podpowiedz="Puste = bez tortu"><Input type="time" {...pole("tort")} /></Pole>
              <Pole etykieta="Diety, alergie, uwagi" blad={bledy.uwagi} className="sm:col-span-2">
                <Textarea rows={3} placeholder="np. Bez glutenu: 2 os., stolik przy oknie" {...pole("uwagi")} />
              </Pole>
            </CardContent>
          </Card>
        </div>
        <div className="space-y-5">
          <Card>
            <CardHeader><CardTitle>Rozliczenie</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Pole etykieta="Zadatek" blad={bledy.zadatek}><Input type="number" step="0.01" min={0} {...pole("zadatek")} /></Pole>
              <Pole etykieta="Status" blad={bledy.status}>
                <select className={klasaSelect} {...pole("status")}>
                  {statusy.map((s) => <option key={s.id} value={s.id}>{s.nazwa}</option>)}
                </select>
              </Pole>
              <div className="rounded-md bg-secondary p-3 text-sm">
                <div className="flex justify-between"><span>Razem</span><b>{zl(razem)}</b></div>
                <div className="flex justify-between"><span>Do zapłaty</span><b>{zl(Math.max(razem - Number(d.zadatek || 0), 0))}</b></div>
                {Number(d.dzieci) > 0 && cenaDz === null && <p className="mt-2 text-xs text-muted-foreground">Dzieci bez ceny — nie wliczone.</p>}
              </div>
            </CardContent>
          </Card>
          {Object.keys(bledy).length > 0 && (
            <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">Popraw zaznaczone pola.</p>
          )}
          <div className="flex gap-2">
            <Button type="submit" className="flex-1" disabled={form.processing}>Zapisz</Button>
            <Button variant="outline" asChild>
              <Link href={edycja ? `/przyjecia/${przyjecie.id}/` : "/przyjecia/"}>Anuluj</Link>
            </Button>
          </div>
        </div>
      </form>
    </Layout>
  );
}
