import { router } from "@inertiajs/react";
import { useState } from "react";
import Layout from "@/components/Layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type W = { nr: number; opis: string; stan: "nowe" | "jest" | "blad"; bledy: string[] };
const STAN = { nowe: ["Nowe", "bg-green-100 text-green-900"], jest: ["Już jest", "bg-stone-100 text-stone-700"], blad: ["Błąd", "bg-red-50 text-red-800"] };

export default function Import({ blad, wiersze }: { blad: string | null; wiersze: W[] | null }) {
  const [plik, setPlik] = useState<File | null>(null);
  const [czeka, setCzeka] = useState(false);
  const wyslij = (zatwierdz: boolean) => {
    if (!plik) return;
    router.post("/import/", { plik, zatwierdz: zatwierdz ? "1" : "0" },
      { forceFormData: true, preserveState: true, onStart: () => setCzeka(true), onFinish: () => setCzeka(false) });
  };
  const nowych = wiersze?.filter((w) => w.stan === "nowe").length ?? 0;
  return (
    <Layout tytul="Import z Excela">
      <Card className="mb-5">
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Wybierz plik „Kalendarz przyjęć” wypełniany w Excelu. Najpierw zobaczysz podgląd — nic się nie zapisze, dopóki nie klikniesz „Importuj”.
            Przyjęcia, które już są w panelu (ta sama data, godzina i klient), zostaną pominięte — import można powtarzać.
          </p>
          <div className="flex flex-wrap gap-2">
            <Input type="file" accept=".xlsx" className="max-w-sm" onChange={(e) => setPlik(e.target.files?.[0] ?? null)} />
            <Button disabled={!plik || czeka} onClick={() => wyslij(false)}>Sprawdź plik</Button>
          </div>
          {blad && <p className="text-sm text-destructive">{blad}</p>}
        </CardContent>
      </Card>
      {wiersze && (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <CardTitle>Podgląd: {nowych} nowych z {wiersze.length}</CardTitle>
            <Button disabled={!nowych || czeka} onClick={() => wyslij(true)}>Importuj {nowych} nowych</Button>
          </CardHeader>
          <CardContent className="space-y-1">
            {wiersze.length === 0 && <p className="text-sm text-muted-foreground">W pliku nie ma przyjęć (wiersz PRZYKŁAD jest pomijany).</p>}
            {wiersze.map((w) => (
              <div key={w.nr} className="flex flex-wrap items-center gap-3 border-b py-1.5 text-sm last:border-0">
                <span className="w-8 text-muted-foreground">{w.nr}.</span>
                <Badge variant="outline" className={STAN[w.stan][1]}>{STAN[w.stan][0]}</Badge>
                <span>{w.opis}</span>
                {w.bledy.length > 0 && <span className="text-destructive">— {w.bledy.join(", ")}</span>}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </Layout>
  );
}
