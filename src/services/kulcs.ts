import * as SecureStore from './tarolo';

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
