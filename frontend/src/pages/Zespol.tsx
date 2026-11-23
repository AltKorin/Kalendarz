import { Link, router } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { Potwierdz } from "@/components/Potwierdz";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type K = { id: number; login: string; imie: string; aktywne: boolean; kierownik: boolean; ostatnio: string | null };

export default function Zespol({ konta, ja }: { konta: K[]; ja: number }) {
  return (
    <Layout tytul="Zespół">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">Konta osób, które pracują w kalendarzu. Kierownik może dodawać i zmieniać konta.</p>
        <Button asChild><Link href="/zespol/nowe/">+ Dodaj osobę</Link></Button>
      </div>
      <Card className="py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow><TableHead>Imię</TableHead><TableHead>Login</TableHead><TableHead>Rola</TableHead><TableHead>Ostatnie logowanie</TableHead><TableHead /><TableHead /></TableRow>
            </TableHeader>
            <TableBody>
              {konta.map((k) => (
                <TableRow key={k.id} className={k.aktywne ? "" : "opacity-50"}>
                  <TableCell className="font-medium text-primary">{k.imie || "—"} {!k.aktywne && <Badge variant="outline">wyłączone</Badge>}</TableCell>
                  <TableCell>{k.login}</TableCell>
                  <TableCell>{k.kierownik ? "Kierownik" : "Obsługa"}</TableCell>
                  <TableCell>{k.ostatnio ?? "nigdy"}</TableCell>
                  <TableCell className="text-right"><Button size="sm" variant="outline" asChild><Link href={`/zespol/${k.id}/`}>Zmień</Link></Button></TableCell>
                  <TableCell className="text-right">
                    {k.id !== ja && k.aktywne && (
                      <Potwierdz przycisk={<Button size="sm" variant="outline" className="text-destructive">Wyłącz</Button>}
                        tytul={`Wyłączyć konto „${k.login}”?`}
                        skutek="Ta osoba nie zaloguje się do kalendarza. Historia jej zmian zostaje. Konto można włączyć z powrotem w „Zmień”."
                        tak="Wyłącz konto" onTak={() => router.post(`/zespol/${k.id}/usun/`)} />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Layout>
  );
}
