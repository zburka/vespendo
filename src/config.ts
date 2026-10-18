import { Platform } from 'react-native';

/**
 * A VeSpendo szerver (belépési kapu) alap URL-je. Weben (PWA) a saját eredet: a webszerver az `/api/` útvonalat a kapuhoz
 * továbbítja, így nincs CORS-gond. Natívan a megadott cím; `EXPO_PUBLIC_API_BASE_URL` felülírja (pl. teszt szerverre).
 */
const webEredet =
  Platform.OS === 'web' && typeof window !== 'undefined' ? window.location.origin : '';

export const API_ALAP_URL = (
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  webEredet ||
  'https://vespendo.cloudoptima.hu'
).replace(/\/$/, '');

/** Mock mód (szerver nélküli fejlesztés): `EXPO_PUBLIC_MOCK=1`. */
export const MOCK_MOD = process.env.EXPO_PUBLIC_MOCK === '1';
