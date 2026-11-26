import { Link, router, usePage } from "@inertiajs/react";
import type { CSSProperties, ReactNode } from "react";
import { Button } from "@/components/ui/button";
import type { Wspolne } from "@/lib/typy";
import { cn } from "@/lib/utils";

const MENU = [
  { href: "/", nazwa: "Pulpit" },
  { href: "/przyjecia/", nazwa: "Przyjęcia" },
  { href: "/rezerwacje/", nazwa: "Rezerwacje", flaga: "rezerwacje" as const },
  { href: "/terminy/", nazwa: "Wydruki" },
  { href: "/menu/", nazwa: "Menu" },
  { href: "/import/", nazwa: "Import z Excela" },
];
const KIEROWNIK = [{ href: "/zespol/", nazwa: "Zespół" }, { href: "/ustawienia/", nazwa: "Ustawienia" }];

const ZAPASOWE = { tytul: ', Georgia, serif', tekst: ', "Segoe UI", system-ui, sans-serif' };

export function kolorySkorki(k: Record<string, string>, fonty?: Record<string, string>): CSSProperties {
  return {
    ...(fonty?.tytul ? { "--font-tytul": `"${fonty.tytul}"${ZAPASOWE.tytul}` } : {}),
    ...(fonty?.tekst ? { "--font-tekst": `"${fonty.tekst}"${ZAPASOWE.tekst}` } : {}),
    "--primary": `#${k.glowny}`, "--accent-foreground": `#${k.glowny}`, "--brand-akcent": `#${k.akcent}`,
    "--ring": `#${k.linia}`, "--secondary": `#${k.tlo_naglowka}`, "--muted": `#${k.tlo_naglowka}`,
    "--accent": `#${k.tlo_naglowka}`,
  } as CSSProperties;
}

export default function Layout({ children, tytul }: { children: ReactNode; tytul?: string }) {
  const { props, url } = usePage<Wspolne>();
  const { lokal, uzytkownik, komunikaty, konto_url } = props;
  const menu = MENU.filter((m) => !m.flaga || props[m.flaga]);
  const aktywny = (href: string) => (href === "/" ? url === "/" || url.startsWith("/?") : url.startsWith(href));
  return (
    <div style={kolorySkorki(lokal.kolory, lokal.fonty)} className="skorka min-h-screen">
      {lokal.demo_do && (
        <div className="nie-drukuj bg-primary px-4 py-2 text-center text-sm text-primary-foreground">
          To jest demo „{lokal.nazwa}” — zmieniaj śmiało, wszystko zniknie{" "}
          {new Date(lokal.demo_do).toLocaleString("pl-PL", { weekday: "long", hour: "2-digit", minute: "2-digit" })}.{" "}
          <a className="font-semibold underline" href={`${konto_url}/rejestracja/?produkt=kalendarz`}>Załóż własne konto</a>
        </div>
      )}
      <header className="nie-drukuj border-b bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/" className="flex items-center gap-3">
            {lokal.logo && <img src={lokal.logo} alt="" className="h-10 w-auto" />}
            <span className="leading-tight">
              <span className="block font-[family-name:var(--font-tytul)] text-lg font-bold text-primary">Kalendarz przyjęć</span>
              {!lokal.logo && <span className="block text-xs text-muted-foreground">{lokal.nazwa}</span>}
            </span>
          </Link>
          <nav className="flex flex-wrap gap-1">
            {[...menu, ...(uzytkownik?.kierownik ? KIEROWNIK : [])].map((m) => (
              <Link key={m.href} href={m.href}
                className={cn("rounded-md px-3 py-1.5 text-sm font-medium hover:bg-accent",
                  aktywny(m.href) ? "bg-primary text-primary-foreground hover:bg-primary" : "text-foreground")}>
                {m.nazwa}
              </Link>
            ))}
          </nav>
          {uzytkownik && (
            <div className="ml-auto flex items-center gap-3 text-sm text-muted-foreground">
              <span>{uzytkownik.nazwa}</span>
              <Button variant="outline" size="sm" onClick={() => router.post("/wyloguj/")}>Wyloguj</Button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        {komunikaty.map((k, i) => (
          <div key={i} className={cn("nie-drukuj mb-4 rounded-md border px-4 py-3 text-sm",
            k.poziom === "error" ? "border-destructive/40 bg-destructive/10 text-destructive" : "border-green-700/30 bg-green-50 text-green-900")}>
            {k.tekst}
          </div>
        ))}
        {tytul && <h1 className="mb-5 text-2xl font-bold text-primary">{tytul}</h1>}
        {children}
      </main>
    </div>
  );
}
