import { Link } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { type Rezerwacja, RzutZajetosci, type StolikRzut } from "@/components/RzutSali";
import { Status, Umowa } from "@/components/Status";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { kiedy, type Miesiac, osoby, type Wiersz, zl } from "@/lib/typy";
import { cn } from "@/lib/utils";

type Props = {
  dzis: string; miesiac: Miesiac; przyjecia: Wiersz[]; najblizsze: Wiersz[];
  podsumowanie: { przyjec: number; gosci: number; wartosc: string; do_potwierdzenia: number };
  rezerwacje_dzis: { liczba: number; osob: number; sala: boolean; stoliki?: StolikRzut[]; rezerwacje?: Rezerwacja[] } | null;
};

const DNI = ["pon.", "wt.", "śr.", "czw.", "pt.", "sob.", "niedz."];

export function NawigacjaMiesiaca({ miesiac, sciezka }: { miesiac: Miesiac; sciezka: string }) {
  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" asChild><Link href={`${sciezka}?m=${miesiac.poprzedni}`}>←</Link></Button>
      <h2 className="min-w-44 text-center text-xl font-bold text-primary">{miesiac.nazwa}</h2>
      <Button variant="outline" size="sm" asChild><Link href={`${sciezka}?m=${miesiac.nastepny}`}>→</Link></Button>
    </div>
  );
}

function Kafel({ etykieta, wartosc, ostrzezenie }: { etykieta: string; wartosc: string | number; ostrzezenie?: boolean }) {
  return (
    <Card className={cn("gap-1 py-4", ostrzezenie && "border-amber-300 bg-amber-50")}>
      <CardContent className="px-4">
        <div className="text-sm text-muted-foreground">{etykieta}</div>
        <div className="text-2xl font-bold text-primary">{wartosc}</div>
      </CardContent>
    </Card>
  );
}

export default function Pulpit({ dzis, miesiac, przyjecia, najblizsze, podsumowanie, rezerwacje_dzis }: Props) {
  const poDniu = new Map<number, Wiersz[]>();
  przyjecia.forEach((p) => {
    // termin kilkudniowy widać w każdym swoim dniu tego miesiąca
    for (let d = 1; d <= miesiac.dni; d++) {
      const iso = `${miesiac.klucz}-${String(d).padStart(2, "0")}`;
      if (iso >= p.data && iso <= (p.koniec ?? p.data)) poDniu.set(d, [...(poDniu.get(d) ?? []), p]);
    }
  });
  const kratki = [...Array(miesiac.pierwszy_dzien_tygodnia).fill(null), ...Array.from({ length: miesiac.dni }, (_, i) => i + 1)];
  return (
    <Layout>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <NawigacjaMiesiaca miesiac={miesiac} sciezka="/" />
        <Button asChild><Link href="/przyjecia/nowe/">+ Dodaj przyjęcie</Link></Button>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kafel etykieta="Przyjęć i terminów" wartosc={podsumowanie.przyjec} />
        <Kafel etykieta="Gości" wartosc={podsumowanie.gosci} />
        <Kafel etykieta="Wartość" wartosc={zl(podsumowanie.wartosc)} />
        <Kafel etykieta="Czeka na potwierdzenie" wartosc={podsumowanie.do_potwierdzenia} ostrzezenie={podsumowanie.do_potwierdzenia > 0} />
      </div>

      {rezerwacje_dzis?.stoliki && rezerwacje_dzis.rezerwacje ? (
        <Card className="mb-6 gap-0 py-0">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pt-5">
            <CardTitle>Sala dziś <span className="text-sm font-normal text-muted-foreground">· {rezerwacje_dzis.liczba} rezerwacji, {rezerwacje_dzis.osob} os.</span></CardTitle>
            <Link href="/sala/" className="text-sm font-medium text-primary hover:underline">Otwórz salę →</Link>
          </CardHeader>
          <CardContent className="mx-auto w-full max-w-4xl px-0">
            <RzutZajetosci dzien={dzis} dzis={dzis} stoliki={rezerwacje_dzis.stoliki} rezerwacje={rezerwacje_dzis.rezerwacje} />
          </CardContent>
        </Card>
      ) : rezerwacje_dzis && (
        <Link href={rezerwacje_dzis.sala ? "/sala/" : "/rezerwacje/"} className="mb-6 flex items-center justify-between rounded-md border bg-card px-4 py-3 text-sm hover:bg-accent">
          <span>Stoliki dziś: <b>{rezerwacje_dzis.liczba}</b> rezerwacji, <b>{rezerwacje_dzis.osob}</b> os.</span>
          <span className="font-medium text-primary">{rezerwacje_dzis.sala ? "Sala →" : "Rezerwacje →"}</span>
        </Link>
      )}
      <Card className="mb-6">
        <CardHeader><CardTitle>Najbliższe 7 dni</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {najblizsze.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Brak przyjęć w najbliższym tygodniu. <Link className="underline" href="/przyjecia/nowe/">Dodaj przyjęcie</Link>
              {" "}albo <Link className="underline" href="/menu/">ustaw menu</Link>.
            </p>
          )}
          {najblizsze.map((p) => (
            <Link key={p.id} href={`/przyjecia/${p.id}/`}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border px-3 py-2 hover:bg-accent">
              <span className="w-44 font-semibold text-primary">{kiedy(p)}</span>
              <span className="font-medium">{p.klient}</span>
              <span className="text-sm text-muted-foreground">{[p.rodzaj, osoby(p), p.menu].filter(Boolean).join(" · ")}</span>
              <Status status={p.status} nazwa={p.status_nazwa} />
              {p.status !== "odwolana" && <Umowa umowa={p.umowa} nazwa={p.umowa_nazwa} />}
              {p.uwagi && <span className="text-sm font-medium text-destructive">⚠ {p.uwagi}</span>}
            </Link>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Kalendarz — {miesiac.nazwa}</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-muted-foreground">
            {DNI.map((d) => <div key={d} className="py-1">{d}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {kratki.map((dzien, i) => {
              if (dzien === null) return <div key={`p${i}`} />;
              const data = `${miesiac.klucz}-${String(dzien).padStart(2, "0")}`;
              const lista = poDniu.get(dzien) ?? [];
              return (
                <div key={data} className={cn("min-h-24 rounded-md border p-1 text-left",
                  data === dzis ? "border-primary ring-1 ring-primary" : "bg-card")}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{dzien}</span>
                    <Link href={`/przyjecia/nowe/?data=${data}`} title="Dodaj przyjęcie tego dnia"
                      className="rounded px-1 text-xs text-muted-foreground hover:bg-accent">+</Link>
                  </div>
                  {lista.map((p) => (
                    <Link key={p.id} href={`/przyjecia/${p.id}/`}
                      className={cn("mt-1 block truncate rounded px-1 py-0.5 text-xs",
                        p.status === "odwolana" ? "bg-red-50 text-red-800 line-through"
                          : p.status === "wstepna" ? "bg-amber-100 text-amber-900" : "bg-primary text-primary-foreground")}>
                      {p.start && p.data === data ? `${p.start} ` : ""}{p.klient} ({p.osoby_opis || p.goscie})
                    </Link>
                  ))}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </Layout>
  );
}
