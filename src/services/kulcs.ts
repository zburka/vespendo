import * as SecureStore from 'expo-secure-store';

const KULCS = 'vespendo.app_key';

/** Az alkalmazás kulcsa a telefon biztonságos tárolójában (iOS Keychain / Android Keystore). */
export const kulcsOlvas = () => SecureStore.getItemAsync(KULCS);
export const kulcsMent = (ertek: string) => SecureStore.setItemAsync(KULCS, ertek);
export const kulcsTorol = () => SecureStore.deleteItemAsync(KULCS);
