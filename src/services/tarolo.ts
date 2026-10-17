import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/** Kulcs-érték tároló: natívan a biztonságos tároló (Keychain / Keystore), weben a böngésző `localStorage`-a. */
export async function getItemAsync(kulcs: string): Promise<string | null> {
  if (Platform.OS === 'web') return window.localStorage.getItem(kulcs);
  return SecureStore.getItemAsync(kulcs);
}

export async function setItemAsync(kulcs: string, ertek: string): Promise<void> {
  if (Platform.OS === 'web') return window.localStorage.setItem(kulcs, ertek);
  return SecureStore.setItemAsync(kulcs, ertek);
}

export async function deleteItemAsync(kulcs: string): Promise<void> {
  if (Platform.OS === 'web') return window.localStorage.removeItem(kulcs);
  return SecureStore.deleteItemAsync(kulcs);
}
