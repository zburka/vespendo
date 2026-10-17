import * as SecureStore from 'expo-secure-store';

const KULCS = 'vespendo.app_key';

/** Az alkalmazás kulcsa a telefon biztonságos tárolójában (iOS Keychain / Android Keystore). */
export const kulcsOlvas = () => SecureStore.getItemAsync(KULCS);
export const kulcsMent = (ertek: string) => SecureStore.setItemAsync(KULCS, ertek);
export const kulcsTorol = () => SecureStore.deleteItemAsync(KULCS);

const SZEREP = 'vespendo.szerep';

export type Szerep = 'ferj' | 'feleseg';

/** Ki használja ezt a telefont (az importoknál alapértelmezett feltöltő). */
export async function szerepOlvas(): Promise<Szerep | null> {
  const ertek = await SecureStore.getItemAsync(SZEREP);
  return ertek === 'ferj' || ertek === 'feleseg' ? ertek : null;
}
export const szerepMent = (szerep: Szerep) => SecureStore.setItemAsync(SZEREP, szerep);
