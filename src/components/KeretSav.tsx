import { StyleSheet, View } from 'react-native';

import { keretSzin } from '../utils/format';

interface Props {
  elkoltve: number;
  keret: number;
}

/**
 * Költségkeret sáv: a kitöltés az elköltött összeg, a piros függőleges vonal a keret határa.
 * Túllépésnél a sáv a vonalon túl is folytatódik, így látszik, mennyivel lépted át a határt.
 */
export function KeretSav({ elkoltve, keret }: Props) {
  const szazalek = keret > 0 ? Math.round((elkoltve / keret) * 100) : 0;
  const skala = Math.max(keret, elkoltve, 1);
  const kitoltes = Math.min(elkoltve / skala, 1) * 100;
  const hatar = Math.min((keret / skala) * 100, 99.4);

  return (
    <View style={styles.kulso}>
      <View style={styles.sav}>
        <View
          style={[styles.kitoltes, { width: `${kitoltes}%`, backgroundColor: keretSzin(szazalek) }]}
        />
      </View>
      <View style={[styles.hatar, { left: `${hatar}%` }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  kulso: { height: 18, justifyContent: 'center' },
  sav: { height: 10, borderRadius: 5, backgroundColor: '#e0e0e0', overflow: 'hidden' },
  kitoltes: { height: '100%', borderRadius: 5 },
  hatar: {
    position: 'absolute',
    top: 0,
    width: 2,
    height: 18,
    marginLeft: -1,
    borderRadius: 1,
    backgroundColor: '#d32f2f',
  },
});
