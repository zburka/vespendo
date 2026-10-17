import Papa from 'papaparse';

import type { BankiTranzakcio } from '../types';

export interface CsvEredmeny {
  tranzakciok: BankiTranzakcio[];
  kihagyott: number;
}

const normal = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

/** Fájl bájtjaiból szöveg: UTF-8, ennek hibája esetén Windows-1250 (az OTP exportok gyakori kódolása). */
export function dekodol(bajtok: Uint8Array): string {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bajtok);
  } catch {
    let s = '';
    for (const b of bajtok) s += String.fromCharCode(b);
    return s.replace(/õ/g, 'ő').replace(/û/g, 'ű').replace(/Õ/g, 'Ő').replace(/Û/g, 'Ű');
  }
}

function parseOsszeg(nyers: string): number | null {
  let s = nyers.replace(/[\s ]/g, '');
  if (!s) return null;
  if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.');
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/** '2026.10.16.' | '2026-10-16' | '2026. 10. 16' -> '2026-10-16' */
function parseDatum(nyers: string): string | null {
  const m = nyers.match(/(\d{4})\D+(\d{1,2})\D+(\d{1,2})/);
  return m ? `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}` : null;
}

function oszlop(fejlecek: string[], kulcsszavak: string[]): string | undefined {
  for (const kulcs of kulcsszavak) {
    const talalt = fejlecek.find((f) => normal(f).includes(kulcs));
    if (talalt) return talalt;
  }
  return undefined;
}

/**
 * Banki kivonat CSV feldolgozása a telefonon. Az oszlopokat a fejléc szavai alapján azonosítja
 * (dátum, összeg, partner, közlemény), az irányt az összeg előjele adja (negatív = kiadás).
 */
export function parseBankiCsv(szoveg: string): CsvEredmeny {
  const { data, meta } = Papa.parse<Record<string, string>>(szoveg.replace(/^﻿/, ''), {
    header: true,
    skipEmptyLines: 'greedy',
  });
  const fejlecek = meta.fields ?? [];

  const datumOszlop = oszlop(fejlecek, ['konyvel', 'datum', 'teljesites']);
  const osszegOszlop = oszlop(fejlecek, ['osszeg']);
  const partnerOszlop = oszlop(fejlecek, ['partner', 'kedvezmenyezett', 'elszamolasi', 'nev']);
  const kozlemenyOszlop = oszlop(fejlecek, ['kozlemeny', 'megjegyzes', 'tranzakcio tipus']);

  if (!datumOszlop || !osszegOszlop) {
    throw new Error(
      `Nem található dátum/összeg oszlop a fájlban. Talált oszlopok: ${fejlecek.join(', ') || '—'}`,
    );
  }

  const tranzakciok: BankiTranzakcio[] = [];
  let kihagyott = 0;
  for (const sor of data) {
    const datum = parseDatum(sor[datumOszlop] ?? '');
    const osszeg = parseOsszeg(sor[osszegOszlop] ?? '');
    if (!datum || osszeg === null || osszeg === 0) {
      kihagyott++;
      continue;
    }
    const kozlemeny = (kozlemenyOszlop && sor[kozlemenyOszlop]?.trim()) || '';
    tranzakciok.push({
      datum,
      osszeg: Math.abs(osszeg),
      kereskedo_nyers: ((partnerOszlop && sor[partnerOszlop]?.trim()) || kozlemeny).trim(),
      kozlemeny,
      irany: osszeg < 0 ? 'kiadas' : 'bevetel',
    });
  }
  return { tranzakciok, kihagyott };
}
