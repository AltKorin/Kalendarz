import { Link } from "@inertiajs/react";
import { type CSSProperties, type ReactNode, type Ref, useState } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type StolikRzut = { id: number; numer: string; miejsc: number; ksztalt: string; x: number | null; y: number | null };

/** Rozmiar na płótnie z liczby miejsc: do 4 os. kwadrat/koło, większy prostokąt się wydłuża. */
export function ksztaltStolika(s: Pick<StolikRzut, "miejsc" | "ksztalt">): CSSProperties {
  const okragly = s.ksztalt === "okragly";
  const dlugosc = okragly ? 1 : Math.max(1, Math.min(s.miejsc, 12) / 4);
  const baza = okragly ? 6 + Math.min(s.miejsc, 10) * 0.6 : 8;
  // minWidth: na telefonie stolik ma być do trafienia palcem (≥ 36 px)
  return { width: `${baza * dlugosc}%`, minWidth: `${2.25 * dlugosc}rem`, aspectRatio: `${dlugosc}`, borderRadius: okragly ? "9999px" : "0.4rem" };
}

/** Płótno 3:2; stolik w środku (x, y) promili. Kolor, treść i zachowanie stolika ustala wołający. */
export function Plotno({ stoliki, stolik, plotnoRef, className }: {
  stoliki: StolikRzut[];
  stolik: (s: StolikRzut, styl: CSSProperties) => ReactNode;
  plotnoRef?: Ref<HTMLDivElement>;
  className?: string;
}) {
  return (
    <div ref={plotnoRef} className={cn("relative aspect-[3/2] w-full touch-none select-none overflow-hidden rounded-md border-2 border-dashed bg-secondary/60", className)}>
      {stoliki.filter((s) => s.x !== null && s.y !== null).map((s) => stolik(s, {
        position: "absolute", left: `${(s.x ?? 0) / 10}%`, top: `${(s.y ?? 0) / 10}%`, transform: "translate(-50%, -50%)",
        ...ksztaltStolika(s),
      }))}
    </div>
  );
}

export type Rezerwacja = {
  id: number; data: string; od: string; do: string; klient: string; telefon: string; osoby: number;
  stoliki: string[]; stoliki_id: number[]; uwagi: string; status: string; status_nazwa: string;
};

/** Dziś: teraz zaokrąglone w dół do kwadransa; inny dzień: 18:00. */
const godzinaStartowa = (dzien: string, dzis: string) => {
  if (dzien !== dzis) return "18:00";
  const t = new Date();
  return `${String(t.getHours()).padStart(2, "0")}:${String(Math.floor(t.getMinutes() / 15) * 15).padStart(2, "0")}`;
};

/** Zajętość stolików o wybranej godzinie: strona „Sala” i karta „Sala dziś” na pulpicie. */
export function RzutZajetosci({ dzien, dzis, stoliki, rezerwacje }: { dzien: string; dzis: string; stoliki: StolikRzut[]; rezerwacje: Rezerwacja[] }) {
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
