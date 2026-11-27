import { Link, router } from "@inertiajs/react";
import { useState } from "react";
import Layout from "@/components/Layout";
import { Potwierdz } from "@/components/Potwierdz";
import { Plotno, type StolikRzut } from "@/components/RzutSali";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type Rezerwacja = {
  id: number; data: string; od: string; do: string; klient: string; telefon: string; osoby: number;
  stoliki: string[]; stoliki_id: number[]; uwagi: string; status: string; status_nazwa: string;
};
type Props = {
  dzien: string; nazwa_dnia: string; dzis: string; poprzedni: string; nastepny: string; rezerwacje: Rezerwacja[];
  osob: number; stoliki: (StolikRzut & { zajety: string[] })[]; rzut: boolean;
};

/** Widok z adresu (?widok=lista|rzut); bez niego rzut, gdy sala jest ułożona — to główny obraz dnia w restauracji. */
const widokZAdresu = (domyslny: string) =>
  (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("widok")) || domyslny;

/** Dziś: teraz zaokrąglone w dół do kwadransa; inny dzień: 18:00. */
const godzinaStartowa = (dzien: string, dzis: string) => {
  if (dzien !== dzis) return "18:00";
  const t = new Date();
  return `${String(t.getHours()).padStart(2, "0")}:${String(Math.floor(t.getMinutes() / 15) * 15).padStart(2, "0")}`;
};

function RzutZajetosci({ dzien, dzis, stoliki, rezerwacje }: Pick<Props, "dzien" | "dzis" | "stoliki" | "rezerwacje">) {
  const [godz, setGodz] = useState(godzinaStartowa(dzien, dzis));
  const aktywne = rezerwacje.filter((r) => r.status !== "odwolana");
  const nieustawione = stoliki.filter((s) => s.x === null).length;
  if (stoliki.every((s) => s.x === null)) {
    return <p className="p-6 text-sm text-muted-foreground">Stoliki nie są jeszcze ułożone. <Link href="/stoliki/" className="underline">Ułóż salę w Stolikach</Link>.</p>;
  }
  return (
    <div className="space-y-3 p-4">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2 font-medium">Godzina <Input type="time" step={900} className="w-32" value={godz} onChange={(e) => e.target.value && setGodz(e.target.value)} /></label>
        <span className="flex items-center gap-1.5"><span className="size-3 rounded-sm border-2 border-green-700 bg-card" /> wolny</span>
        <span className="flex items-center gap-1.5"><span className="size-3 rounded-sm bg-primary" /> zajęty</span>
        {nieustawione > 0 && <span className="text-muted-foreground">({nieustawione} poza rzutem)</span>}
      </div>
      <Plotno stoliki={stoliki} stolik={(s, styl) => {
        const moje = aktywne.filter((r) => r.stoliki_id.includes(s.id));
        const teraz = moje.find((r) => r.od <= godz && godz < r.do);
        const potem = moje.filter((r) => r.od > godz).sort((a, b) => a.od.localeCompare(b.od))[0];
        return (
          <Link key={s.id} style={styl} href={teraz ? `/rezerwacje/${teraz.id}/` : `/rezerwacje/nowa/?d=${dzien}&od=${godz}&stolik=${s.id}`}
            title={teraz ? `${teraz.klient}, ${teraz.osoby} os., ${teraz.od}–${teraz.do}` : `Wolny — dodaj rezerwację na ${godz}`}
            className={cn("flex flex-col items-center justify-center overflow-hidden border-2 px-1 text-center leading-tight shadow-sm hover:ring-2 hover:ring-ring",
              teraz ? "border-primary bg-primary text-primary-foreground" : "border-green-700 bg-card text-primary")}>
            <b className="text-sm">{s.numer}</b>
            {teraz && <span className="hidden w-full truncate text-[11px] sm:block">{teraz.klient}</span>}
            <span className="hidden w-full truncate text-[11px] sm:block">
              {teraz ? `do ${teraz.do}` : potem ? `do ${potem.od}` : "wolny"}
            </span>
          </Link>
        );
      }} />
      <p className="text-xs text-muted-foreground">Kliknij wolny stolik, żeby dodać rezerwację na wybraną godzinę, albo zajęty, żeby ją otworzyć.</p>
    </div>
  );
}

