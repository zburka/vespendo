import { MOCK_MOD } from '../config';
import { hitelesitettFetch } from './auth';
import type {
  Alapadatok,
  BankiImportKeres,
  FajlElemzesKeres,
  FajlElemzesValasz,
  HaviOsszesito,
  ImportOsszegzes,
  KategoriaModositasKeres,
  NyugtaKeres,
  NyugtaValasz,
  Tranzakcio,
  UjTranzakcioKeres,
} from '../types';

/** Alapból élő módban fut; mock adatokkal csak `EXPO_PUBLIC_MOCK=1` esetén. */
export const ELO_API = !MOCK_MOD;

const IDOTUL_MS = 60_000;

async function keres<T>(
  utvonal: string,
  opciok: { method: 'GET' | 'POST'; body?: unknown; idotulMs?: number },
) {
  const vezerlo = new AbortController();
  const idozito = setTimeout(() => vezerlo.abort(), opciok.idotulMs ?? IDOTUL_MS);
  try {
    // a belépési kapu ellenőrzi a belépést és a háztartást, majd továbbítja a kérést az n8n-nek
    const res = await hitelesitettFetch(`/api/v/${utvonal}`, {
      method: opciok.method,
      headers: { 'Content-Type': 'application/json' },
      body: opciok.body === undefined ? undefined : JSON.stringify(opciok.body),
      signal: vezerlo.signal,
    });
    if (!res.ok) {
      const hibaTest = await res.json().catch(() => null);
      throw new Error(hibaTest?.uzenet ?? hibaTest?.hiba ?? `A szerver hibát jelzett (${res.status})`);
    }
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof Error && e.name === 'AbortError') throw new Error('Időtúllépés');
    throw e;
  } finally {
    clearTimeout(idozito);
  }
}

const kesleltet = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** `POST /api/v/nyugta-feltoltes` */
export async function feltoltNyugta(body: NyugtaKeres): Promise<NyugtaValasz> {
  if (ELO_API) return keres('nyugta-feltoltes', { method: 'POST', body });

  await kesleltet(2500);
  return {
    status: 'success',
    data: {
      kereskedo: 'Lidl Magyarország',
      osszeg: 12000,
      datum: new Date().toISOString().slice(0, 10),
      fizetesi_mod: 'kartya',
      allapot: 'banki_egyeztetesre_var',
      bontott_tetelek: [
        { kategoria: 'Ruházat', osszeg: 7000 },
        { kategoria: 'Élelmiszer', osszeg: 5000 },
      ],
    },
  };
}

/**
 * `POST /api/v/banki-fajl-elemzes`: bármilyen banki kivonat (PDF / XLSX / CSV) elemzése a szerveren
 * (token nélküli Python script). Csak élő módban hívható.
 */
export async function elemezBankiFajl(body: FajlElemzesKeres) {
  const valasz = await keres<FajlElemzesValasz>('banki-fajl-elemzes', { method: 'POST', body });
  if (valasz.status !== 'success' || !valasz.data) {
    throw new Error(valasz.uzenet ?? 'A fájl elemzése nem sikerült');
  }
  return valasz.data;
}

/**
 * `POST /api/v/banki-import`. Élő módban az n8n összegzését adja vissza, mock módban `null`
 * (ekkor a store helyi logikája dolgozik).
 */
export async function bankiImport(body: BankiImportKeres): Promise<ImportOsszegzes | null> {
  if (ELO_API) {
    const valasz = await keres<{ data?: ImportOsszegzes }>('banki-import', {
      method: 'POST',
      body,
    });
    return valasz.data ?? null;
  }
  await kesleltet(1500);
  return null;
}

/** `GET /api/v/adatok`: kategóriák, keretek, előfizetések, célok, szabályok. */
export function alapadatok(): Promise<Alapadatok> {
  return keres('adatok', { method: 'GET' });
}

/** `GET /api/v/tranzakciok[?honap=YYYY-MM]` */
export function tranzakciokLekeres(honap?: string): Promise<{ tranzakciok: Tranzakcio[] }> {
  return keres(`tranzakciok${honap ? `?honap=${honap}` : ''}`, { method: 'GET' });
}

/** `GET /api/v/havi-osszesito?honap=YYYY-MM`. Mock módban nem hívható. */
export function haviOsszesito(honap: string): Promise<HaviOsszesito> {
  return keres(`havi-osszesito?honap=${encodeURIComponent(honap)}`, { method: 'GET' });
}

