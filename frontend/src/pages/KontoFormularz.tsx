import { Link, useForm } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { Pole } from "@/components/Pole";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { Bledy } from "@/lib/typy";

type K = { id?: number; login: string; imie: string; haslo: string; aktywne: boolean; kierownik: boolean };

export default function KontoFormularz({ konto, bledy, edycja }: { konto: K; bledy: Bledy; edycja: boolean }) {
  const form = useForm<K>(konto);
  return (
    <Layout tytul={edycja ? `Konto — ${konto.login}` : "Nowa osoba w zespole"}>
      <Card className="max-w-xl">
        <CardContent>
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); form.post(edycja ? `/zespol/${konto.id}/` : "/zespol/nowe/", { preserveState: true }); }}>
            <Pole etykieta="Imię" blad={bledy.imie}><Input value={form.data.imie} onChange={(e) => form.setData("imie", e.target.value)} placeholder="np. Ania" /></Pole>
            <Pole etykieta="Login" blad={bledy.login} podpowiedz={edycja ? "Loginu nie zmieniamy." : undefined}>
              <Input value={form.data.login} disabled={edycja} onChange={(e) => form.setData("login", e.target.value)} autoComplete="off" />
            </Pole>
            <Pole etykieta={edycja ? "Nowe hasło" : "Hasło"} blad={bledy.haslo} podpowiedz={edycja ? "Puste = hasło bez zmian. Minimum 10 znaków." : "Minimum 10 znaków."}>
              <Input type="password" value={form.data.haslo} onChange={(e) => form.setData("haslo", e.target.value)} autoComplete="new-password" />
            </Pole>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.data.kierownik} onChange={(e) => form.setData("kierownik", e.target.checked)} /> Kierownik (może zmieniać konta zespołu)</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.data.aktywne} onChange={(e) => form.setData("aktywne", e.target.checked)} /> Konto włączone</label>
            <div className="flex gap-2">
              <Button disabled={form.processing}>Zapisz</Button>
              <Button variant="outline" asChild><Link href="/zespol/">Anuluj</Link></Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </Layout>
  );
}
