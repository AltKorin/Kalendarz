import { Link, router } from "@inertiajs/react";
import { useRef, useState } from "react";
import Layout from "@/components/Layout";
import { klasaSelect } from "@/components/Pole";
import { Potwierdz } from "@/components/Potwierdz";
import { Plotno, type StolikRzut } from "@/components/RzutSali";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { Opcja } from "@/lib/typy";
import { cn } from "@/lib/utils";

type S = StolikRzut & { przyszlych: number; wczesniejszych: number };

/** Jeden wiersz = formularz: nowy stolik albo zmiana istniejącego. */
function Wiersz({ s, ksztalty }: { s?: S; ksztalty: Opcja[] }) {
  const [numer, setNumer] = useState(s?.numer ?? "");
  const [miejsc, setMiejsc] = useState(String(s?.miejsc ?? 4));
  const [ksztalt, setKsztalt] = useState(s?.ksztalt ?? "prostokatny");
  const zmieniony = !s || numer !== s.numer || miejsc !== String(s.miejsc) || ksztalt !== s.ksztalt;
  const zapisz = (e: React.FormEvent) => {
    e.preventDefault();
    router.post("/stoliki/", { id: s?.id ?? null, numer, miejsc, ksztalt }, {
      preserveScroll: true, onSuccess: () => { if (!s) { setNumer(""); setMiejsc("4"); setKsztalt("prostokatny"); } },
    });
  };
  return (
    <form onSubmit={zapisz} className="flex flex-wrap items-center gap-2 border-b py-2 last:border-0">
      <Input aria-label="Numer stolika" placeholder={s ? "" : "nowy, np. 12"} className="w-32" value={numer} onChange={(e) => setNumer(e.target.value)} />
      <Input aria-label="Miejsc" type="number" min={1} max={99} className="w-20" value={miejsc} onChange={(e) => setMiejsc(e.target.value)} />
      <span className="text-sm text-muted-foreground">miejsc</span>
      <select aria-label="Kształt" className={cn(klasaSelect, "w-36")} value={ksztalt} onChange={(e) => setKsztalt(e.target.value)}>
        {ksztalty.map((k) => <option key={k.id} value={k.id}>{k.nazwa}</option>)}
      </select>
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

type Poz = Record<number, { x: number | null; y: number | null }>;
const zakres = (v: number) => Math.round(Math.min(1000, Math.max(0, v)));
/** k-te miejsce w siatce 6 × 3 (potem od nowa z przesunięciem) — nowe stoliki nie lądują jeden na drugim. */
const miejsceWSiatce = (k: number) => [100 + (k % 6) * 160 + Math.floor(k / 18) * 40, 170 + (Math.floor(k / 6) % 3) * 300] as const;

/** Układanie sali: przeciągnij stolik (mysz/palec) albo zaznacz i przesuwaj strzałkami. Zapis jednym przyciskiem. */
function Uklad({ stoliki }: { stoliki: S[] }) {
  const start: Poz = Object.fromEntries(stoliki.map((s) => [s.id, { x: s.x, y: s.y }]));
  const [poz, setPoz] = useState<Poz>(start);
  const [wybrany, setWybrany] = useState<number | null>(null);
  const [chwyt, setChwyt] = useState<number | null>(null);
  const plotno = useRef<HTMLDivElement>(null);
  const zmieniony = stoliki.some((s) => poz[s.id]?.x !== s.x || poz[s.id]?.y !== s.y);
  const ustaw = (id: number, x: number | null, y: number | null) =>
    setPoz((p) => ({ ...p, [id]: { x: x === null ? null : zakres(x), y: y === null ? null : zakres(y) } }));
  const doPlotna = (e: React.PointerEvent) => {
    const r = plotno.current!.getBoundingClientRect();
    return [((e.clientX - r.left) / r.width) * 1000, ((e.clientY - r.top) / r.height) * 1000] as const;
  };
  const strzalki = (e: React.KeyboardEvent, id: number) => {
    const krok = e.shiftKey ? 50 : 10;
    const ruch = ({ ArrowLeft: [-krok, 0], ArrowRight: [krok, 0], ArrowUp: [0, -krok], ArrowDown: [0, krok] } as Record<string, number[]>)[e.key];
    if (!ruch) return;
    e.preventDefault();
    const p = poz[id];
    ustaw(id, (p.x ?? 500) + ruch[0], (p.y ?? 500) + ruch[1]);
  };
  const naRzucie = stoliki.map((s) => ({ ...s, ...poz[s.id] }));
  const poza = naRzucie.filter((s) => s.x === null);
  const postaw = (lista: typeof poza) => {
    const zajete = naRzucie.length - poza.length;
    lista.forEach((s, i) => ustaw(s.id, ...miejsceWSiatce(zajete + i)));
  };
  const zaznaczony = naRzucie.find((s) => s.id === wybrany && s.x !== null);
  return (
    <Card className="mt-5 max-w-4xl">
      <CardHeader><CardTitle>Rzut sali</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">Przeciągnij stolik w jego miejsce. Na klawiaturze: kliknij stolik i przesuwaj strzałkami (z Shift szybciej).</p>
        {poza.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted-foreground">Poza rzutem:</span>
            {poza.map((s) => (
              <Button key={s.id} type="button" size="sm" variant="outline" onClick={() => { postaw([s]); setWybrany(s.id); }}>
                + {s.numer}
              </Button>
            ))}
            {poza.length > 1 && <Button type="button" size="sm" onClick={() => postaw(poza)}>Postaw wszystkie</Button>}
          </div>
        )}
        <Plotno stoliki={naRzucie} plotnoRef={plotno} stolik={(s, styl) => (
          <button key={s.id} type="button" style={styl} aria-label={`Stolik ${s.numer}, ${s.miejsc} miejsc`}
            className={cn("flex cursor-grab items-center justify-center border-2 bg-card text-sm font-bold text-primary shadow-sm active:cursor-grabbing",
              s.id === wybrany ? "border-primary ring-2 ring-ring" : "border-primary/50")}
            onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); setChwyt(s.id); setWybrany(s.id); }}
            onPointerMove={(e) => { if (chwyt === s.id) { const [x, y] = doPlotna(e); ustaw(s.id, x, y); } }}
            onPointerUp={() => setChwyt(null)}
            onKeyDown={(e) => strzalki(e, s.id)}>
            {s.numer}
          </button>
        )} />
        <div className="flex flex-wrap gap-2">
          {zmieniony && <Button type="button" onClick={() => router.post("/stoliki/", { uklad: naRzucie.map(({ id, x, y }) => ({ id, x, y })) }, { preserveScroll: true })}>Zapisz układ</Button>}
          {zmieniony && <Button type="button" variant="outline" onClick={() => setPoz(start)}>Cofnij zmiany</Button>}
          {zaznaczony && <Button type="button" variant="outline" onClick={() => ustaw(zaznaczony.id, null, null)}>Zdejmij {zaznaczony.numer} z rzutu</Button>}
        </div>
      </CardContent>
    </Card>
  );
}

export default function Stoliki({ stoliki, czas, rzut, ksztalty }: { stoliki: S[]; czas: number; rzut: boolean; ksztalty: Opcja[] }) {
  const [minuty, setMinuty] = useState(String(czas));
  const razem = stoliki.reduce((a, s) => a + s.miejsc, 0);
  return (
    <Layout tytul="Stoliki">
      <div className="grid max-w-4xl gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Stolików: {stoliki.length} · miejsc: {razem}</CardTitle></CardHeader>
          <CardContent>
            {stoliki.map((s) => <Wiersz key={`${s.id}-${s.numer}-${s.miejsc}-${s.ksztalt}`} s={s} ksztalty={ksztalty} />)}
            <Wiersz ksztalty={ksztalty} />
          </CardContent>
        </Card>
        <Card className="self-start">
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
      {rzut && stoliki.length > 0 && <Uklad key={stoliki.map((s) => `${s.id}:${s.x}:${s.y}`).join()} stoliki={stoliki} />}
      <Button variant="outline" className="mt-5" asChild>{rzut ? <Link href="/sala/">← Sala</Link> : <Link href="/rezerwacje/">← Rezerwacje</Link>}</Button>
    </Layout>
  );
}