export default function Rezerwacje({ dzien, nazwa_dnia, dzis, poprzedni, nastepny, rezerwacje, osob, stoliki, rzut }: Props) {
  const [widok, setWidok] = useState(rzut ? widokZAdresu(stoliki.some((s) => s.x !== null) ? "rzut" : "lista") : "lista");
  const idz = (d: string) => router.get("/rezerwacje/", rzut ? { d, widok } : { d }, { preserveScroll: true });
  const przelacz = (w: string) => {
    setWidok(w);
    window.history.replaceState(window.history.state, "", `/rezerwacje/?d=${dzien}&widok=${w}`);
  };
  return (
    <Layout>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => idz(poprzedni)} aria-label="Poprzedni dzień">←</Button>
          <Input type="date" className="w-40" value={dzien} onChange={(e) => e.target.value && idz(e.target.value)} />
          <Button variant="outline" size="sm" onClick={() => idz(nastepny)} aria-label="Następny dzień">→</Button>
          <h1 className="text-xl font-bold text-primary">{nazwa_dnia}</h1>
          {dzien !== dzis && <Button variant="ghost" size="sm" onClick={() => idz(dzis)}>Dziś</Button>}
        </div>
        <div className="flex flex-wrap gap-2">
          {rzut && (
            <div className="flex rounded-md border p-0.5" role="group" aria-label="Widok">
              {[["lista", "Lista"], ["rzut", "Rzut sali"]].map(([w, nazwa]) => (
                <Button key={w} size="sm" variant={widok === w ? "default" : "ghost"} aria-pressed={widok === w} onClick={() => przelacz(w)}>{nazwa}</Button>
              ))}
            </div>
          )}
          <Button variant="outline" asChild><Link href="/stoliki/">Stoliki</Link></Button>
          <Button asChild><Link href={`/rezerwacje/nowa/?d=${dzien}`}>+ Dodaj rezerwację</Link></Button>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="min-w-0 self-start py-0 lg:col-span-2">
          <CardContent className="px-0">
            {widok === "rzut" ? <RzutZajetosci dzien={dzien} dzis={dzis} stoliki={stoliki} rezerwacje={rezerwacje} /> : rezerwacje.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground">Brak rezerwacji tego dnia.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Godziny</TableHead><TableHead>Nazwisko</TableHead><TableHead className="text-right">Osób</TableHead>
                    <TableHead>Stolik</TableHead><TableHead>Uwagi</TableHead><TableHead /><TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rezerwacje.map((r) => (
                    <TableRow key={r.id} className={r.status === "odwolana" ? "text-muted-foreground line-through" : ""}>
                      <TableCell className="whitespace-nowrap font-medium">{r.od}–{r.do}</TableCell>
                      <TableCell>
                        <span className="text-primary">{r.klient}</span>
                        {r.telefon && <span className="block text-xs text-muted-foreground">{r.telefon}</span>}
                        {r.status === "odwolana" && <Badge variant="outline" className="ml-1">odwołana</Badge>}
                      </TableCell>
                      <TableCell className="text-right">{r.osoby}</TableCell>
                      <TableCell className="font-semibold">{r.stoliki.join(", ") || "—"}</TableCell>
                      <TableCell className="max-w-56 text-sm">{r.uwagi}</TableCell>
                      <TableCell><Button size="sm" variant="outline" asChild><Link href={`/rezerwacje/${r.id}/`}>Zmień</Link></Button></TableCell>
                      <TableCell>
                        <Potwierdz przycisk={<Button size="sm" variant="outline" className="text-destructive">Usuń</Button>}
                          tytul={`Usunąć rezerwację „${r.klient}”?`}
                          skutek={`${r.od}–${r.do}, ${r.osoby} os. Rezerwacja zniknie z listy. Jeśli goście odwołali, lepiej ustaw status „Odwołana” — zostanie ślad.`}
                          tak="Usuń rezerwację" onTak={() => router.post(`/rezerwacje/${r.id}/usun/`)} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card className="self-start">
          <CardHeader><CardTitle>Stoliki — {osob} os. zarezerwowanych</CardTitle></CardHeader>
          <CardContent className="space-y-1.5 text-sm">
            {stoliki.length === 0 && (
              <p className="text-muted-foreground">Nie ma jeszcze stolików. <Link href="/stoliki/" className="underline">Dodaj stoliki</Link>, żeby przypisywać je do rezerwacji.</p>
            )}
            {stoliki.map((s) => (
              <div key={s.id} className="flex justify-between gap-3 border-b pb-1.5 last:border-0">
                <span><b>{s.numer}</b> <span className="text-muted-foreground">({s.miejsc} os.)</span></span>
                <span className={s.zajety.length ? "text-right" : "text-right text-green-800"}>{s.zajety.join(", ") || "wolny"}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
