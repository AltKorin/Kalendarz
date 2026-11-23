import { Link, router } from "@inertiajs/react";
import { useState } from "react";
import Layout from "@/components/Layout";
import { Pole } from "@/components/Pole";
import { Status } from "@/components/Status";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { kiedy, osoby, type Wiersz } from "@/lib/typy";

type Props = {
  od: string; do: string; dzis: string; max_tygodni: number; terminy: Wiersz[];
  nakladania: { a: string; b: string; a_id: number; b_id: number; od: string; do: string }[];
  wolne: { od: string; do: string }[];
};

const krotko = (iso: string) => `${Number(iso.slice(8, 10))}.${iso.slice(5, 7)}`;
const WYDRUKI = [
  { widok: "lista", nazwa: "Lista terminów", opis: "A4 pionowo — termin, impreza, osoby. Do rozdania pracownikom." },
  { widok: "kalendarz", nazwa: "Kalendarz pon–nd", opis: "A4 poziomo — tygodnie, weekendy przyciemnione, „dziś”." },
  { widok: "pelny", nazwa: "Pełny", opis: "Kalendarz + tabela z salami i uwagami, wolne terminy, linie na zmiany." },
];

export default function Terminy({ od, do: doDnia, max_tygodni, terminy, nakladania, wolne }: Props) {
  const [okres, setOkres] = useState({ od, do: doDnia });
  const q = `?od=${od}&do=${doDnia}`;
  return (
    <Layout tytul="Wydruki i wolne terminy">
      <form className="mb-5 flex flex-wrap items-end gap-3"
        onSubmit={(e) => { e.preventDefault(); router.get("/terminy/", okres, { preserveScroll: true }); }}>
        <Pole etykieta="Od"><Input type="date" value={okres.od} onChange={(e) => setOkres({ ...okres, od: e.target.value })} /></Pole>
        <Pole etykieta="Do"><Input type="date" value={okres.do} onChange={(e) => setOkres({ ...okres, do: e.target.value })} /></Pole>
        <Button type="submit" variant="outline">Pokaż</Button>
        <p className="text-xs text-muted-foreground">Najwyżej {max_tygodni} tygodni naraz.</p>
      </form>

      <div className="mb-5 grid gap-3 md:grid-cols-3">
        {WYDRUKI.map((w) => (
          <a key={w.widok} href={`/terminy/${w.widok}.pdf${q}`} target="_blank" rel="noopener"
            className="rounded-lg border bg-card p-4 hover:bg-secondary">
            <span className="block font-bold text-primary">{w.nazwa} (PDF) ↗</span>
            <span className="mt-1 block text-sm text-muted-foreground">{w.opis}</span>
          </a>
        ))}
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-2">
        <Card className={nakladania.length ? "gap-2 border-amber-300 bg-amber-50" : "gap-2"}>
          <CardHeader><CardTitle>Nakładające się terminy</CardTitle></CardHeader>
          <CardContent className="space-y-1 text-sm">
            {nakladania.length === 0 && <p className="text-muted-foreground">Brak — żadne dwa terminy nie dzielą dnia.</p>}
            {nakladania.map((n) => (
              <p key={`${n.a_id}-${n.b_id}`}>
                <b>{krotko(n.od)}{n.od !== n.do && `–${krotko(n.do)}`}</b>:{" "}
                <Link className="underline" href={`/przyjecia/${n.a_id}/`}>{n.a}</Link> +{" "}
                <Link className="underline" href={`/przyjecia/${n.b_id}/`}>{n.b}</Link>
                <span className="text-muted-foreground"> — sprawdź pokoje i obsadę</span>
              </p>
            ))}
          </CardContent>
        </Card>
        <Card className="gap-2">
          <CardHeader><CardTitle>Wolne terminy</CardTitle></CardHeader>
          <CardContent className="text-sm">
            {wolne.length === 0 ? <p className="text-muted-foreground">Brak wolnych dni w tym okresie.</p> : (
              <p className="leading-7">{wolne.map((w) => (
                <Link key={w.od} href={`/przyjecia/nowe/?data=${w.od}`} title="Dodaj termin"
                  className="mr-2 inline-block rounded border px-2 hover:bg-secondary">{krotko(w.od)}–{krotko(w.do)}</Link>
              ))}</p>
            )}
            <p className="mt-2 text-xs text-muted-foreground">Przyjazd – wyjazd. Kliknij, żeby dodać termin.</p>
          </CardContent>
        </Card>
      </div>

      <Card className="gap-2">
        <CardHeader><CardTitle>Terminy w okresie ({terminy.length})</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          {terminy.length === 0 && <p className="text-sm text-muted-foreground">Brak przyjęć i terminów w tym okresie.</p>}
          {terminy.map((p) => (
            <Link key={p.id} href={`/przyjecia/${p.id}/`}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border px-3 py-2 hover:bg-accent">
              <span className="w-48 font-semibold text-primary">{kiedy(p)}</span>
              <span className="font-medium">{p.klient}</span>
              <span className="text-sm text-muted-foreground">{osoby(p)}{p.sale && ` · ${p.sale}`}</span>
              <Status status={p.status} nazwa={p.status_nazwa} />
            </Link>
          ))}
        </CardContent>
      </Card>
    </Layout>
  );
}
