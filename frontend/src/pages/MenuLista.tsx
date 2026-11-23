import { Link, router } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { Potwierdz } from "@/components/Potwierdz";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { zl } from "@/lib/typy";

type M = { id: number; nazwa: string; cena_os: string; aktywne: boolean; etapow: number; przyjec: number };

export default function MenuLista({ menu }: { menu: M[] }) {
  return (
    <Layout tytul="Menu przyjęć">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-muted-foreground">
          Menu to dania z porcjami i przebieg przyjęcia (co, kiedy i który dział). Z niego liczą się agenda, plan obsługi i ilości dla kuchni.
        </p>
        <Button asChild><Link href="/menu/nowe/">+ Dodaj menu</Link></Button>
      </div>
      <Card className="py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nazwa</TableHead><TableHead className="text-right">Cena / os.</TableHead>
                <TableHead className="text-right">Etapów</TableHead><TableHead className="text-right">Przyjęć</TableHead>
                <TableHead /><TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {menu.map((m) => (
                <TableRow key={m.id}>
                  <TableCell className="font-medium text-primary">
                    {m.nazwa} {!m.aktywne && <Badge variant="outline" className="ml-2">niedostępne</Badge>}
                  </TableCell>
                  <TableCell className="text-right">{zl(m.cena_os)}</TableCell>
                  <TableCell className="text-right">{m.etapow}</TableCell>
                  <TableCell className="text-right">{m.przyjec}</TableCell>
                  <TableCell className="text-right"><Button size="sm" variant="outline" asChild><Link href={`/menu/${m.id}/`}>Zmień</Link></Button></TableCell>
                  <TableCell className="text-right">
                    <Potwierdz przycisk={<Button size="sm" variant="outline" className="text-destructive">Usuń</Button>}
                      tytul={`Usunąć „${m.nazwa}”?`}
                      skutek={m.przyjec ? `To menu jest w ${m.przyjec} przyjęciach — nie da się go usunąć. Zamiast tego w edycji odznacz „dostępne przy nowych przyjęciach”.`
                        : `Usunie też ${m.etapow} etapów z daniami. Tego nie da się cofnąć.`}
                      tak="Usuń menu" onTak={() => router.post(`/menu/${m.id}/usun/`)} />
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
