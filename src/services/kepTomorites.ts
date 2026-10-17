import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';

const MAX_SZELESSEG = 1200;
const JPEG_MINOSEG = 0.7;

/**
 * Feltöltés előtti eszközoldali tömörítés: max. 1200 px szélesség, 70% JPEG.
 * Visszaadja a `kep_base64` mezőbe szánt data URI-t.
 */
export async function tomorit(uri: string, szelesseg: number): Promise<string> {
  const context = ImageManipulator.manipulate(uri);
  if (szelesseg > MAX_SZELESSEG) context.resize({ width: MAX_SZELESSEG });
  const kep = await context.renderAsync();
  const eredmeny = await kep.saveAsync({
    format: SaveFormat.JPEG,
    compress: JPEG_MINOSEG,
    base64: true,
  });
  context.release();
  return `data:image/jpeg;base64,${eredmeny.base64}`;
}
