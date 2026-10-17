import type { Szemely } from '../types';

/** A személy megjelenített neve a kulcs alapján (ismeretlen kulcsnál maga a kulcs). */
export function szemelyNev(szemelyek: Szemely[], kulcs: string): string {
  return szemelyek.find((s) => s.kulcs === kulcs)?.nev ?? kulcs;
}
