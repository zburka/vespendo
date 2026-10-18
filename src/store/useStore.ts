import { create } from 'zustand';

import {
  CELOK,
  ELOFIZETESEK,
  KATEGORIAK,
  KOLTSEGKERETEK,
  SZABALYOK,
  SZEMELYEK,
  TRANZAKCIOK,
} from '../mock/data';
import {
  alapadatok,
  celMentes,
  celTorles,
  ELO_API,
  elofizetesMentes,
  elofizetesTorles,
  keretMentes,
  szemelyMentes,
  tranzakciokLekeres,
} from '../services/api';
import {
  belepes as authBelepes,
  kilepes as authKilepes,
  NincsBelepes,
  onKilepett,
  type Profil,
  profil as authProfil,
  regisztracio as authRegisztracio,
  type RegisztraciosAdat,
  szemelyKapcsolas,
  vanMunkamenet,
} from '../services/auth';
import { elutasitottMent } from '../services/kulcs';
import { alkalmazImport } from '../services/mockImport';
import type {
  BankiImportKeres,
  Elofizetes,
  ImportOsszegzes,
  Kategoria,
  Koltsegkeret,
  MegtakaritasiCel,
  Szabaly,
  Szemely,
  Tranzakcio,
} from '../types';
import { aktualisHonap, leptetHonap } from '../utils/format';
import { kereskedoKulcs } from '../utils/kereskedo';

let elsoBetoltes = true;

/** Tulajdonos szerinti szűrő: 'mind' vagy egy személy kulcsa. */
export type TulajdonosSzuro = string;

