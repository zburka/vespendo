import { N8N_BASE_URL } from '../config';
import type { NyugtaKeres, NyugtaValasz } from '../types';

/** `POST /webhook/nyugta-feltoltes`. Amíg nincs n8n URL beállítva, mock választ ad (5. fázisban bekötjük). */
export async function feltoltNyugta(keres: NyugtaKeres): Promise<NyugtaValasz> {
  if (N8N_BASE_URL) {
    const res = await fetch(`${N8N_BASE_URL}/webhook/nyugta-feltoltes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(keres),
    });
    if (!res.ok) throw new Error(`Feltöltési hiba (${res.status})`);
    return res.json();
  }

  await new Promise((r) => setTimeout(r, 2500));
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
