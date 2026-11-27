import { Link, router } from "@inertiajs/react";
import { useState } from "react";
import Layout from "@/components/Layout";
import { Potwierdz } from "@/components/Potwierdz";
import { Status, Umowa } from "@/components/Status";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { kiedy, type Opcja, osoby, type Wiersz } from "@/lib/typy";
import { cn } from "@/lib/utils";

type Props = {
  przyjecie: Wiersz & { telefon: string; doroslych: number; dzieci: number; tort: string | null };
  wycena: string[]; do_potwierdzenia: string[]; plan: boolean;
  program: { od: string; tytul: string; opis: string[] }[];
  obowiazki: { od: string; dzial: string; dzial_nazwa: string; zadanie: string; pozycje: string[] }[];
  dzialy: Opcja[]; umowy: Opcja[];
};

export default function Przyjecie({ przyjecie: p, wycena, do_potwierdzenia, plan, program, obowiazki, dzialy, umowy }: Props) {
  const [dzial, setDzial] = useState<string>("");
  const widoczne = obowiazki.filter((o) => !dzial || o.dzial === dzial);
  return (
    <Layout>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-akcent">{p.rodzaj}</p>
          <h1 className="text-3xl font-bold text-primary">{p.klient}</h1>
          <p className="mt-1 text-muted-foreground">
            {kiedy(p)} · {p.osoby_opis || `${p.doroslych} dorosłych${p.dzieci ? ` + ${p.dzieci} dzieci` : ""}`}
            {p.menu && <> · {p.menu}</>}{p.sale && <> · {p.sale}</>}
            {p.telefon && <> · tel. <a className="underline" href={`tel:${p.telefon}`}>{p.telefon}</a></>}
          </p>
          <div className="mt-2 flex flex-wrap gap-2"><Status status={p.status} nazwa={p.status_nazwa} /><Umowa umowa={p.umowa} nazwa={p.umowa_nazwa} /></div>
        </div>
        <div className="nie-drukuj flex flex-wrap gap-2">
          <Button asChild><a href={`/przyjecia/${p.id}/umowa.docx`}>Umowa (Word)</a></Button>
          {plan && <Button asChild><a href={`/przyjecia/${p.id}/agenda.docx`}>Agenda (Word)</a></Button>}
          {plan && <Button asChild><a href={`/przyjecia/${p.id}/plan.docx`}>Plan obsługi (Word)</a></Button>}
          <Button variant="outline" onClick={() => window.print()}>Drukuj</Button>
          <Button variant="outline" asChild><Link href={`/przyjecia/${p.id}/edycja/`}>Zmień</Link></Button>
          <Potwierdz przycisk={<Button variant="outline" className="text-destructive">Usuń</Button>}
            tytul={`Usunąć przyjęcie „${p.klient}”?`}
            skutek={`${kiedy(p)}, ${osoby(p)}. Przyjęcie zniknie z kalendarza; ślad zostaje w historii zmian. Odwołane przyjęcie lepiej oznaczyć statusem „Odwołana”.`}
            tak="Usuń przyjęcie" onTak={() => router.post(`/przyjecia/${p.id}/usun/`)} />
        </div>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-3">
        {wycena.length > 0 ? (
          <Card className="gap-2">
            <CardHeader><CardTitle>Wycena</CardTitle></CardHeader>
            <CardContent className="space-y-1 text-sm">
              {wycena.map((l) => <p key={l} className={cn(/^(Razem|Do zapłaty)/.test(l) && "font-bold")}>{l}</p>)}
            </CardContent>
          </Card>
        ) : (
          <Card className="gap-2">
            <CardHeader><CardTitle>Termin</CardTitle></CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p><b>{kiedy(p)}</b></p>
              <p>Osoby: <b>{osoby(p)}</b></p>
              <p>Sale: {p.sale || <span className="text-muted-foreground">do uzupełnienia</span>}</p>
            </CardContent>
          </Card>
        )}
        <Card className={cn("gap-2", p.uwagi && "border-destructive/50 bg-destructive/5")}>
          <CardHeader><CardTitle className={cn(p.uwagi && "text-destructive")}>Diety, alergie, uwagi</CardTitle></CardHeader>
          <CardContent className="text-sm">
            <p className={cn(p.uwagi ? "font-semibold text-destructive" : "text-muted-foreground")}>{p.uwagi || "Brak"}</p>
            {p.tort && <p className="mt-2 font-semibold">Tort o {p.tort}</p>}
          </CardContent>
        </Card>
        {do_potwierdzenia.length > 0 && (
          <Card className="gap-2 border-amber-300 bg-amber-50">
            <CardHeader><CardTitle>Do potwierdzenia</CardTitle></CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1 text-sm">{do_potwierdzenia.map((d) => <li key={d}>{d}</li>)}</ul>
            </CardContent>
          </Card>
        )}
      </div>

      <Card className="nie-drukuj mb-5 gap-2 py-4">
        <CardContent className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 text-sm">
          <span className="font-semibold">Umowa z klientem</span>
          <ToggleGroup type="single" variant="outline" size="sm" value={p.umowa} aria-label="Stan umowy"
            onValueChange={(v) => v && v !== p.umowa && router.post(`/przyjecia/${p.id}/umowa/`, { umowa: v }, { preserveScroll: true })}>
            {umowy.map((u) => <ToggleGroupItem key={String(u.id)} value={String(u.id)} className="px-3 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">{u.nazwa}</ToggleGroupItem>)}
          </ToggleGroup>
          <span className="basis-full text-muted-foreground">„Umowa (Word)” to wzór z danymi przyjęcia: przed wysłaniem uzupełnij [nawiasy] i dopasuj zasady do lokalu.</span>
        </CardContent>
      </Card>

      {!plan && (
        <p className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
          Ten termin nie ma menu, więc nie ma agendy ani planu obsługi. Wybierz menu i godzinę w „Zmień”, żeby je
          wyliczyć — albo drukuj terminy w <Link className="underline" href="/terminy/">Wydrukach</Link>.
        </p>
      )}
      {plan && <div className="grid gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Agenda dla gości</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {program.map((e) => (
              <div key={e.od + e.tytul} className="flex gap-3 border-b pb-2 last:border-0">
                <span className="w-12 shrink-0 font-bold text-primary">{e.od}</span>
                <div>
                  <p className="font-semibold">{e.tytul}</p>
                  {e.opis.map((o) => <p key={o} className="text-sm text-muted-foreground">{o}</p>)}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <CardTitle>Plan obsługi</CardTitle>
            <div className="nie-drukuj flex flex-wrap gap-1">
              {[{ id: "", nazwa: "Wszyscy" }, ...dzialy].map((d) => (
                <Button key={String(d.id)} size="sm" variant={dzial === d.id ? "default" : "outline"} onClick={() => setDzial(String(d.id))}>
                  {d.nazwa}
                </Button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {widoczne.map((o, i) => (
              <label key={i} className="flex cursor-pointer gap-3 rounded-md border p-2 has-checked:bg-secondary has-checked:opacity-60">
                <input type="checkbox" className="mt-1 size-4 accent-[var(--primary)]" />
                <span className="w-12 shrink-0 font-bold text-primary">{o.od}</span>
                <div className="min-w-0">
                  <p className="font-semibold">{o.zadanie} <span className="text-xs font-normal text-muted-foreground">· {o.dzial_nazwa}</span></p>
                  <ul className="text-sm text-muted-foreground">{o.pozycje.map((x) => <li key={x}>• {x}</li>)}</ul>
                </div>
              </label>
            ))}
            <p className="nie-drukuj text-xs text-muted-foreground">Kratki to pomoc na ekranie — nie zapisują się. Do druku: „Plan obsługi (Word)”.</p>
          </CardContent>
        </Card>
      </div>}
    </Layout>
  );
}
