import { AI_ELEMZESEK } from '../mock/data';
import type {
  Elofizetes,
  HaviOsszesito,
  Kategoria,
  Koltsegkeret,
  Tranzakcio,
} from '../types';

interface Bemenet {
  honap: string;
  tranzakciok: Tranzakcio[];
  kategoriak: Kategoria[];
  keretek: Koltsegkeret[];
  elofizetesek: Elofizetes[];
}

/** A `GET /webhook/havi-osszesito` válaszát utánzó, kliensoldali számítás (mock réteg). */
export function szamolHaviOsszesito(b: Bemenet): HaviOsszesito {
  const havi = b.tranzakciok.filter((t) => t.datum.startsWith(b.honap));
  const kiadasok = havi.filter((t) => t.tipus === 'kiadas');
  const sum = (l: Tranzakcio[]) => l.reduce((s, t) => s + t.osszeg, 0);

  const osszes_bevetel = sum(havi.filter((t) => t.tipus !== 'kiadas'));
  const osszes_kiadas = sum(kiadasok);

  const keretek = b.keretek
    .filter((k) => k.aktiv)
    .map((k) => {
      const elkoltve = sum(kiadasok.filter((t) => t.kategoria_id === k.kategoria_id));
      return {
        kategoria: b.kategoriak.find((c) => c.id === k.kategoria_id)?.nev ?? '?',
        havi_keret: k.havi_keret,
        elkoltve,
        szazalek: Math.round((elkoltve / k.havi_keret) * 100),
      };
    });

  const elofizetesek = b.elofizetesek.map((e) => {
    const nev = e.megnevezes.split(' ')[0].toLowerCase();
    const kifizetve = kiadasok.some((t) => t.kereskedo.toLowerCase().includes(nev));
    return { ...e, kifizetve };
  });

  return {
    osszes_bevetel,
    osszes_kiadas,
    egyenleg: osszes_bevetel - osszes_kiadas,
    bontas_tulajdonos_szerint: {
      kozos: sum(kiadasok.filter((t) => t.tulajdonos === 'kozos')),
      ferj_sajat: sum(kiadasok.filter((t) => t.tulajdonos === 'ferj')),
      feleseg_sajat: sum(kiadasok.filter((t) => t.tulajdonos === 'feleseg')),
    },
    keretek,
    elofizetesek,
    varhato_hatralevo_elofizetesek: elofizetesek
      .filter((e) => !e.kifizetve)
      .reduce((s, e) => s + e.varhato_osszeg, 0),
    ai_elemzes: AI_ELEMZESEK[b.honap] ?? 'Ehhez a hónaphoz még nincs elemzés.',
  };
}
