/** n8n webhook alap URL (pl. https://n8n.cloudoptima.hu). Üres érték esetén a mock réteg válaszol. */
export const N8N_BASE_URL = (process.env.EXPO_PUBLIC_N8N_BASE_URL ?? '').replace(/\/$/, '');
/** A webhookok `X-App-Key` fejléce. Nem titok a szó szigorú értelmében (az app csomagjában van), csak elriasztja a véletlen hívásokat. */
export const N8N_APP_KEY = process.env.EXPO_PUBLIC_N8N_APP_KEY ?? '';
