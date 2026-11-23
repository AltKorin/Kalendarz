import { router, usePage } from "@inertiajs/react";
import { kolorySkorki } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BanerZgody, StopkaPubliczna } from "@/components/Publiczne";
import type { Wspolne } from "@/lib/typy";

type Demo = { id: string; przycisk: string; opis: string };

const CO_ROBI = [
  { tytul: "Przyjęcia z menu", tekst: "Komunia, chrzciny, stypa: wybierasz menu i liczbę gości, a kalendarz liczy wycenę, ilości dla kuchni i godziny etapów." },
  { tytul: "Plan obsługi dla działów", tekst: "Kuchnia, sala i bar dostają swoje zadania z godzinami i kratkami do odhaczenia. Gościom — agenda na jedną stronę A4." },
  { tytul: "Grupy i pobyty hotelowe", tekst: "Terminy kilkudniowe z liczbą osób albo opisem („ok. 90?”, „cały hotel”). Widać nakładające się terminy i wolne okna." },
  { tytul: "Wydruki czarno-białe", tekst: "Lista terminów do rozdania, kalendarz pon–nd i pełne zestawienie — A4, oszczędnie w tonerze, z datą stanu." },
];

export default function Start({ demo, demo_godzin, sso, ga }: { demo: Demo[]; demo_godzin: number; sso: boolean; ga: string }) {
  const { lokal, komunikaty, konto_url } = usePage<Wspolne>().props;
  return (
    <div style={kolorySkorki(lokal.kolory)} className="skorka min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
          <span className="text-lg font-bold text-primary">Kalendarz przyjęć</span>
          <Button variant="outline" size="sm" asChild><a href={sso ? "/oidc/login/" : "/logowanie/"}>Zaloguj się</a></Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4">
        {komunikaty.map((k, i) => (
          <p key={i} className="mt-4 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">{k.tekst}</p>
        ))}
        <section className="py-12 md:py-16">
          <p className="text-sm font-semibold uppercase tracking-wide text-[var(--brand-akcent)]">Dla restauracji i hoteli</p>
          <h1 className="mt-2 max-w-3xl text-3xl font-bold leading-tight text-primary md:text-5xl">
            Wszystkie przyjęcia i grupy w jednym kalendarzu — z planem dla kuchni, sali i baru.
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
            Wpisujesz termin, menu i liczbę gości. Kalendarz rozpisuje, kto co robi i o której, liczy ilości i drukuje
            to, co pracownicy powieszą na zapleczu.
          </p>
          {demo.length > 0 && (
            <div className="mt-8">
              <p className="mb-3 font-semibold">Wypróbuj bez zakładania konta:</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {demo.map((d) => (
                  <button key={d.id} type="button" onClick={() => router.post(`/demo/${d.id}/`)}
                    className="rounded-lg border-2 border-primary bg-card p-4 text-left transition hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <span className="block text-lg font-bold text-primary">Demo: {d.przycisk} →</span>
                    <span className="mt-1 block text-sm text-muted-foreground">{d.opis}</span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted-foreground">Demo to Twoja kopia z przykładowymi danymi — możesz wszystko zmieniać, zniknie po {demo_godzin} godz.</p>
            </div>
          )}
        </section>

        <section className="grid gap-4 pb-12 sm:grid-cols-2">
          {CO_ROBI.map((c) => (
            <Card key={c.tytul} className="gap-2">
              <CardHeader><CardTitle className="text-primary">{c.tytul}</CardTitle></CardHeader>
              <CardContent className="text-sm text-muted-foreground">{c.tekst}</CardContent>
            </Card>
          ))}
        </section>

        <section className="mb-12 rounded-lg bg-secondary p-6">
          <h2 className="text-xl font-bold text-primary">Własny kalendarz dla Twojego lokalu</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Konto zakładasz raz w Koncie sudomie — tym samym loginem wchodzisz do Kalendarza, Grafiku i innych narzędzi.
            Pracowników zapraszasz mailem; każdy widzi tylko dane swojego lokalu.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button asChild><a href={`${konto_url}/rejestracja/?produkt=kalendarz`}>Załóż konto firmy</a></Button>
            {sso && <Button variant="outline" asChild><a href="/oidc/login/">Mam konto — zaloguj</a></Button>}
          </div>
        </section>
      </main>

      <StopkaPubliczna ga={ga} />
      <BanerZgody ga={ga} />
    </div>
  );
}