/** `POST /api/v/kategoria-modositas`. Mock módban nincs teendő. */
export async function kategoriaModositas(body: KategoriaModositasKeres): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('kategoria-modositas', { method: 'POST', body });
}

/** `POST /api/v/keret-mentes`: egy kategória havi keretének létrehozása vagy módosítása. Mock módban nincs teendő. */
export async function keretMentes(body: {
  kategoria_id: string;
  nev: string;
  havi_keret: number;
  aktiv: boolean;
}): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('keret-mentes', { method: 'POST', body });
}

/** `POST /api/v/cel-mentes`: megtakarítási cél létrehozása (id nélkül) vagy módosítása. */
export async function celMentes(body: {
  id?: string;
  cel_neve: string;
  celosszeg: number;
  aktualis_osszeg: number;
}): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('cel-mentes', { method: 'POST', body });
}

/** `POST /api/v/cel-torles` */
export async function celTorles(id: string): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('cel-torles', { method: 'POST', body: { id } });
}

/** `POST /api/v/tranzakcio-felvetel`: kézi tétel rögzítése. Mock módban nincs teendő (a store rögzíti helyben). */
export async function ujTranzakcio(body: UjTranzakcioKeres): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('tranzakcio-felvetel', { method: 'POST', body });
}

/** `POST /api/v/elofizetes-mentes`: létrehozás (id nélkül) vagy módosítás. */
export async function elofizetesMentes(body: {
  id?: string;
  megnevezes: string;
  varhato_osszeg: number;
  esedekesseg_napja: number;
  kategoria_id: string;
}): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('elofizetes-mentes', { method: 'POST', body });
}

/** `POST /api/v/elofizetes-torles` */
export async function elofizetesTorles(id: string): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('elofizetes-torles', { method: 'POST', body: { id } });
}

/** `POST /api/v/tranzakcio-modositas`: név, összeg, dátum, megjegyzés, fizetési mód módosítása. */
export async function tranzakcioModositas(body: {
  id: string;
  kereskedo?: string;
  osszeg?: number;
  datum?: string;
  megjegyzes?: string;
  fizetesi_mod?: string;
}): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('tranzakcio-modositas', { method: 'POST', body });
}

/** `POST /api/v/tranzakcio-torles` */
export async function tranzakcioTorles(id: string): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('tranzakcio-torles', { method: 'POST', body: { id } });
}

/** `POST /api/v/szemely-mentes`: új személy (kulcs nélkül) vagy átnevezés / kikapcsolás. Visszaadja a kulcsot. */
export async function szemelyMentes(body: {
  kulcs?: string;
  nev: string;
  aktiv?: boolean;
}): Promise<string | null> {
  if (!ELO_API) return null;
  const valasz = await keres<{ kulcs?: string }>('szemely-mentes', { method: 'POST', body });
  return valasz.kulcs ?? null;
}

export interface BankKapcsolat {
  id: string;
  szemely: string;
  iban_vege: string;
  lejarat: string | null;
  napok_hatra: number | null;
  utolso_szinkron: string | null;
  lejart: boolean;
}

export interface BankSzinkronEredmeny {
  szemely: string;
  ok: boolean;
  hiba: string;
  uj: number;
  duplikalt: number;
  letoltott: number;
}

/** `GET /api/v/bank-allapot`: az összekötött bankszámlák és a hozzáférés lejárata. */
export async function bankAllapot(): Promise<BankKapcsolat[]> {
  if (!ELO_API) return [];
  const v = await keres<{ kapcsolatok: BankKapcsolat[] }>('bank-allapot', { method: 'GET' });
  return v.kapcsolatok;
}

/** `POST /api/v/bank-osszekotes`: a bank jóváhagyási hivatkozása (böngészőben kell megnyitni). */
export async function bankOsszekotes(szemely: string): Promise<string> {
  const v = await keres<{ url: string }>('bank-osszekotes', { method: 'POST', body: { szemely } });
  return v.url;
}

/** `POST /api/v/bank-szinkron`: az új banki tételek letöltése és importálása (kézi indítás). */
export async function bankSzinkron(): Promise<BankSzinkronEredmeny[]> {
  const v = await keres<{ kapcsolatok: BankSzinkronEredmeny[] }>('bank-szinkron', {
    method: 'POST',
    body: {},
    idotulMs: 180_000,
  });
  return v.kapcsolatok;
}
