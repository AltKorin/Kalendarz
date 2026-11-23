import { useForm, usePage } from "@inertiajs/react";
import { kolorySkorki } from "@/components/Layout";
import { Pole } from "@/components/Pole";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { Bledy, Wspolne } from "@/lib/typy";

export default function Logowanie({ bledy, sso }: { bledy: Bledy; sso: { nazwa: string } | null }) {
  const { lokal, komunikaty } = usePage<Wspolne>().props;
  const next = new URLSearchParams(window.location.search).get("next") ?? "/";
  const form = useForm({ login: "", haslo: "" });
  return (
    <div style={kolorySkorki(lokal.kolory, lokal.fonty)} className="flex min-h-screen items-center justify-center bg-secondary px-4">
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-5 pt-6">
          <div className="text-center">
            {lokal.logo && <img src={lokal.logo} alt={lokal.nazwa} className="mx-auto h-24 w-auto" />}
            <h1 className="mt-3 text-xl font-bold text-primary">Kalendarz przyjęć</h1>
          </div>
          {komunikaty.map((k, i) => (
            <p key={i} className={k.poziom === "error" ? "rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive" : "rounded-md bg-secondary p-3 text-sm"}>{k.tekst}</p>
          ))}
          {sso && (
            <>
              <Button asChild className="w-full" variant="default">
                <a href={`/oidc/login/?next=${encodeURIComponent(next)}`}>Zaloguj przez {sso.nazwa}</a>
              </Button>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="h-px flex-1 bg-border" />albo loginem i hasłem kalendarza<span className="h-px flex-1 bg-border" />
              </div>
            </>
          )}
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); form.post(window.location.pathname + window.location.search, { preserveState: true }); }}>
            <Pole etykieta="Login">
              <Input autoFocus autoComplete="username" value={form.data.login} onChange={(e) => form.setData("login", e.target.value)} />
            </Pole>
            <Pole etykieta="Hasło" blad={bledy.haslo}>
              <Input type="password" autoComplete="current-password" value={form.data.haslo} onChange={(e) => form.setData("haslo", e.target.value)} />
            </Pole>
            <Button className="w-full" variant={sso ? "outline" : "default"} disabled={form.processing}>Zaloguj</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
