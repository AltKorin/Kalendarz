import { Link, router } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { Status } from "@/components/Status";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { kiedy, type Miesiac, osoby, type Wiersz, zl } from "@/lib/typy";
import { NawigacjaMiesiaca } from "./Pulpit";

export default function Przyjecia({ miesiac, przyjecia }: { miesiac: Miesiac; przyjecia: Wiersz[] }) {
  return (
    <Layout>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <NawigacjaMiesiaca miesiac={miesiac} sciezka="/przyjecia/" />
        <div className="flex gap-2">
          <Button variant="outline" asChild><Link href="/terminy/">Wydruki i wolne terminy</Link></Button>
          <Button variant="outline" asChild><Link href="/import/">Import z Excela</Link></Button>
          <Button asChild><Link href="/przyjecia/nowe/">+ Dodaj przyjęcie</Link></Button>
        </div>
      </div>
      <Card className="py-0">
        <CardContent className="px-0">
          {przyjecia.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">Brak przyjęć i terminów w tym miesiącu. Dodaj pierwsze albo zaimportuj z Excela.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Kiedy</TableHead><TableHead>Klient / impreza</TableHead>
                  <TableHead>Rodzaj</TableHead><TableHead className="text-right">Goście</TableHead><TableHead>Menu</TableHead>
                  <TableHead className="text-right">Razem</TableHead><TableHead className="text-right">Zadatek</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {przyjecia.map((p) => (
                  <TableRow key={p.id} className="cursor-pointer" onClick={() => router.visit(`/przyjecia/${p.id}/`)}>
                    <TableCell className="whitespace-nowrap font-medium">{kiedy(p)}</TableCell>
                    <TableCell className="font-medium text-primary">{p.klient}{p.uwagi && <span className="ml-1 text-destructive" title={p.uwagi}>⚠</span>}</TableCell>
                    <TableCell>{p.rodzaj}</TableCell>
                    <TableCell className="text-right">{osoby(p)}</TableCell>
                    <TableCell>{p.menu ?? "—"}</TableCell>
                    <TableCell className="text-right">{p.menu ? zl(p.razem) : "—"}</TableCell>
                    <TableCell className="text-right">{zl(p.zadatek)}</TableCell>
                    <TableCell><Status status={p.status} nazwa={p.status_nazwa} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
