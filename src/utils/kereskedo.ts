const GENERIKUS =
  /^(vásárlás kártyával|áruvisszavét ellenértéke|azonnali fizetés.*|napközbeni átutalás.*|tranzakció.*)$/i;

/**
 * Kereskedőnév-kulcs szabálynak: a hosszú banki leírásból az azonosítókat és a generikus részeket eldobja
 * (ugyanez a logika fut az n8n importban és az AI-tanulásban, tartsd összhangban).
 * 'VÁSÁRLÁS KÁRTYÁVAL, Pekaru Mintabolt -APPLE' -> 'pekaru mintabolt'
 */
export function kereskedoKulcs(szoveg: string): string | null {
  // átutalásból nem tanulunk szabályt: a leírásban a saját név szerepel
  if (/^(azonnali fizetés|napközbeni átutalás|átutalás|csoportos|beszedés)/i.test(szoveg.trim()))
    return null;
  for (const resz of szoveg.split(', ').map((x) => x.trim())) {
    if (!resz || GENERIKUS.test(resz) || /^[\d\W]+$/.test(resz)) continue;
    if (/\d+[,.]?\d*\s?EUR|\bEUR\b/i.test(resz)) continue;
    const kulcs = resz
      .replace(/\s+-apple\b.*$/i, '')
      .replace(/\s+\d{3,}.*$/, '')
      .replace(/\*+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
    if (kulcs.length >= 4) return kulcs;
  }
  return null;
}

/**
 * A hosszú banki leírásból olvasható megjelenített név (az eredeti adat változatlan marad):
 * kódokat, azonosítókat, BIC-et, devizafragmenseket és a "-APPLE" utótagot elhagyja.
 * 'VÁSÁRLÁS KÁRTYÁVAL, 6296…, Tranzakció: 26.09.01, Pekaru Mintabolt -APPLE' -> 'Pekaru Mintabolt'
 */
export function megjelenitettNev(szoveg: string): string {
  const tisztit = (r: string) =>
    r
      .replace(/\s+-apple\b.*$/i, '')
      .replace(/\*+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  const reszek = szoveg
    .split(', ')
    .map((r) => r.trim())
    .filter(
      (r) =>
        r &&
        !/^[\d\W]+$/.test(r) &&
        !/^F\.\d{4}$/.test(r) &&
        !/^[A-Z]{6}[A-Z0-9]{2,5}$/.test(r) &&
        !/^\(\d+\.\)/.test(r) &&
        !/^tranzakció:/i.test(r) &&
        !/\d+[,.]?\d*\s?(EUR|USD|GBP|CHF)\b/i.test(r),
    )
    .map(tisztit)
    .filter(Boolean);
  // kártyás vásárlásnál a "VÁSÁRLÁS KÁRTYÁVAL" felesleges, ha van mellette kereskedő
  const tartalmas = reszek.filter((r) => !/^vásárlás kártyával$/i.test(r));
  const kiir = (tartalmas.length ? tartalmas : reszek).slice(0, 3).join(', ');
  return kiir.replace(/\s+\d{4,}.*$/, '').slice(0, 80) || szoveg.slice(0, 80);
}

/** A leírásban szereplő devizaösszeg, pl. '10,960EUR' -> '10,96 EUR' (a tétel összege forintban van tárolva). */
export function devizaInfo(...szovegek: (string | undefined)[]): string | null {
  const m = szovegek.join(' ').match(/(\d+)[,.](\d+)\s?(EUR|USD|GBP|CHF)\b/i);
  if (!m) return null;
  const ertek = Number(`${m[1]}.${m[2]}`);
  return Number.isFinite(ertek)
    ? `${ertek.toFixed(2).replace('.', ',')} ${m[3].toUpperCase()}`
    : null;
}

/**
 * Azonnali fizetési rendszeren (AFR) feldolgozott tétel? A bank tranzakciótípusa a névben vagy a megjegyzés elején áll
 * ('AZONNALI FIZETÉS BANKON BELÜL', 'QVIK FIZETÉS BANKON BELÜL'). Ezeknél kötelező a qvik logó megjelenítése.
 * A 'NAPKÖZBENI ÁTUTALÁS' nem azonnali fizetés.
 */
export function azonnaliTetel(t: { kereskedo: string; megjegyzes?: string }): boolean {
  const azonnali = /^\s*(azonnali fizetés|qvik fizetés)/i;
  return azonnali.test(t.kereskedo) || azonnali.test(t.megjegyzes ?? '');
}
