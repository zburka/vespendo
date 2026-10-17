import type { BankiImportKeres, ImportOsszegzes, Szabaly, Tranzakcio } from '../types';

const NAP_MS = 24 * 60 * 60 * 1000;

function napokKulonbseg(tol: string, ig: string): number {
  return Math.round((Date.parse(ig) - Date.parse(tol)) / NAP_MS);
}

/**
 * Az n8n `banki-import` belső logikájának helyi mása (mock mód):
 * 1. szabálymotor illesztés, 2. nyugtával való párosítás (azonos összeg, 0–3 nap), 3. ismeretlen -> Egyéb.
 */
export function alkalmazImport(
  meglevo: Tranzakcio[],
  szabalyok: Szabaly[],
  keres: BankiImportKeres,
): { tranzakciok: Tranzakcio[]; osszegzes: ImportOsszegzes } {
  const lista = [...meglevo];
  const osszegzes: ImportOsszegzes = { uj: 0, egyeztetve: 0, szaballyal: 0, ismeretlen: 0 };
  const stamp = Date.now();

  keres.tranzakciok.forEach((b, i) => {
    const nyugtaIndex = lista.findIndex(
      (t) =>
        t.allapot === 'banki_egyeztetesre_var' &&
        t.osszeg === b.osszeg &&
        napokKulonbseg(t.datum, b.datum) >= 0 &&
        napokKulonbseg(t.datum, b.datum) <= 3,
    );
    if (b.irany === 'kiadas' && nyugtaIndex >= 0) {
      lista[nyugtaIndex] = { ...lista[nyugtaIndex], allapot: 'lezart' };
      osszegzes.egyeztetve++;
      return;
    }

    const nyers = b.kereskedo_nyers.toLowerCase();
    const szabaly = szabalyok.find((r) => nyers.includes(r.minta));
    const bevetel = b.irany === 'bevetel';
    if (szabaly) osszegzes.szaballyal++;
    else if (!bevetel) osszegzes.ismeretlen++;

    lista.push({
      id: `rec${stamp}_${i}`,
      datum: b.datum,
      osszeg: b.osszeg,
      kereskedo: b.kereskedo_nyers || b.kozlemeny || 'Ismeretlen',
      kategoria_id: szabaly?.kategoria_id ?? (bevetel ? 'kat_fizetes' : 'kat_egyeb'),
      tipus: bevetel ? 'bevetel_egyszeri' : 'kiadas',
      tulajdonos: szabaly?.alapertelmezett_tulajdonos ?? keres.feltolto,
      fizetesi_mod: 'kartya',
      forras: 'bank_import',
      allapot: 'lezart',
      megjegyzes: b.kozlemeny || undefined,
    });
    osszegzes.uj++;
  });

  return { tranzakciok: lista, osszegzes };
}
