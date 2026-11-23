import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { SUDOMIE_HUB, SUDOMIE_PRODUCTS } from "@/lib/sudomie";
import { uruchomAnalityke, wybierz, wybor } from "@/lib/zgoda";

export const POLITYKA = "https://sudomie.pl/polityka-prywatnosci.html#kalendarz";

/** Baner zgody na statystyki — tylko gdy wdrożenie ma GA (ga ≠ ""). Wraca po „Ustawienia cookies”. */
export function BanerZgody({ ga }: { ga: string }) {
  const [otwarty, setOtwarty] = useState(false);
  useEffect(() => {
    if (!ga) return;
    uruchomAnalityke(ga);
    setOtwarty(wybor() === null);
    const otworz = () => setOtwarty(true);
    window.addEventListener("cc:open", otworz);
    return () => window.removeEventListener("cc:open", otworz);
  }, [ga]);
  if (!otwarty) return null;
  const wybrano = (w: "accepted" | "declined") => { wybierz(w); setOtwarty(false); };
  return (
    <div role="region" aria-label="Zgoda na statystyki"
      className="fixed inset-x-0 bottom-0 z-50 border-t bg-card p-4 shadow-lg">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3">
        <p className="flex-1 text-sm">
          Używamy Google Analytics, żeby wiedzieć, jak korzystasz z tej strony. Bez zgody nie zapisujemy cookies
          statystycznych. <a className="underline" href={POLITYKA}>Polityka prywatności</a>
        </p>
        <Button onClick={() => wybrano("accepted")}>Akceptuję</Button>
        <Button variant="outline" onClick={() => wybrano("declined")}>Odrzucam</Button>
      </div>
    </div>
  );
}

/** Stopka stron publicznych: regulamin, polityka, cookies, kontakt + narzędzia sudomie. */
export function StopkaPubliczna({ ga }: { ga: string }) {
  return (
    <footer className="border-t bg-card pb-24 sm:pb-6">
      <div className="mx-auto max-w-5xl space-y-3 px-4 pt-6 text-sm text-muted-foreground">
        <p className="flex flex-wrap gap-x-4 gap-y-1">
          <a className="underline" href="/regulamin/">Regulamin</a>
          <a className="underline" href={POLITYKA}>Polityka prywatności</a>
          {ga && <button type="button" className="underline" onClick={() => window.dispatchEvent(new Event("cc:open"))}>Ustawienia cookies</button>}
          <a className="underline" href="mailto:kontakt@sudomie.pl">kontakt@sudomie.pl</a>
          <a className="underline" href="tel:+48668341191">+48 668 341 191</a>
        </p>
        <nav aria-label="Narzędzia sudomie">
          Narzędzia sudomie:{" "}
          {SUDOMIE_PRODUCTS.map((p) => (
            <span key={p.id}><a className="underline" href={p.url} title={p.pl}>{p.name}</a> · </span>
          ))}
          <a className="underline" href={SUDOMIE_HUB.url}>{SUDOMIE_HUB.pl}</a>
        </nav>
      </div>
    </footer>
  );
}
