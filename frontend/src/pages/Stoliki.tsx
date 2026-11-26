import { Link, router } from "@inertiajs/react";
import { useState } from "react";
import Layout from "@/components/Layout";
import { Potwierdz } from "@/components/Potwierdz";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type S = { id: number; numer: string; miejsc: number; przyszlych: number; wczesniejszych: number };

/** Jeden wiersz = formularz: nowy stolik albo zmiana istniejącego. */
function Wiersz({ s }: { s?: S }) {
  const [numer, setNumer] = useState(s?.numer ?? "");
  const [miejsc, setMiejsc] = useState(String(s?.miejsc ?? 4));
  const zmieniony = !s || numer !== s.numer || miejsc !== String(s.miejsc);
  const zapisz = (e: React.FormEvent) => {
    e.preventDefault();
    router.post("/stoliki/", { id: s?.id ?? null, numer, miejsc }, {
      preserveScroll: true, onSuccess: () => { if (!s) { setNumer(""); setMiejsc("4"); } },
    });
  };
  return (
    <form onSubmit={zapisz} className="flex flex-wrap items-center gap-2 border-b py-2 last:border-0">
      <Input aria-label="Numer stolika" placeholder={s ? "" : "nowy, np. 12"} className="w-32" value={numer} onChange={(e) => setNumer(e.target.value)} />
      <Input aria-label="Miejsc" type="number" min={1} max={99} className="w-20" value={miejsc} onChange={(e) => setMiejsc(e.target.value)} />
      <span className="text-sm text-muted-foreground">miejsc</span>
      <div className="ml-auto flex gap-2">
        {zmieniony && <Button type="submit" size="sm" variant={s ? "default" : "outline"}>{s ? "Zapisz" : "+ Dodaj stolik"}</Button>}
        {s && (
          <Potwierdz przycisk={<Button type="button" size="sm" variant="outline" className="text-destructive">Usuń</Button>}
            tytul={`Usunąć stolik ${s.numer}?`}
            skutek={s.przyszlych
              ? `Stolik ma ${s.przyszlych} rezerwacji od dziś — nie da się go usunąć. Najpierw przenieś je na inny stolik albo odwołaj.`
              : s.wczesniejszych ? `Zniknie z ${s.wczesniejszych} wcześniejszych rezerwacji (historia zmian zostaje).` : "Stolik nie ma rezerwacji."}
            tak="Usuń stolik" onTak={() => router.post(`/stoliki/${s.id}/usun/`, {}, { preserveScroll: true })} />
        )}
      </div>
    </form>
  );
}

export default function Stoliki({ stoliki, czas }: { stoliki: S[]; czas: number }) {
  const [minuty, setMinuty] = useState(String(czas));
  const razem = stoliki.reduce((a, s) => a + s.miejsc, 0);
  return (
    <Layout tytul="Stoliki">
      <div className="grid max-w-4xl gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Stolików: {stoliki.length} · miejsc: {razem}</CardTitle></CardHeader>
          <CardContent>
            {stoliki.map((s) => <Wiersz key={`${s.id}-${s.numer}-${s.miejsc}`} s={s} />)}
            <Wiersz />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Czas rezerwacji</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); router.post("/stoliki/", { czas: minuty }, { preserveScroll: true }); }}>
              <label className="block space-y-1.5 text-sm">
                <span className="font-medium">Domyślnie (minuty)</span>
                <Input type="number" min={15} max={720} step={15} value={minuty} onChange={(e) => setMinuty(e.target.value)} />
              </label>
              <p className="text-xs text-muted-foreground">Podpowiada godzinę „do” w nowej rezerwacji. Przy małej imprezie zmienisz ją w samej rezerwacji.</p>
              {minuty !== String(czas) && <Button type="submit" size="sm">Zapisz</Button>}
            </form>
          </CardContent>
        </Card>
      </div>
      <Button variant="outline" className="mt-5" asChild><Link href="/rezerwacje/">← Rezerwacje</Link></Button>
    </Layout>
  );
}
