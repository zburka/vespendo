import { Platform } from 'react-native';

/** A kiválasztott fájl tartalma bájtokban (natívan expo-file-system, weben a böngésző blobja). */
export async function fajlBajtok(uri: string): Promise<Uint8Array> {
  if (Platform.OS === 'web') return new Uint8Array(await (await fetch(uri)).arrayBuffer());
  const { File } = await import('expo-file-system');
  return new File(uri).bytes();
}

/** A kiválasztott fájl tartalma base64-ben. */
export async function fajlBase64(uri: string): Promise<string> {
  if (Platform.OS === 'web') {
    const blob = await (await fetch(uri)).blob();
    return new Promise((resolve, reject) => {
      const olvaso = new FileReader();
      olvaso.onload = () => resolve(String(olvaso.result).split(',')[1] ?? '');
      olvaso.onerror = () => reject(new Error('A fájl nem olvasható'));
      olvaso.readAsDataURL(blob);
    });
  }
  const { File } = await import('expo-file-system');
  return new File(uri).base64();
}
