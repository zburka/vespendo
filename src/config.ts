import { Platform } from 'react-native';

/**
 * n8n webhook alap URL. A szerver címe nem titok, ezért alapértelmezetten be van égetve;
 * `EXPO_PUBLIC_N8N_BASE_URL` felülírja (pl. teszt szerverre).
 */
// Weben (PWA) a saját eredetet használjuk: a webszerver a /webhook/ útvonalat az n8n-hez továbbítja, így nincs CORS-gond.
const webEredet =
  Platform.OS === 'web' && typeof window !== 'undefined' ? window.location.origin : '';

export const N8N_BASE_URL = (
  process.env.EXPO_PUBLIC_N8N_BASE_URL ||
  webEredet ||
  'https://n8n.cloudoptima.hu'
).replace(/\/$/, '');

/** Mock mód (szerver nélküli fejlesztés): `EXPO_PUBLIC_MOCK=1`. */
export const MOCK_MOD = process.env.EXPO_PUBLIC_MOCK === '1';

/** Fejlesztői kényelem: az `X-App-Key` megadható környezeti változóval is; különben az app első indításkor kéri. */
export const N8N_APP_KEY_ENV = process.env.EXPO_PUBLIC_N8N_APP_KEY ?? '';
