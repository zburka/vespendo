import type {
  Elofizetes,
  Kategoria,
  Koltsegkeret,
  MegtakaritasiCel,
  Tranzakcio,
} from '../types';

export const KATEGORIAK: Kategoria[] = [
  { id: 'kat_elelmiszer', nev: 'Élelmiszer', tipus: 'kiadas', ikon: 'cart' },
  { id: 'kat_rezsi', nev: 'Rezsi', tipus: 'kiadas', ikon: 'flash' },
  { id: 'kat_szorakozas', nev: 'Szórakozás', tipus: 'kiadas', ikon: 'film' },
  { id: 'kat_ruhazat', nev: 'Ruházat', tipus: 'kiadas', ikon: 'shirt' },
  { id: 'kat_fizetes', nev: 'Fizetés', tipus: 'bevetel', ikon: 'cash' },
];

type T = Omit<Tranzakcio, 'id' | 'forras' | 'allapot' | 'fizetesi_mod'> &
  Partial<Pick<Tranzakcio, 'forras' | 'allapot' | 'fizetesi_mod'>>;

const raw: T[] = [
  // 2026-09
  { datum: '2026-09-01', osszeg: 520000, kereskedo: 'Munkabér - Férj', kategoria_id: 'kat_fizetes', tipus: 'bevetel_rendszeres', tulajdonos: 'kozos', fizetesi_mod: 'atutalas' },
  { datum: '2026-09-05', osszeg: 430000, kereskedo: 'Munkabér - Feleség', kategoria_id: 'kat_fizetes', tipus: 'bevetel_rendszeres', tulajdonos: 'kozos', fizetesi_mod: 'atutalas' },
  { datum: '2026-09-08', osszeg: 74000, kereskedo: 'MVM Zrt.', kategoria_id: 'kat_rezsi', tipus: 'kiadas', tulajdonos: 'kozos', fizetesi_mod: 'atutalas' },
  { datum: '2026-09-10', osszeg: 38500, kereskedo: 'LIDL', kategoria_id: 'kat_elelmiszer', tipus: 'kiadas', tulajdonos: 'kozos' },
  { datum: '2026-09-15', osszeg: 4490, kereskedo: 'Netflix', kategoria_id: 'kat_szorakozas', tipus: 'kiadas', tulajdonos: 'kozos' },
  { datum: '2026-09-21', osszeg: 52300, kereskedo: 'SPAR', kategoria_id: 'kat_elelmiszer', tipus: 'kiadas', tulajdonos: 'kozos' },
  { datum: '2026-09-27', osszeg: 19990, kereskedo: 'H&M', kategoria_id: 'kat_ruhazat', tipus: 'kiadas', tulajdonos: 'feleseg' },
  // 2026-10
  { datum: '2026-10-01', osszeg: 520000, kereskedo: 'Munkabér - Férj', kategoria_id: 'kat_fizetes', tipus: 'bevetel_rendszeres', tulajdonos: 'kozos', fizetesi_mod: 'atutalas', forras: 'bank_import' },
  { datum: '2026-10-05', osszeg: 430000, kereskedo: 'Munkabér - Feleség', kategoria_id: 'kat_fizetes', tipus: 'bevetel_rendszeres', tulajdonos: 'kozos', fizetesi_mod: 'atutalas', forras: 'bank_import' },
  { datum: '2026-10-07', osszeg: 78000, kereskedo: 'MVM Zrt.', kategoria_id: 'kat_rezsi', tipus: 'kiadas', tulajdonos: 'kozos', fizetesi_mod: 'atutalas', forras: 'bank_import' },
  { datum: '2026-10-09', osszeg: 46200, kereskedo: 'LIDL', kategoria_id: 'kat_elelmiszer', tipus: 'kiadas', tulajdonos: 'kozos', forras: 'bank_import' },
  { datum: '2026-10-12', osszeg: 31800, kereskedo: 'SPAR', kategoria_id: 'kat_elelmiszer', tipus: 'kiadas', tulajdonos: 'kozos', forras: 'bank_import' },
  { datum: '2026-10-13', osszeg: 15000, kereskedo: 'Zara', kategoria_id: 'kat_ruhazat', tipus: 'kiadas', tulajdonos: 'feleseg', forras: 'bank_import' },
  { datum: '2026-10-15', osszeg: 4490, kereskedo: 'Netflix', kategoria_id: 'kat_szorakozas', tipus: 'kiadas', tulajdonos: 'kozos', forras: 'bank_import' },
  { datum: '2026-10-15', osszeg: 12000, kereskedo: 'Lidl Magyarország', kategoria_id: 'kat_elelmiszer', tipus: 'kiadas', tulajdonos: 'ferj', forras: 'nyugta_foto', allapot: 'banki_egyeztetesre_var', megjegyzes: '7000 ruha, 5000 zöldség' },
  { datum: '2026-10-16', osszeg: 8500, kereskedo: 'Mozi', kategoria_id: 'kat_szorakozas', tipus: 'kiadas', tulajdonos: 'ferj', fizetesi_mod: 'keszpenz', forras: 'kezi' },
];

export const TRANZAKCIOK: Tranzakcio[] = raw.map((t, i) => ({
  fizetesi_mod: 'kartya',
  forras: 'bank_import',
  allapot: 'lezart',
  ...t,
  id: `rec${i + 1}`,
}));

export const KOLTSEGKERETEK: Koltsegkeret[] = [
  { id: 'kk1', kategoria_id: 'kat_elelmiszer', havi_keret: 180000, aktiv: true },
  { id: 'kk2', kategoria_id: 'kat_rezsi', havi_keret: 80000, aktiv: true },
  { id: 'kk3', kategoria_id: 'kat_szorakozas', havi_keret: 30000, aktiv: true },
  { id: 'kk4', kategoria_id: 'kat_ruhazat', havi_keret: 40000, aktiv: true },
];

export const ELOFIZETESEK: Elofizetes[] = [
  { id: 'e1', megnevezes: 'Netflix Családi', varhato_osszeg: 4490, esedekesseg_napja: 15, kategoria_id: 'kat_szorakozas' },
  { id: 'e2', megnevezes: 'Claude Pro', varhato_osszeg: 8000, esedekesseg_napja: 20, kategoria_id: 'kat_szorakozas' },
  { id: 'e3', megnevezes: 'Edzőterem', varhato_osszeg: 14900, esedekesseg_napja: 25, kategoria_id: 'kat_szorakozas' },
];

export const CELOK: MegtakaritasiCel[] = [
  { id: 'c1', cel_neve: 'Olaszországi nyaralás', celosszeg: 800000, aktualis_osszeg: 310000 },
  { id: 'c2', cel_neve: 'Vészhelyzeti tartalék', celosszeg: 1500000, aktualis_osszeg: 900000 },
];

export const AI_ELEMZESEK: Record<string, string> = {
  '2026-09': 'Szeptemberben az élelmiszer kiadásaitok a keret alatt maradtak, a megtakarítási célokhoz bőven jutott pénz.',
  '2026-10': 'Ebben a hónapban a rezsi keretetek majdnem elérte a maximumot. Az élelmiszer költéseitek a megszokott ütemben alakulnak, a közös megtakarítási célhoz további 100 000 Ft félretehető.',
};
