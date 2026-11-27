import { Link, router } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { Potwierdz } from "@/components/Potwierdz";
import { type Rezerwacja, RzutZajetosci, type StolikRzut } from "@/components/RzutSali";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

type Props = {
  dzien: string; nazwa_dnia: string; dzis: string; poprzedni: string; nastepny: string; rezerwacje: Rezerwacja[];
  osob: number; stoliki: (StolikRzut & { zajety: string[] })[]; sala: boolean;
};


/** Ten sam dzień w dwóch miejscach menu: „Rezerwacje” (lista) i „Sala” (rzut z zajętością stolików). */
export default function Rezerwacje({ dzien, nazwa_dnia, dzis, poprzedni, nastepny, rezerwacje, osob, stoliki, sala }: Props) {
  const idz = (d: string) => router.get(sala ? "/sala/" : "/rezerwacje/", { d }, { preserveScroll: true });
  return (
    <Layout>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => idz(poprzedni)} aria-label="Poprzedni dzień">←</Button>
          <Input type="date" className="w-40" value={dzien} onChange={(e) => e.target.value && idz(e.target.value)} />
          <Button variant="outline" size="sm" onClick={() => idz(nastepny)} aria-label="Następny dzień">→</Button>
          <h1 className="text-xl font-bold text-primary">{sala && "Sala · "}{nazwa_dnia}</h1>
          {dzien !== dzis && <Button variant="ghost" size="sm" onClick={() => idz(dzis)}>Dziś</Button>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild><Link href="/stoliki/">{sala ? "Ułóż stoliki" : "Stoliki"}</Link></Button>
          <Button asChild><Link href={`/rezerwacje/nowa/?d=${dzien}`}>+ Dodaj rezerwację</Link></Button>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="min-w-0 self-start py-0 lg:col-span-2">
          <CardContent className="px-0">
            {sala ? <RzutZajetosci dzien={dzien} dzis={dzis} stoliki={stoliki} rezerwacje={rezerwacje} /> : rezerwacje.length === 0 ? (
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
