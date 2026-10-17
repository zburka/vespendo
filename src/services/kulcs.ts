import * as SecureStore from 'expo-secure-store';

const KULCS = 'vespendo.app_key';

/** Az alkalmazás kulcsa a telefon biztonságos tárolójában (iOS Keychain / Android Keystore). */
export const kulcsOlvas = () => SecureStore.getItemAsync(KULCS);
export const kulcsMent = (ertek: string) => SecureStore.setItemAsync(KULCS, ertek);
export const kulcsTorol = () => SecureStore.deleteItemAsync(KULCS);

const SZEREP = 'vespendo.szerep';

export type Szerep = string;

/** Ki használja ezt a telefont (az importoknál alapértelmezett feltöltő). */
export async function szerepOlvas(): Promise<Szerep | null> {
  const ertek = await SecureStore.getItemAsync(SZEREP);
  return ertek && /^[a-z0-9_]{1,30}$/.test(ertek) ? ertek : null;
}
export const szerepMent = (szerep: Szerep) => SecureStore.setItemAsync(SZEREP, szerep);

const ELUTASITOTT = 'vespendo.elutasitott_javaslatok';

/** Az elvetett előfizetés-javaslatok kulcsai (kereskedő|összeg). */
export async function elutasitottOlvas(): Promise<string[]> {
  try {
    const nyers = await SecureStore.getItemAsync(ELUTASITOTT);
    const lista = nyers ? JSON.parse(nyers) : [];
    return Array.isArray(lista) ? lista.filter((x) => typeof x === 'string') : [];
  } catch {
    return [];
  }
}
export const elutasitottMent = (lista: string[]) =>
  SecureStore.setItemAsync(ELUTASITOTT, JSON.stringify(lista));
