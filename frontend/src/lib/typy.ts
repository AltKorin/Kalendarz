export type Lokal = {
  nazwa: string; kolory: Record<string, string>; fonty?: Record<string, string>; logo: string | null; demo_do: string | null;
};
export type Wspolne = {
  lokal: Lokal;
  konto_url: string;
  rezerwacje: boolean;
  sala: boolean;
  uzytkownik: { nazwa: string; kierownik: boolean } | null;
  komunikaty: { tekst: string; poziom: string }[];
};
export type Wiersz = {
  id: number; data: string; dzien: string; koniec: string | null; start: string | null; klient: string; rodzaj: string;
  goscie: number; osoby_opis: string; sale: string; menu: string | null; razem: string; zadatek: string; do_zaplaty: string; status: string; status_nazwa: string; uwagi: string;
  umowa: string; umowa_nazwa: string;
};
export type Miesiac = {
  klucz: string; nazwa: string; poprzedni: string; nastepny: string; pierwszy_dzien_tygodnia: number; dni: number;
};
export type Opcja = { id: string | number; nazwa: string };
export type Bledy = Record<string, string>;

const SKROT = ["nd", "pon", "wt", "śr", "czw", "pt", "sob"];
const dzienMies = (iso: string) => `${Number(iso.slice(8, 10))}.${iso.slice(5, 7)}`;
const skrot = (iso: string) => SKROT[new Date(`${iso}T12:00`).getDay()];

/** „sob 22.11, 14:00” albo „pt 27.11 – nd 29.11” (termin kilkudniowy). */
export const kiedy = (p: Pick<Wiersz, "data" | "koniec" | "start">) =>
  p.koniec && p.koniec !== p.data
    ? `${skrot(p.data)} ${dzienMies(p.data)} – ${skrot(p.koniec)} ${dzienMies(p.koniec)}`
    : `${skrot(p.data)} ${dzienMies(p.data)}${p.start ? `, ${p.start}` : ""}`;

/** Liczba gości albo opis planistyczny („ok. 90?”, „cały hotel (planujemy)”). */
export const osoby = (p: Pick<Wiersz, "goscie" | "osoby_opis">) => p.osoby_opis || (p.goscie ? `${p.goscie} os.` : "—");

export const zl = (kwota: string | number) =>
  Number(kwota || 0).toLocaleString("pl-PL", { style: "currency", currency: "PLN" });
