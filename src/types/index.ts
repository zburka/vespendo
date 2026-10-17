export type KategoriaTipus = 'kiadas' | 'bevetel';
export type TranzakcioTipus = 'kiadas' | 'bevetel_rendszeres' | 'bevetel_egyszeri';
/** A személy kulcsa (a szemelyek tábla kulcsa): 'kozos', 'ferj', 'feleseg' vagy bármely felvett személy. */
export type Tulajdonos = string;

export interface Szemely {
  kulcs: string;
  nev: string;
  aktiv: boolean;
}
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
  /** Kiadás személyenként (kulcs → összeg); a `bontas_tulajdonos_szerint` helyett ezt használja az app. */
  bontas_szemely_szerint?: Record<string, number>;
  keretek: KeretAllapot[];
  /** Az élő végpont csak az összeget adja; a részletes lista a mock/lokális számításból jön. */
  elofizetesek?: ElofizetesAllapot[];
  varhato_hatralevo_elofizetesek: number;
  ai_elemzes: string;
}

export interface Szabaly {
  id: string;
  minta: string; // kisbetűs keresőszó
  kategoria_id: string;
  alapertelmezett_tulajdonos?: Tulajdonos;
}

export interface NyugtaKeres {
  kep_base64: string;
  megjegyzes: string;
  feltolto: Exclude<Tulajdonos, 'kozos'>;
}

export interface NyugtaValasz {
  status: 'success';
  data: {
    kereskedo: string;
    osszeg: number;
    datum: string;
    fizetesi_mod: FizetesiMod;
    allapot: Allapot;
    bontott_tetelek: { kategoria: string; osszeg: number }[];
  };
}

export interface BankiTranzakcio {
  datum: string;
  osszeg: number;
  kereskedo_nyers: string;
  kozlemeny: string;
  irany: 'kiadas' | 'bevetel';
}

export interface BankiImportKeres {
  feltolto: Exclude<Tulajdonos, 'kozos'>;
  tranzakciok: BankiTranzakcio[];
}

export interface ImportOsszegzes {
  uj: number;
  egyeztetve: number;
  szaballyal: number;
  ismeretlen: number;
  duplikalt?: number;
  ai_besorolt?: number;
}

export interface KategoriaModositasKeres {
  tranzakcio_id: string;
  uj_kategoria_id?: string;
  uj_tulajdonos?: Tulajdonos;
  kereskedo_minta?: string;
}

/** `GET /webhook/adatok`: a nem tranzakció jellegű törzsadatok. */
export interface Alapadatok {
  kategoriak: Kategoria[];
  keretek: Koltsegkeret[];
  elofizetesek: Elofizetes[];
  celok: MegtakaritasiCel[];
  szabalyok: Szabaly[];
  szemelyek: Szemely[];
}

export interface FajlElemzesKeres {
  fajl_nev: string;
  fajl_base64: string;
}

export type Megbizhatosag = 'magas' | 'kozepes' | 'alacsony';

/** `POST /webhook/banki-fajl-elemzes` válasza (a Python elemző szolgáltatás kimenete). */
export interface FajlElemzesValasz {
  status: 'success' | 'error';
  uzenet?: string;
  data?: {
    tranzakciok: BankiTranzakcio[];
    kihagyott: number;
    megbizhatosag: Megbizhatosag;
    figyelmeztetesek: string[];
    /** Nyitó/záró egyenleg alapú ellenőrzés (ha a kivonat tartalmaz ilyet). */
    egyenleg_ellenorzes?: { nyito: number; zaro: number; egyezik: boolean; elteres: number } | null;
  };
}

export interface UjTranzakcioKeres {
  osszeg: number;
  datum: string; // YYYY-MM-DD
  kereskedo: string;
  kategoria_id: string;
  tipus: TranzakcioTipus;
  tulajdonos: Tulajdonos;
  fizetesi_mod: FizetesiMod;
  megjegyzes?: string;
}
