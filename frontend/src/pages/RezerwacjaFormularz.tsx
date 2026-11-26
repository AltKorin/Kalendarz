import { Link, useForm } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { klasaSelect, Pole } from "@/components/Pole";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { Bledy, Opcja } from "@/lib/typy";

type Props = {
  rezerwacja: Record<string, unknown>; bledy: Bledy; edycja: boolean; czas: number;
  stoliki: { id: number; numer: string; miejsc: number }[]; statusy: Opcja[];
};

/** „18:00” + 120 min → „20:00” (najpóźniej 23:59, jak na serwerze). */
const plus = (godz: string, min: number) => {
  const [h, m] = godz.split(":").map(Number);
  const t = Math.min(h * 60 + m + min, 23 * 60 + 59);
  return `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
};

export default function RezerwacjaFormularz({ rezerwacja, bledy, edycja, czas, stoliki, statusy }: Props) {
  const r = rezerwacja;
  const form = useForm({
    data: String(r.data ?? ""), od: String(r.od ?? ""), do: String(r.do || (r.od ? plus(String(r.od), czas) : "")),
    klient: String(r.klient ?? ""), telefon: String(r.telefon ?? ""), osoby: String(r.osoby ?? ""),
    stoliki: ((r.stoliki as (number | string)[]) ?? []).map(Number), uwagi: String(r.uwagi ?? ""),
    status: String(r.status ?? "potwierdzona"),
  });
  const d = form.data;
  const wybrane = stoliki.filter((s) => d.stoliki.includes(s.id));
  const miejsc = wybrane.reduce((a, s) => a + s.miejsc, 0);
  const zmienOd = (od: string) => {
    // koniec idzie za początkiem, dopóki nikt nie ustawił go ręcznie na inny czas
    form.setData((f) => ({ ...f, od, do: !f.do || f.do === plus(f.od, czas) ? (od ? plus(od, czas) : "") : f.do }));
  };
  const przelacz = (id: number) =>
    form.setData("stoliki", d.stoliki.includes(id) ? d.stoliki.filter((x) => x !== id) : [...d.stoliki, id]);
  const zapisz = (e: React.FormEvent) => {
    e.preventDefault();
    form.post(edycja ? `/rezerwacje/${r.id}/` : "/rezerwacje/nowa/", { preserveState: true, preserveScroll: true });
  };
  const tekst = (nazwa: "data" | "do" | "klient" | "telefon" | "osoby" | "uwagi" | "status") => ({
    value: d[nazwa], onChange: (e: { target: { value: string } }) => form.setData(nazwa, e.target.value),
  });
  return (
    <Layout tytul={edycja ? `Zmień rezerwację — ${r.klient}` : "Nowa rezerwacja stolika"}>
      <form onSubmit={zapisz} className="max-w-3xl space-y-5">
        <Card>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <Pole etykieta="Data" blad={bledy.data}><Input type="date" {...tekst("data")} /></Pole>
            <Pole etykieta="Od" blad={bledy.od}><Input type="time" value={d.od} onChange={(e) => zmienOd(e.target.value)} /></Pole>
            <Pole etykieta="Do" blad={bledy.do} podpowiedz={`Domyślnie ${czas / 60} h. Mała impreza — ustaw dłużej.`}>
              <Input type="time" {...tekst("do")} />
            </Pole>
            <Pole etykieta="Nazwisko" blad={bledy.klient} className="sm:col-span-2"><Input {...tekst("klient")} /></Pole>
            <Pole etykieta="Osób" blad={bledy.osoby}><Input type="number" min={1} {...tekst("osoby")} /></Pole>
            <Pole etykieta="Telefon" blad={bledy.telefon}><Input type="tel" {...tekst("telefon")} /></Pole>
            <Pole etykieta="Status" blad={bledy.status}>
              <select className={klasaSelect} {...tekst("status")}>
                {statusy.map((s) => <option key={s.id} value={s.id}>{s.nazwa}</option>)}
              </select>
            </Pole>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="text-sm font-medium">Stoliki <span className="font-normal text-muted-foreground">— przy większej grupie zaznacz kilka</span></span>
              {wybrane.length > 0 && (
                <span className={Number(d.osoby) > miejsc ? "text-sm text-amber-700" : "text-sm text-muted-foreground"}>
                  {miejsc} miejsc{Number(d.osoby) > miejsc && ` — za mało na ${d.osoby} os.`}
                </span>
              )}
            </div>
            {stoliki.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nie ma jeszcze stolików — <Link href="/stoliki/" className="underline">dodaj je</Link>. Rezerwację można zapisać bez stolika.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {stoliki.map((s) => (
                  <label key={s.id} className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-secondary">
                    <input type="checkbox" className="size-4" checked={d.stoliki.includes(s.id)} onChange={() => przelacz(s.id)} />
                    <b>{s.numer}</b> <span className="text-muted-foreground">{s.miejsc} os.</span>
                  </label>
                ))}
              </div>
            )}
            {bledy.stoliki && <p className="text-sm text-destructive">{bledy.stoliki}</p>}
            <Pole etykieta="Uwagi" blad={bledy.uwagi}><Textarea rows={2} placeholder="np. urodziny, tort własny, krzesełko dla dziecka" {...tekst("uwagi")} /></Pole>
          </CardContent>
        </Card>
        <div className="flex gap-2">
          <Button type="submit" disabled={form.processing}>Zapisz</Button>
          <Button variant="outline" asChild><Link href={`/rezerwacje/?d=${d.data}`}>Anuluj</Link></Button>
        </div>
      </form>
    </Layout>
  );
}
