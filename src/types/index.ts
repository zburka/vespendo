export type KategoriaTipus = 'kiadas' | 'bevetel';
export type TranzakcioTipus = 'kiadas' | 'bevetel_rendszeres' | 'bevetel_egyszeri';
export type Tulajdonos = 'kozos' | 'ferj' | 'feleseg';
export type FizetesiMod = 'kartya' | 'keszpenz' | 'atutalas';
export type Forras = 'bank_import' | 'nyugta_foto' | 'kezi';
export type Allapot = 'lezart' | 'banki_egyeztetesre_var';

export interface Kategoria {
  id: string;
  nev: string;
  tipus: KategoriaTipus;
  ikon: string;
}

export interface Tranzakcio {
  id: string;
  datum: string; // YYYY-MM-DD
  osszeg: number; // mindig pozitív, a tipus dönti el az irányt
  kereskedo: string;
  kategoria_id: string;
  tipus: TranzakcioTipus;
  tulajdonos: Tulajdonos;
  fizetesi_mod: FizetesiMod;
  forras: Forras;
  allapot: Allapot;
  megjegyzes?: string;
  nyugta_kep_url?: string;
}

export interface Koltsegkeret {
  id: string;
  kategoria_id: string;
  havi_keret: number;
  aktiv: boolean;
}

export interface Elofizetes {
  id: string;
  megnevezes: string;
  varhato_osszeg: number;
  esedekesseg_napja: number;
  kategoria_id: string;
}

export interface MegtakaritasiCel {
  id: string;
  cel_neve: string;
  celosszeg: number;
  aktualis_osszeg: number;
}

export interface KeretAllapot {
  kategoria: string;
  havi_keret: number;
  elkoltve: number;
  szazalek: number;
}

export interface ElofizetesAllapot extends Elofizetes {
  kifizetve: boolean;
}

export interface HaviOsszesito {
  osszes_bevetel: number;
  osszes_kiadas: number;
  egyenleg: number;
  bontas_tulajdonos_szerint: { kozos: number; ferj_sajat: number; feleseg_sajat: number };
  keretek: KeretAllapot[];
  elofizetesek: ElofizetesAllapot[];
  varhato_hatralevo_elofizetesek: number;
  ai_elemzes: string;
}
