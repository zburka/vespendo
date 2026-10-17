import { create } from 'zustand';

import {
  CELOK,
  ELOFIZETESEK,
  KATEGORIAK,
  KOLTSEGKERETEK,
  SZABALYOK,
  TRANZAKCIOK,
} from '../mock/data';
import { alapadatok, ELO_API, tranzakciokLekeres } from '../services/api';
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
  /** Élő módban a szerverről (n8n) tölti be az adatokat; mock módban nem csinál semmit. */
  betoltes: () => Promise<void>;
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
  betoltes: async () => {
    if (!ELO_API) return;
    set({ toltes: true, hiba: null });
    try {
      const [alap, tr] = await Promise.all([alapadatok(), tranzakciokLekeres()]);
      set({ ...alap, tranzakciok: tr.tranzakciok, toltes: false });
    } catch (e) {
      set({
        toltes: false,
        hiba: e instanceof Error ? e.message : 'Az adatok betöltése nem sikerült',
      });
    }
  },
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
      const minta = t.kereskedo.toLowerCase();
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
