const GENERIKUS =
  /^(vásárlás kártyával|áruvisszavét ellenértéke|azonnali fizetés.*|napközbeni átutalás.*|tranzakció.*)$/i;

/**
 * Kereskedőnév-kulcs szabálynak: a hosszú banki leírásból az azonosítókat és a generikus részeket eldobja
 * (ugyanez a logika fut az n8n importban és az AI-tanulásban, tartsd összhangban).
 * 'VÁSÁRLÁS KÁRTYÁVAL, Pekaru Mintabolt -APPLE' -> 'pekaru mintabolt'
 */
export function kereskedoKulcs(szoveg: string): string | null {
  for (const resz of szoveg.split(', ').map((x) => x.trim())) {
    if (!resz || GENERIKUS.test(resz) || /^[\d\W]+$/.test(resz)) continue;
    if (/\d+[,.]?\d*\s?EUR|\bEUR\b/i.test(resz)) continue;
    const kulcs = resz
      .replace(/\s*-?apple\b.*$/i, '')
      .replace(/\s+\d{3,}.*$/, '')
      .replace(/\*+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
    if (kulcs.length >= 4) return kulcs;
  }
  return null;
}
