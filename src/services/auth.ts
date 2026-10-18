import { API_ALAP_URL } from '../config';
import * as Tarolo from './tarolo';

const FRISSITO = 'vespendo.frissito_token';
/** A lejárat előtt ennyivel már megújítjuk a hozzáférési tokent. */
const ELOZETES_MS = 30_000;

export interface Tag {
  id: number;
  nev: string;
  szerep: 'admin' | 'tag';
  szemely_kulcs: string | null;
  /** Csak adminnak. */
  email: string | null;
}

export interface Profil {
  felhasznalo: { id: number; nev: string; email: string; demo?: boolean };
  haztartas: {
    id: string;
    nev: string;
    szerep: 'admin' | 'tag';
    szemely_kulcs: string | null;
    bank_engedelyezett: boolean;
    /** Csak adminnak. */
    meghivokod: string | null;
  };
  tagok: Tag[];
}

export interface ApiToken {
  id: number;
  nev: string;
  letrehozva: string;
  utolso: string | null;
}

/** A belépés érvénytelen vagy lejárt: újra be kell lépni. */
export class NincsBelepes extends Error {
  constructor(uzenet = 'Lépj be újra.') {
    super(uzenet);
    this.name = 'NincsBelepes';
  }
}

let hozzaferes: { token: string; lejar: number } | null = null;
let ujitas: Promise<string> | null = null;
let kilepesFigyelo: (() => void) | null = null;

/** A store ezen keresztül értesül, ha a munkamenet véglegesen érvénytelen. */
export const onKilepett = (f: () => void) => {
  kilepesFigyelo = f;
};