interface State {
  honap: string; // YYYY-MM
  szuro: TulajdonosSzuro;
  kategoriak: Kategoria[];
  tranzakciok: Tranzakcio[];
  keretek: Koltsegkeret[];
  elofizetesek: Elofizetes[];
  celok: MegtakaritasiCel[];
  szabalyok: Szabaly[];
  szemelyek: Szemely[];
  /** Dashboardról kategóriára szűrés a tranzakciólistán (kategória azonosító). */
  kategoriaSzuro: string | null;
  setKategoriaSzuro: (id: string | null) => void;
  /** Új személy (kulcs nélkül) vagy átnevezés / kikapcsolás. */
  mentSzemely: (kulcs: string | undefined, nev: string, aktiv: boolean) => Promise<string | null>;
  /** Élő módban: töltés állapota és az utolsó hiba. */
  toltes: boolean;
  hiba: string | null;
  /** Belépési állapot: induláskor 'betolt', majd 'kilepve' (belépőképernyő), 'belepve' vagy 'hiba' (nincs kapcsolat). */
  munkamenet: 'betolt' | 'kilepve' | 'belepve' | 'hiba';
  munkamenetHiba: string | null;
  /** A bejelentkezett felhasználó, háztartása és tagjai (mock módban null). */
  en: Profil | null;
  /** Induláskor: van-e eltárolt belépés, és érvényes-e. */
  munkamenetInditas: () => Promise<void>;
  belepes: (email: string, jelszo: string) => Promise<void>;
  regisztracio: (adatok: RegisztraciosAdat) => Promise<void>;
  kilepes: () => Promise<void>;
  setEn: (en: Profil) => void;
  profilFrissit: () => Promise<void>;
  /** Élő módban a szerverről (n8n) tölti be az adatokat; mock módban nem csinál semmit. */
  betoltes: () => Promise<void>;
  /** Keret létrehozása/módosítása egy kategóriára (élő módban a szerverre is ment, majd újratölt). */
  mentKeret: (kategoriaId: string, nev: string, haviKeret: number, aktiv: boolean) => Promise<void>;
  /** Cél létrehozása (id nélkül) vagy módosítása. */
  mentCel: (cel: Omit<MegtakaritasiCel, 'id'> & { id?: string }) => Promise<void>;
  torolCel: (id: string) => Promise<void>;
  /** Ki használja ezt a telefont; az importoknál ez az alapértelmezett feltöltő. */
  szerep: string | null;
  szerepSzukseges: boolean;
  setSzerep: (szerep: string) => Promise<void>;
  setSzerepSzukseges: (ertek: boolean) => void;
  mentElofizetes: (e: Omit<Elofizetes, 'id'> & { id?: string }) => Promise<void>;
  torolElofizetes: (id: string) => Promise<void>;
  /** Helyi állapotból törli a tételt (a szerveroldali törlés külön hívás). */
  torolTranzakcioLokal: (id: string) => void;
  /** Elvetett előfizetés-javaslatok (kereskedő|összeg), a telefonon tárolva. */
  elutasitott: string[];
  setElutasitott: (lista: string[]) => void;
  elvetJavaslat: (kulcs: string) => Promise<void>;
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

/** Kilépéskor / felhasználóváltáskor a háztartás adatai nem maradhatnak a memóriában. */
function adatTorles() {
  elsoBetoltes = true;
  useStore.setState({
    kategoriak: [],
    tranzakciok: [],
    keretek: [],
    elofizetesek: [],
    celok: [],
    szabalyok: [],
    szemelyek: [],
    kategoriaSzuro: null,
    szuro: 'mind',
    hiba: null,
  });
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
  szemelyek: ELO_API ? [] : SZEMELYEK,
  kategoriaSzuro: null,
  setKategoriaSzuro: (kategoriaSzuro) => set({ kategoriaSzuro }),
  mentSzemely: async (kulcs, nev, aktiv) => {
    if (ELO_API) {
      const uj = await szemelyMentes({ kulcs, nev, aktiv });
      await get().betoltes();
      return uj ?? kulcs ?? null;
    }
    const ujKulcs = kulcs ?? `szemely${Date.now()}`;
    set((s) => ({
      szemelyek: kulcs
        ? s.szemelyek.map((x) => (x.kulcs === kulcs ? { ...x, nev, aktiv } : x))
        : [...s.szemelyek, { kulcs: ujKulcs, nev, aktiv }],
    }));
    return ujKulcs;
  },
  toltes: false,
  hiba: null,
  munkamenet: ELO_API ? 'betolt' : 'belepve',
  munkamenetHiba: null,
  en: null,
  setEn: (en) => set({ en, szerep: en.haztartas.szemely_kulcs, szerepSzukseges: !en.haztartas.szemely_kulcs }),
  munkamenetInditas: async () => {
    if (!ELO_API) return;
    set({ munkamenet: 'betolt', munkamenetHiba: null });
    try {
      if (!(await vanMunkamenet())) {
        set({ munkamenet: 'kilepve' });
        return;
      }
      const en = await authProfil();
      get().setEn(en);
      set({ munkamenet: 'belepve' });
      await get().betoltes();
    } catch (e) {
      if (e instanceof NincsBelepes) set({ munkamenet: 'kilepve' });
      else
        set({
          munkamenet: 'hiba',
          munkamenetHiba: e instanceof Error ? e.message : 'A szerver nem érhető el',
        });
    }
  },
  belepes: async (email, jelszo) => {
    const en = await authBelepes(email, jelszo);
    adatTorles();
    get().setEn(en);
    set({ munkamenet: 'belepve' });
    await get().betoltes();
  },
  regisztracio: async (adatok) => {
    const en = await authRegisztracio(adatok);
    adatTorles();
    get().setEn(en);
    set({ munkamenet: 'belepve' });
    await get().betoltes();
  },
  kilepes: async () => {
    await authKilepes();
    adatTorles();
    set({ munkamenet: 'kilepve', en: null, szerep: null, szerepSzukseges: false });
  },
  profilFrissit: async () => {
    if (!ELO_API) return;
    get().setEn(await authProfil());
  },
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
      if (e instanceof NincsBelepes) {
        set({ toltes: false, munkamenet: 'kilepve' });
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
    if (ELO_API) {
      // a személy a fiókhoz kötődik (a szerveren), nem a telefonhoz
      get().setEn(await szemelyKapcsolas(szerep));
      return;
    }
    set({ szerep, szerepSzukseges: false });
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
  elutasitott: [],
  setElutasitott: (elutasitott) => set({ elutasitott }),
  elvetJavaslat: async (kulcs) => {
    const lista = [...new Set([...get().elutasitott, kulcs])];
    set({ elutasitott: lista });
    try {
      await elutasitottMent(lista);
    } catch {
      // a tároló nem érhető el: az elvetés csak az aktuális munkamenetre él
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

// ha a szerver a munkamenetet véglegesen érvénytelennek mondja (pl. másik eszközről kijelentkeztették), vissza a belépéshez
onKilepett(() => useStore.setState({ munkamenet: 'kilepve' }));
