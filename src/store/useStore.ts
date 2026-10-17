import { create } from 'zustand';

import {
  CELOK,
  ELOFIZETESEK,
  KATEGORIAK,
  KOLTSEGKERETEK,
  TRANZAKCIOK,
} from '../mock/data';
import type {
  Elofizetes,
  Kategoria,
  Koltsegkeret,
  MegtakaritasiCel,
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
  setHonap: (honap: string) => void;
  leptetHonap: (delta: number) => void;
  setSzuro: (szuro: TulajdonosSzuro) => void;
  modositTranzakcio: (id: string, valtozas: Partial<Tranzakcio>) => void;
}

export const useStore = create<State>((set) => ({
  honap: aktualisHonap(),
  szuro: 'mind',
  kategoriak: KATEGORIAK,
  tranzakciok: TRANZAKCIOK,
  keretek: KOLTSEGKERETEK,
  elofizetesek: ELOFIZETESEK,
  celok: CELOK,
  setHonap: (honap) => set({ honap }),
  leptetHonap: (delta) => set((s) => ({ honap: leptetHonap(s.honap, delta) })),
  setSzuro: (szuro) => set({ szuro }),
  modositTranzakcio: (id, valtozas) =>
    set((s) => ({
      tranzakciok: s.tranzakciok.map((t) => (t.id === id ? { ...t, ...valtozas } : t)),
    })),
}));