async function nyers<T>(
  metodus: 'GET' | 'POST' | 'DELETE',
  ut: string,
  body?: unknown,
  token?: string,
): Promise<{ status: number; adat: T & { hiba?: string } }> {
  const res = await fetch(`${API_ALAP_URL}${ut}`, {
    method: metodus,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const adat = (await res.json().catch(() => ({}))) as T & { hiba?: string };
  return { status: res.status, adat };
}

interface TokenValasz {
  access_token: string;
  frissito_token: string;
  lejarat_mp: number;
  en: Profil;
}

async function mentTokenek(v: TokenValasz | Omit<TokenValasz, 'en'>) {
  hozzaferes = { token: v.access_token, lejar: Date.now() + v.lejarat_mp * 1000 };
  await Tarolo.setItemAsync(FRISSITO, v.frissito_token);
}

/** Több fül (PWA) ne forgassa egyszerre ugyanazt a frissítő tokent: a böngésző zárjával sorba állítjuk. */
async function zarral<T>(f: () => Promise<T>): Promise<T> {
  const zarak = (globalThis as { navigator?: { locks?: { request: <R>(n: string, f: () => Promise<R>) => Promise<R> } } })
    .navigator?.locks;
  return zarak?.request ? zarak.request('vespendo-frissites', f) : f();
}

function munkamenetUjitas(): Promise<string> {
  ujitas ??= zarral(async () => {
    const tarolt = await Tarolo.getItemAsync(FRISSITO);
    if (!tarolt) throw new NincsBelepes();
    const { status, adat } = await nyers<TokenValasz>('POST', '/api/auth/frissites', { frissito_token: tarolt });
    if (status === 401) {
      hozzaferes = null;
      await Tarolo.deleteItemAsync(FRISSITO).catch(() => {});
      kilepesFigyelo?.();
      throw new NincsBelepes();
    }
    if (status !== 200) throw new Error(adat.hiba ?? `A szerver hibát jelzett (${status})`);
    await mentTokenek(adat);
    return adat.access_token;
  }).finally(() => {
    ujitas = null;
  });
  return ujitas;
}

/** Érvényes hozzáférési token; szükség esetén megújítja. */
export async function hozzaferesToken(): Promise<string> {
  if (hozzaferes && hozzaferes.lejar - Date.now() > ELOZETES_MS) return hozzaferes.token;
  return munkamenetUjitas();
}

/** Hitelesített hívás: 401-nél egyszer megújít és újrapróbál. A válasz nyers `Response`. */
export async function hitelesitettFetch(ut: string, init: RequestInit): Promise<Response> {
  const hivas = async (t: string) =>
    fetch(`${API_ALAP_URL}${ut}`, { ...init, headers: { ...(init.headers as Record<string, string>), Authorization: `Bearer ${t}` } });
  let res = await hivas(await hozzaferesToken());
  if (res.status === 401) {
    hozzaferes = null;
    res = await hivas(await munkamenetUjitas());
    if (res.status === 401) {
      kilepesFigyelo?.();
      throw new NincsBelepes();
    }
  }
  return res;
}

async function hitelesitett<T>(metodus: 'GET' | 'POST' | 'DELETE', ut: string, body?: unknown): Promise<T> {
  const res = await hitelesitettFetch(ut, {
    method: metodus,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const adat = (await res.json().catch(() => ({}))) as T & { hiba?: string };
  if (!res.ok) throw new Error(adat.hiba ?? `A szerver hibát jelzett (${res.status})`);
  return adat;
}

async function belepesValasz(status: number, adat: TokenValasz & { hiba?: string }): Promise<Profil> {
  if (status !== 200) throw new Error(adat.hiba ?? `A szerver hibát jelzett (${status})`);
  await mentTokenek(adat);
  return adat.en;
}

export async function belepes(email: string, jelszo: string): Promise<Profil> {
  const { status, adat } = await nyers<TokenValasz>('POST', '/api/auth/belepes', { email, jelszo });
  return belepesValasz(status, adat);
}

/** Jelszó nélküli belépés a bemutató (demó) háztartásba; csak ha a szerver be van állítva rá. */
export async function demoBelepes(): Promise<Profil> {
  const { status, adat } = await nyers<TokenValasz>('POST', '/api/auth/demo');
  return belepesValasz(status, adat);
}

export interface RegisztraciosAdat {
  email: string;
  jelszo: string;
  nev: string;
  /** Meglévő háztartáshoz csatlakozáshoz. */
  meghivokod?: string;
  /** Új háztartás létrehozásához. */
  regisztracios_kod?: string;
  haztartas_nev?: string;
}

export async function regisztracio(adatok: RegisztraciosAdat): Promise<Profil> {
  const { status, adat } = await nyers<TokenValasz>('POST', '/api/auth/regisztracio', adatok);
  return belepesValasz(status, adat);
}

/** Van-e eltárolt munkamenet (az induláskor ezzel döntjük el, hogy belépőképernyő kell-e). */
export async function vanMunkamenet(): Promise<boolean> {
  return !!(await Tarolo.getItemAsync(FRISSITO).catch(() => null));
}

export async function kilepes(): Promise<void> {
  const tarolt = await Tarolo.getItemAsync(FRISSITO).catch(() => null);
  hozzaferes = null;
  await Tarolo.deleteItemAsync(FRISSITO).catch(() => {});
  if (tarolt) await nyers('POST', '/api/auth/kilepes', { frissito_token: tarolt }).catch(() => {});
}

export const profil = () => hitelesitett<Profil>('GET', '/api/auth/en');
export const szemelyKapcsolas = (kulcs: string) => hitelesitett<Profil>('POST', '/api/auth/szemely', { kulcs });
export const jelszoCsere = (regi: string, uj: string) =>
  hitelesitett<{ ok: boolean }>('POST', '/api/auth/jelszo', { regi, uj });
export const ujMeghivokod = async () =>
  (await hitelesitett<{ meghivokod: string }>('POST', '/api/auth/meghivokod')).meghivokod;
export const tagJelszoVisszaallitas = async (id: number) =>
  (await hitelesitett<{ ideiglenes_jelszo: string }>('POST', `/api/auth/tagok/${id}/jelszo-visszaallitas`)).ideiglenes_jelszo;
export const tagEltavolit = (id: number) => hitelesitett<{ ok: boolean }>('DELETE', `/api/auth/tagok/${id}`);
export const apiTokenek = () => hitelesitett<ApiToken[]>('GET', '/api/auth/api-tokenek');
export const apiTokenLetrehoz = (nev: string) =>
  hitelesitett<{ id: number; nev: string; token: string }>('POST', '/api/auth/api-tokenek', { nev });
export const apiTokenTorol = (id: number) => hitelesitett<{ ok: boolean }>('DELETE', `/api/auth/api-tokenek/${id}`);
