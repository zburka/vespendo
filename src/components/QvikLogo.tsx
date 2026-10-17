import { Image, StyleSheet } from 'react-native';

// Az MNB hivatalos qvik logója (színes, módosítatlan, a méretarány megtartva). Az MNB arculati kézikönyve szerint
// legalább 57 x 24 px méretben, az azonnali fizetési (AFR) tételek mellett kell megjeleníteni.
const LOGO = require('../../assets/qvik-logo.png');
const ARANY = 185 / 78;

/** `magassag` legalább 24 legyen (kézikönyv: min. 57 x 24 px). */
export function QvikLogo({ magassag = 26 }: { magassag?: number }) {
  return (
    <Image
      source={LOGO}
      accessibilityLabel="qvik azonnali fizetés"
      style={[styles.logo, { height: magassag, width: Math.round(magassag * ARANY) }]}
      resizeMode="contain"
    />
  );
}

const styles = StyleSheet.create({
  logo: { alignSelf: 'flex-end' },
});
