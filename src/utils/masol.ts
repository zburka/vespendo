import { Platform, Share } from 'react-native';

/** Szöveg vágólapra (web) vagy megosztási lapra (natív), hogy pl. a meghívókód elküldhető legyen. */
export async function masol(szoveg: string): Promise<'masolva' | 'megosztva'> {
  if (Platform.OS === 'web') {
    await navigator.clipboard.writeText(szoveg);
    return 'masolva';
  }
  await Share.share({ message: szoveg });
  return 'megosztva';
}
