import { router, usePage } from "@inertiajs/react";
import { useState } from "react";
import { kolorySkorki } from "@/components/Layout";
import { BanerZgody, POLITYKA, StopkaPubliczna } from "@/components/Publiczne";
import { Button } from "@/components/ui/button";
import type { Wspolne } from "@/lib/typy";

type Props = { html: string; wersja: string; ga: string; akceptacja: { kierownik: boolean; lokal: string } | null };

export default function Regulamin({ html, wersja, ga, akceptacja }: Props) {
  const { lokal } = usePage<Wspolne>().props;
  const [zaznaczone, setZaznaczone] = useState(false);
  return (
    <div style={kolorySkorki(lokal.kolory, lokal.fonty)} className="skorka min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3">
          <a href="/" className="text-lg font-bold text-primary">Kalendarz przyjęć</a>
          {akceptacja && <Button variant="outline" size="sm" onClick={() => router.post("/wyloguj/")}>Wyloguj</Button>}
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">
        {akceptacja && (
          <div className="mb-6 rounded-lg border-2 border-primary bg-card p-4">
            <p className="font-semibold text-primary">Zanim zaczniesz: regulamin dla „{akceptacja.lokal}”</p>
            {akceptacja.kierownik ? (
              <div className="mt-3 space-y-3">
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" className="mt-0.5 size-4" checked={zaznaczone} onChange={(e) => setZaznaczone(e.target.checked)} />
                  <span>Akceptuję regulamin (wersja {wersja}) w imieniu firmy, w tym umowę powierzenia danych z § 8,
                    i zapoznałem/am się z <a className="underline" href={POLITYKA}>polityką prywatności</a>.</span>
                </label>
                <Button disabled={!zaznaczone} onClick={() => router.post("/regulamin/akceptuj/", { akceptuje: true })}>
                  Akceptuję i przechodzę do kalendarza
                </Button>
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">
                Regulamin akceptuje kierownik lokalu. Gdy to zrobi, kalendarz otworzy się także dla Ciebie.
              </p>
            )}
          </div>
        )}
        <h1 className="text-3xl font-bold text-primary">Regulamin Kalendarza przyjęć</h1>
        {/* nasz własny plik z repo (przyjecia/dane/regulamin.html) — ten sam tekst, którego skrót zapisujemy */}
        <div className="regulamin mt-4" dangerouslySetInnerHTML={{ __html: html }} />
      </main>
      {!akceptacja && <StopkaPubliczna ga={ga} />}
      {!akceptacja && <BanerZgody ga={ga} />}
    </div>
  );
}
