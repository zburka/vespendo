import { StyleSheet, View } from 'react-native';
import { ActivityIndicator, Button, Text, useTheme } from 'react-native-paper';

import { useStore } from '../store/useStore';

/** Élő módban: töltésjelző az első betöltéskor, hiba esetén üzenet és újrapróbálás. */
export function AdatAllapot() {
  const theme = useTheme();
  const toltes = useStore((s) => s.toltes);
  const hiba = useStore((s) => s.hiba);
  const betoltes = useStore((s) => s.betoltes);
  const vanAdat = useStore((s) => s.kategoriak.length > 0);

  if (hiba) {
    return (
      <View style={styles.doboz}>
        <Text style={{ color: theme.colors.error }}>
          Nem sikerült betölteni az adatokat: {hiba}
        </Text>
        <Button mode="outlined" onPress={betoltes}>
          Újrapróbálás
        </Button>
      </View>
    );
  }
  if (toltes && !vanAdat) return <ActivityIndicator style={styles.doboz} />;
  return null;
}

const styles = StyleSheet.create({
  doboz: { gap: 8, marginVertical: 8 },
});
