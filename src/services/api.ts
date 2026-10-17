import { N8N_BASE_URL } from '../config';
import type {
  BankiImportKeres,
  HaviOsszesito,
  KategoriaModositasKeres,
  NyugtaKeres,
  NyugtaValasz,
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
      headers: { 'Content-Type': 'application/json' },
      body: opciok.body === undefined ? undefined : JSON.stringify(opciok.body),
      signal: vezerlo.signal,
    });
    if (!res.ok) throw new Error(`A szerver hibát jelzett (${res.status})`);
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

/** `POST /webhook/banki-import` (a spec nem ír le válasz-szerkezetet, bármely 2xx siker). */
export async function bankiImport(body: BankiImportKeres): Promise<void> {
  if (ELO_API) {
    await keres<unknown>('banki-import', { method: 'POST', body });
    return;
  }
  await kesleltet(1500);
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
