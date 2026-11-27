import { Badge } from "@/components/ui/badge";

const STYL: Record<string, string> = {
  wstepna: "bg-amber-100 text-amber-900 border-amber-300",
  potwierdzona: "bg-green-100 text-green-900 border-green-300",
  odbyla: "bg-stone-100 text-stone-700 border-stone-300",
  odwolana: "bg-red-50 text-red-800 border-red-200 line-through",
};

export function Status({ status, nazwa }: { status: string; nazwa: string }) {
  return <Badge variant="outline" className={STYL[status]}>{nazwa}</Badge>;
}

const STYL_UMOWY: Record<string, string> = {
  brak: "border-dashed text-muted-foreground",
  wyslana: "bg-secondary text-primary border-primary/40",  // barwy lokalu (Słownik Kolorów), nie nowy odcień
  podpisana: "bg-green-100 text-green-900 border-green-300",
};

export function Umowa({ umowa, nazwa }: { umowa: string; nazwa: string }) {
  return <Badge variant="outline" className={STYL_UMOWY[umowa]}>{nazwa}</Badge>;
}
