import type { Tranzakcio } from '../types';

/** Ékezet- és kisbetű-független alak a kereséshez. */
export const egyszerusit = (s: string) =>
  s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

/** A keresőszavak (szóközzel elválasztva): mindegyiknek szerepelnie kell a tétel nevében vagy megjegyzésében, sorrendtől függetlenül. */
export function keresoSzavak(kerdes: string): string[] {
  return egyszerusit(kerdes).split(/\s+/).filter(Boolean);
}

export function egyezik(t: Tranzakcio, szavak: string[]): boolean {
  if (szavak.length === 0) return true;
  const szoveg = egyszerusit(`${t.kereskedo} ${t.megjegyzes ?? ''}`);
  return szavak.every((sz) => szoveg.includes(sz));
}
