import type { Elofizetes, Kategoria, Tranzakcio } from '../types';
import { kereskedoKulcs, megjelenitettNev } from './kereskedo';

export interface ElofizetesJavaslat {
  /** Egyedi azonosító az elvetéshez (kereskedő + összeg). */
  kulcs: string;
  nev: string;
  osszeg: number;
  nap: number;
  kategoria_id: string;
  honapok: number;
  utolso: string;
}

const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

const median = (l: number[]) => {
  const s = [...l].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

const NAP_MS = 864e5;
const MIN_OSSZEG = 1000; // az apró banki díjak nem előfizetések
const ALTALANOS =
  /^(vasarlas kartyaval|azonnali fizetes|napkozbeni atutalas|qvik fizetes|aruvisszavet)/;
const honapIndex = (datum: string) => Number(datum.slice(0, 4)) * 12 + Number(datum.slice(5, 7));

/**
 * Fix előfizetés-javaslatok a tranzakciókból: ugyanattól a kereskedőtől (és nagyjából ugyanolyan összeggel)
 * legalább 3 különböző hónapban, havonta legfeljebb egyszer, nagyjából ugyanazon a napon érkező kiadás,
 * ami még aktív (az utolsó az elmúlt ~2 hónapban volt). A gyakori vásárlások (bolt) így kiesnek.
 */
export function elofizetesJavaslatok(
  tranzakciok: Tranzakcio[],
  kategoriak: Kategoria[],
  meglevo: Elofizetes[],
  elutasitott: string[],
  ma: Date = new Date(),
): ElofizetesJavaslat[] {
  const atvezetes = new Set(kategoriak.filter((k) => k.tipus === 'atvezetes').map((k) => k.id));
  const csoportok = new Map<string, Tranzakcio[]>();
  for (const t of tranzakciok) {
    if (t.tipus !== 'kiadas' || atvezetes.has(t.kategoria_id)) continue;
    const kulcs = kereskedoKulcs(t.kereskedo) ?? megjelenitettNev(t.kereskedo);
    const k = norm(kulcs);
    if (k.length < 3 || ALTALANOS.test(k)) continue;
    csoportok.set(k, [...(csoportok.get(k) ?? []), t]);
  }

  // Névegyezés a már felvett előfizetésekkel: a szavak előtagját (5 betű) hasonlítjuk, mert a bank csonkolhatja a nevet
  // ('SIMPLEP one' / 'SimplePay one'); ha mindkét névben van második szó, annak is egyeznie kell
  // (a 'SIMPLEP*one' és a 'SIMPLEP*szamlazz' két különböző tétel).
  const szavak = (nev: string) =>
    norm(nev)
      .split(/[^a-z0-9]+/)
      .filter((x) => x.length >= 3);
  const elotag = (x: string, y: string) =>
    x.startsWith(y.slice(0, 5)) || y.startsWith(x.slice(0, 5));
  const meglevoSzavak = meglevo.map((e) => szavak(e.megnevezes)).filter((w) => w.length > 0);
  const ugyanaz = (nev: string) => {
    const w = szavak(nev);
    return meglevoSzavak.some(
      (m) => w.length > 0 && elotag(w[0], m[0]) && (!w[1] || !m[1] || elotag(w[1], m[1])),
    );
  };
  const javaslatok: ElofizetesJavaslat[] = [];

  for (const [kulcs, lista] of csoportok) {
    // összegek szerinti sávok (pl. ugyanattól a kereskedőtől több, eltérő összegű havi díj)
    const datumokMind = lista.map((t) => t.datum).sort();
    // a kereskedő működési ideje hónapokban: egy összegsávnak ennek nagy részében jelen kell lennie
    const idoszak =
      honapIndex(datumokMind[datumokMind.length - 1]) - honapIndex(datumokMind[0]) + 1;
    const rendezett = [...lista].sort((a, b) => a.osszeg - b.osszeg);
    const savok: Tranzakcio[][] = [];
    for (const t of rendezett) {
      const sav = savok[savok.length - 1];
      if (sav && t.osszeg <= median(sav.map((x) => x.osszeg)) * 1.08) sav.push(t);
      else savok.push([t]);
    }

    for (const sav of savok) {
      const honapok = new Set(sav.map((t) => t.datum.slice(0, 7)));
      if (honapok.size < 3 || honapok.size / idoszak < 0.6) continue;
      if (sav.length / honapok.size > 1.35) continue; // gyakori vásárlás, nem havi díj
      const datumok = sav.map((t) => t.datum).sort();
      const utolso = datumok[datumok.length - 1];
      if ((ma.getTime() - Date.parse(utolso)) / NAP_MS > 70) continue; // már nem aktív
      const napok = sav.map((t) => Number(t.datum.slice(8, 10)));
      const kozepnap = median(napok);
      if (napok.filter((n) => Math.abs(n - kozepnap) <= 5).length / napok.length < 0.7) continue;

      const osszeg = Math.round(median(sav.map((t) => t.osszeg)));
      if (osszeg < MIN_OSSZEG) continue;
      const elutKulcs = `${kulcs}|${osszeg}`;
      if (elutasitott.includes(elutKulcs)) continue;
      const legujabb = sav.reduce((a, b) => (a.datum >= b.datum ? a : b));
      const nev = megjelenitettNev(legujabb.kereskedo);
      if (ugyanaz(nev)) continue;
      // leggyakoribb kategória
      const katok = new Map<string, number>();
      for (const t of sav) katok.set(t.kategoria_id, (katok.get(t.kategoria_id) ?? 0) + 1);
      const kategoria = [...katok].sort((a, b) => b[1] - a[1])[0][0];
      javaslatok.push({
        kulcs: elutKulcs,
        nev: savok.length > 1 ? `${nev} (${osszeg.toLocaleString('hu-HU')} Ft)` : nev,
        osszeg,
        nap: Math.round(kozepnap),
        kategoria_id: kategoria,
        honapok: honapok.size,
        utolso,
      });
    }
  }
  return javaslatok.sort((a, b) => b.honapok - a.honapok || b.osszeg - a.osszeg);
}
