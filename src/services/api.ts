import { N8N_APP_KEY, N8N_BASE_URL } from '../config';
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
} from '../types';

/** Ha nincs n8n URL beállítva (EXPO_PUBLIC_N8N_BASE_URL), az app mock adatokkal működik. */
export const ELO_API = N8N_BASE_URL !== '';

const IDOTUL_MS = 60_000;

async function keres<T>(utvonal: string, opciok: { method: 'GET' | 'POST'; body?: unknown }) {
  const vezerlo = new AbortController();
  const idozito = setTimeout(() => vezerlo.abort(), IDOTUL_MS);
  try {
    const res = await fetch(`${N8N_BASE_URL}/webhook/${utvonal}`, {
      method: opciok.method,
      headers: { 'Content-Type': 'application/json', 'X-App-Key': N8N_APP_KEY },
      body: opciok.body === undefined ? undefined : JSON.stringify(opciok.body),
      signal: vezerlo.signal,
    });
    if (!res.ok) {
      const hibaTest = await res.json().catch(() => null);
      throw new Error(hibaTest?.uzenet ?? `A szerver hibát jelzett (${res.status})`);
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

/** `POST /webhook/nyugta-feltoltes` */
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
 * `POST /webhook/banki-fajl-elemzes`: bármilyen banki kivonat (PDF / XLSX / CSV) elemzése a szerveren
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
 * `POST /webhook/banki-import`. Élő módban az n8n összegzését adja vissza, mock módban `null`
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

/** `GET /webhook/adatok`: kategóriák, keretek, előfizetések, célok, szabályok. */
export function alapadatok(): Promise<Alapadatok> {
  return keres('adatok', { method: 'GET' });
}

/** `GET /webhook/tranzakciok[?honap=YYYY-MM]` */
export function tranzakciokLekeres(honap?: string): Promise<{ tranzakciok: Tranzakcio[] }> {
  return keres(`tranzakciok${honap ? `?honap=${honap}` : ''}`, { method: 'GET' });
}

/** `GET /webhook/havi-osszesito?honap=YYYY-MM`. Mock módban nem hívható. */
export function haviOsszesito(honap: string): Promise<HaviOsszesito> {
  return keres(`havi-osszesito?honap=${encodeURIComponent(honap)}`, { method: 'GET' });
}

/** `POST /webhook/kategoria-modositas`. Mock módban nincs teendő. */
export async function kategoriaModositas(body: KategoriaModositasKeres): Promise<void> {
  if (!ELO_API) return;
  await keres<unknown>('kategoria-modositas', { method: 'POST', body });
}
