import { create } from 'zustand';

import {
  CELOK,
  ELOFIZETESEK,
  KATEGORIAK,
  KOLTSEGKERETEK,
  SZABALYOK,
  TRANZAKCIOK,
} from '../mock/data';
import {
  alapadatok,
  celMentes,
  celTorles,
  ELO_API,
  elofizetesMentes,
  elofizetesTorles,
  HibasKulcs,
  keretMentes,
  tranzakciokLekeres,
} from '../services/api';
import { szerepMent, type Szerep } from '../services/kulcs';
import { alkalmazImport } from '../services/mockImport';
import type {
  BankiImportKeres,
  Elofizetes,
  ImportOsszegzes,
  Kategoria,
  Koltsegkeret,
  MegtakaritasiCel,
  Szabaly,
  Tranzakcio,
  Tulajdonos,
} from '../types';
import { aktualisHonap, leptetHonap } from '../utils/format';
import { kereskedoKulcs } from '../utils/kereskedo';

let elsoBetoltes = true;

export type TulajdonosSzuro = 'mind' | Tulajdonos;

interface State {
  honap: string; // YYYY-MM
  szuro: TulajdonosSzuro;
  kategoriak: Kategoria[];
  tranzakciok: Tranzakcio[];
  keretek: Koltsegkeret[];
  elofizetesek: Elofizetes[];
  celok: MegtakaritasiCel[];
  szabalyok: Szabaly[];
  /** Élő módban: töltés állapota és az utolsó hiba. */
  toltes: boolean;
  hiba: string | null;
  /** Az n8n elutasította a kulcsot (vagy nincs): az app bekéri. */
  kulcsSzukseges: boolean;
  setKulcsSzukseges: (ertek: boolean) => void;
  /** Élő módban a szerverről (n8n) tölti be az adatokat; mock módban nem csinál semmit. */
  betoltes: () => Promise<void>;
  /** Keret létrehozása/módosítása egy kategóriára (élő módban a szerverre is ment, majd újratölt). */
  mentKeret: (kategoriaId: string, nev: string, haviKeret: number, aktiv: boolean) => Promise<void>;
  /** Cél létrehozása (id nélkül) vagy módosítása. */
  mentCel: (cel: Omit<MegtakaritasiCel, 'id'> & { id?: string }) => Promise<void>;
  torolCel: (id: string) => Promise<void>;
  /** Ki használja ezt a telefont; az importoknál ez az alapértelmezett feltöltő. */
  szerep: Szerep | null;
  szerepSzukseges: boolean;
  setSzerep: (szerep: Szerep) => Promise<void>;
  setSzerepSzukseges: (ertek: boolean) => void;
  mentElofizetes: (e: Omit<Elofizetes, 'id'> & { id?: string }) => Promise<void>;
  torolElofizetes: (id: string) => Promise<void>;
  /** Helyi állapotból törli a tételt (a szerveroldali törlés külön hívás). */
  torolTranzakcioLokal: (id: string) => void;
  setHonap: (honap: string) => void;
  leptetHonap: (delta: number) => void;
  setSzuro: (szuro: TulajdonosSzuro) => void;
  /** Mock mód: a banki import n8n-logikájának helyi alkalmazása. */
  mockBankiImport: (keres: BankiImportKeres) => ImportOsszegzes;
  hozzaadTranzakcio: (t: Omit<Tranzakcio, 'id'>) => string;
  modositTranzakcio: (id: string, valtozas: Partial<Tranzakcio>) => void;
  /** Kategóriát átállít, és a kereskedőre új szabályt generál (mock a `kategoria-modositas` végpontra). */
  modositKategoria: (id: string, ujKategoriaId: string) => void;
}

