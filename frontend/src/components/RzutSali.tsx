import type { CSSProperties, ReactNode, Ref } from "react";
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
