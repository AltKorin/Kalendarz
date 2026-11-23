import { Link, useForm } from "@inertiajs/react";
import Layout from "@/components/Layout";
import { klasaSelect, Pole } from "@/components/Pole";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { Bledy, Opcja } from "@/lib/typy";

type Poz = { nazwa: string; dla_gosci: boolean; porcja: string; miara: string };
type Etap = { po_min: string; tytul: string; dzial: string; zadanie: string; pozycje: Poz[] };
type MenuDane = { id?: number; nazwa: string; cena_os: string; cena_dziecko: string; aktywne: boolean; etapy: Etap[] };

export default function MenuFormularz({ menu, bledy, dzialy, miary }: { menu: MenuDane; bledy: Bledy; dzialy: Opcja[]; miary: Opcja[] }) {
  const form = useForm<MenuDane>({
    ...menu,
    etapy: menu.etapy.map((e) => ({ ...e, po_min: String(e.po_min), pozycje: e.pozycje.map((p) => ({ ...p, porcja: p.porcja ?? "" })) })),
  });
  const etapy = form.data.etapy;
  const ustawEtapy = (nowe: Etap[]) => form.setData("etapy", nowe);
  const zmienEtap = (i: number, zm: Partial<Etap>) => ustawEtapy(etapy.map((e, j) => (j === i ? { ...e, ...zm } : e)));
  const zmienPoz = (i: number, j: number, zm: Partial<Poz>) =>
    zmienEtap(i, { pozycje: etapy[i].pozycje.map((p, k) => (k === j ? { ...p, ...zm } : p)) });
  const zapisz = (e: React.FormEvent) => {
    e.preventDefault();
    form.post(menu.id ? `/menu/${menu.id}/` : "/menu/nowe/", { preserveState: true, preserveScroll: true });
  };
  return (
    <Layout tytul={menu.id ? `Menu — ${menu.nazwa}` : "Nowe menu"}>
      <form onSubmit={zapisz} className="space-y-5">
        <Card>
          <CardContent className="grid gap-4 sm:grid-cols-4">
            <Pole etykieta="Nazwa" blad={bledy.nazwa} className="sm:col-span-2">
              <Input value={form.data.nazwa} onChange={(e) => form.setData("nazwa", e.target.value)} placeholder="np. Menu 3" />
            </Pole>
            <Pole etykieta="Cena za osobę (zł)" blad={bledy.cena_os}>
              <Input type="number" step="0.01" min={0} value={form.data.cena_os} onChange={(e) => form.setData("cena_os", e.target.value)} />
            </Pole>
            <Pole etykieta="Cena za dziecko (zł)" blad={bledy.cena_dziecko} podpowiedz="Puste = dzieci nie wliczane">
              <Input type="number" step="0.01" min={0} value={form.data.cena_dziecko} onChange={(e) => form.setData("cena_dziecko", e.target.value)} />
            </Pole>
            <label className="flex items-center gap-2 text-sm sm:col-span-4">
              <input type="checkbox" className="size-4" checked={form.data.aktywne} onChange={(e) => form.setData("aktywne", e.target.checked)} />
              Dostępne przy nowych przyjęciach
            </label>
          </CardContent>
        </Card>

        <p className="text-sm text-muted-foreground">
          Etap = co robi dany dział i kiedy. <b>Minuty od startu</b>: 0 = przyjście gości, -20 = 20 minut wcześniej, 180 = po 3 godzinach.
          Pozycja z porcją to danie — kuchnia dostaje ilość (porcja × goście). Pozycja bez „dla gości” widzi tylko obsługa (np. „Obrusy, nakrycia”).
          Etapy układają się same według minut.
        </p>
        {bledy.etapy && <p className="text-sm text-destructive">{bledy.etapy}</p>}

        {etapy.map((e, i) => (
          <Card key={i} className="gap-3">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Etap {i + 1}</CardTitle>
              <Button type="button" size="sm" variant="ghost" className="text-destructive"
                onClick={() => ustawEtapy(etapy.filter((_, j) => j !== i))}>Usuń etap</Button>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-12">
                <Pole etykieta="Minuty od startu" blad={bledy[`etapy.${i}.po_min`]} className="sm:col-span-2">
                  <Input type="number" value={e.po_min} onChange={(ev) => zmienEtap(i, { po_min: ev.target.value })} />
                </Pole>
                <Pole etykieta="Dział" blad={bledy[`etapy.${i}.dzial`]} className="sm:col-span-2">
                  <select className={klasaSelect} value={e.dzial} onChange={(ev) => zmienEtap(i, { dzial: ev.target.value })}>
                    <option value="">—</option>
                    {dzialy.map((d) => <option key={d.id} value={d.id}>{d.nazwa}</option>)}
                  </select>
                </Pole>
                <Pole etykieta="Zadanie dla obsługi" blad={bledy[`etapy.${i}.zadanie`]} className="sm:col-span-5">
                  <Input value={e.zadanie} onChange={(ev) => zmienEtap(i, { zadanie: ev.target.value })} placeholder="np. Obiad serwowany — zupa" />
                </Pole>
                <Pole etykieta="Etap w agendzie gości" podpowiedz="Puste = tylko obsługa" className="sm:col-span-3">
                  <Input value={e.tytul} onChange={(ev) => zmienEtap(i, { tytul: ev.target.value })} placeholder="np. Obiad" />
                </Pole>
              </div>
              <div className="space-y-2 rounded-md bg-secondary/60 p-3">
                {e.pozycje.map((p, j) => (
                  <div key={j} className="grid items-start gap-2 sm:grid-cols-12">
                    <div className="sm:col-span-6">
                      <Input value={p.nazwa} placeholder="Danie albo punkt do zrobienia" onChange={(ev) => zmienPoz(i, j, { nazwa: ev.target.value })} />
                      {bledy[`etapy.${i}.pozycje.${j}.nazwa`] && <p className="text-xs text-destructive">{bledy[`etapy.${i}.pozycje.${j}.nazwa`]}</p>}
                    </div>
                    <label className="flex h-9 items-center gap-2 text-sm sm:col-span-2">
                      <input type="checkbox" checked={p.dla_gosci} onChange={(ev) => zmienPoz(i, j, { dla_gosci: ev.target.checked })} /> dla gości
                    </label>
                    <div className="sm:col-span-2">
                      <Input type="number" step="0.1" min={0} placeholder="porcja/os." value={p.porcja} onChange={(ev) => zmienPoz(i, j, { porcja: ev.target.value })} />
                      {bledy[`etapy.${i}.pozycje.${j}.porcja`] && <p className="text-xs text-destructive">{bledy[`etapy.${i}.pozycje.${j}.porcja`]}</p>}
                    </div>
                    <div className="sm:col-span-1">
                      <select className={klasaSelect} value={p.miara} onChange={(ev) => zmienPoz(i, j, { miara: ev.target.value })}>
                        {miary.map((m) => <option key={m.id} value={m.id}>{m.nazwa}</option>)}
                      </select>
                      {bledy[`etapy.${i}.pozycje.${j}.miara`] && <p className="text-xs text-destructive">{bledy[`etapy.${i}.pozycje.${j}.miara`]}</p>}
                    </div>
                    <Button type="button" variant="ghost" size="sm" className="sm:col-span-1" title="Usuń pozycję"
                      onClick={() => zmienEtap(i, { pozycje: e.pozycje.filter((_, k) => k !== j) })}>✕</Button>
                  </div>
                ))}
                <Button type="button" variant="outline" size="sm"
                  onClick={() => zmienEtap(i, { pozycje: [...e.pozycje, { nazwa: "", dla_gosci: e.dzial === "kuchnia", porcja: "", miara: e.dzial === "kuchnia" ? "g" : "" }] })}>
                  + Pozycja
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
        <Button type="button" variant="outline"
          onClick={() => ustawEtapy([...etapy, { po_min: String(Number(etapy.at(-1)?.po_min ?? 0) + 30), tytul: "", dzial: "kuchnia", zadanie: "", pozycje: [] }])}>
          + Etap
        </Button>

        <div className="sticky bottom-0 flex gap-2 border-t bg-background py-3">
          <Button type="submit" disabled={form.processing}>Zapisz menu</Button>
          <Button variant="outline" asChild><Link href="/menu/">Anuluj</Link></Button>
          {Object.keys(bledy).length > 0 && <span className="self-center text-sm text-destructive">Popraw zaznaczone pola.</span>}
        </div>
      </form>
    </Layout>
  );
}