export const useStore = create<State>((set, get) => ({
  honap: aktualisHonap(),
  szuro: 'mind',
  // élő módban üresen indul és a szerverről töltődik, mock módban a minta adatokkal
  kategoriak: ELO_API ? [] : KATEGORIAK,
  tranzakciok: ELO_API ? [] : TRANZAKCIOK,
  keretek: ELO_API ? [] : KOLTSEGKERETEK,
  elofizetesek: ELO_API ? [] : ELOFIZETESEK,
  celok: ELO_API ? [] : CELOK,
  szabalyok: ELO_API ? [] : SZABALYOK,
  toltes: false,
  hiba: null,
  kulcsSzukseges: false,
  setKulcsSzukseges: (kulcsSzukseges) => set({ kulcsSzukseges }),
  betoltes: async () => {
    if (!ELO_API) return;
    set({ toltes: true, hiba: null });
    try {
      const [alap, tr] = await Promise.all([alapadatok(), tranzakciokLekeres()]);
      set({ ...alap, tranzakciok: tr.tranzakciok, toltes: false });
      if (elsoBetoltes) {
        // induláskor az utolsó olyan hónapra ugrik, amelyben van tétel (ha az aktuális üres)
        elsoBetoltes = false;
        const { honap, tranzakciok } = get();
        if (tranzakciok.length && !tranzakciok.some((t) => t.datum.startsWith(honap))) {
          const utolso = tranzakciok.reduce((m, t) => (t.datum > m ? t.datum : m), '');
          set({ honap: utolso.slice(0, 7) });
        }
      }
    } catch (e) {
      if (e instanceof HibasKulcs) {
        set({ toltes: false, kulcsSzukseges: true });
        return;
      }
      set({
        toltes: false,
        hiba: e instanceof Error ? e.message : 'Az adatok betöltése nem sikerült',
      });
    }
  },
  mentKeret: async (kategoriaId, nev, haviKeret, aktiv) => {
    if (ELO_API) {
      await keretMentes({ kategoria_id: kategoriaId, nev, havi_keret: haviKeret, aktiv });
      await get().betoltes();
      return;
    }
    set((s) => {
      const van = s.keretek.some((k) => k.kategoria_id === kategoriaId);
      return {
        keretek: van
          ? s.keretek.map((k) =>
              k.kategoria_id === kategoriaId ? { ...k, havi_keret: haviKeret, aktiv } : k,
            )
          : [
              ...s.keretek,
              {
                id: `keret_${kategoriaId}`,
                kategoria_id: kategoriaId,
                havi_keret: haviKeret,
                aktiv,
              },
            ],
      };
    });
  },
  mentCel: async (cel) => {
    if (ELO_API) {
      await celMentes({
        id: cel.id,
        cel_neve: cel.cel_neve,
        celosszeg: cel.celosszeg,
        aktualis_osszeg: cel.aktualis_osszeg,
      });
      await get().betoltes();
      return;
    }
    set((s) => ({
      celok: cel.id
        ? s.celok.map((c) => (c.id === cel.id ? { ...c, ...cel, id: c.id } : c))
        : [...s.celok, { ...cel, id: `cel${Date.now()}` }],
    }));
  },
  torolCel: async (id) => {
    if (ELO_API) {
      await celTorles(id);
      await get().betoltes();
      return;
    }
    set((s) => ({ celok: s.celok.filter((c) => c.id !== id) }));
  },
  szerep: null,
  szerepSzukseges: false,
  setSzerep: async (szerep) => {
    set({ szerep, szerepSzukseges: false });
    try {
      await szerepMent(szerep);
    } catch {
      // a tároló nem érhető el: a beállítás csak az aktuális munkamenetre él
    }
  },
  setSzerepSzukseges: (szerepSzukseges) => set({ szerepSzukseges }),
  mentElofizetes: async (e) => {
    if (ELO_API) {
      await elofizetesMentes({
        id: e.id,
        megnevezes: e.megnevezes,
        varhato_osszeg: e.varhato_osszeg,
        esedekesseg_napja: e.esedekesseg_napja,
        kategoria_id: e.kategoria_id,
      });
      await get().betoltes();
      return;
    }
    set((s) => ({
      elofizetesek: e.id
        ? s.elofizetesek.map((x) => (x.id === e.id ? { ...x, ...e, id: x.id } : x))
        : [...s.elofizetesek, { ...e, id: `ef${Date.now()}` }],
    }));
  },
  torolElofizetes: async (id) => {
    if (ELO_API) {
      await elofizetesTorles(id);
      await get().betoltes();
      return;
    }
    set((s) => ({ elofizetesek: s.elofizetesek.filter((x) => x.id !== id) }));
  },
  torolTranzakcioLokal: (id) =>
    set((s) => ({ tranzakciok: s.tranzakciok.filter((t) => t.id !== id) })),
  setHonap: (honap) => set({ honap }),
  leptetHonap: (delta) => set((s) => ({ honap: leptetHonap(s.honap, delta) })),
  setSzuro: (szuro) => set({ szuro }),
  mockBankiImport: (keres) => {
    const { tranzakciok, osszegzes } = alkalmazImport(get().tranzakciok, get().szabalyok, keres);
    set({ tranzakciok });
    return osszegzes;
  },
  hozzaadTranzakcio: (t) => {
    const id = `rec${Date.now()}`;
    set((s) => ({ tranzakciok: [...s.tranzakciok, { ...t, id }] }));
    return id;
  },
  modositTranzakcio: (id, valtozas) =>
    set((s) => ({
      tranzakciok: s.tranzakciok.map((t) => (t.id === id ? { ...t, ...valtozas } : t)),
    })),
  modositKategoria: (id, ujKategoriaId) =>
    set((s) => {
      const t = s.tranzakciok.find((x) => x.id === id);
      if (!t) return s;
      const minta = kereskedoKulcs(t.kereskedo) ?? t.kereskedo.toLowerCase().slice(0, 60);
      return {
        tranzakciok: s.tranzakciok.map((x) =>
          x.id === id ? { ...x, kategoria_id: ujKategoriaId } : x,
        ),
        szabalyok: [
          ...s.szabalyok.filter((r) => r.minta !== minta),
          { id: `szabaly_${minta}`, minta, kategoria_id: ujKategoriaId },
        ],
      };
    }),
}));
