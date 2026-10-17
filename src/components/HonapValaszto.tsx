import { StyleSheet, View } from 'react-native';
import { IconButton, Text } from 'react-native-paper';

import { useStore } from '../store/useStore';
import { formatHonap } from '../utils/format';

export function HonapValaszto() {
  const honap = useStore((s) => s.honap);
  const leptet = useStore((s) => s.leptetHonap);

  return (
    <View style={styles.sor}>
      <IconButton icon="chevron-left" onPress={() => leptet(-1)} accessibilityLabel="Előző hónap" />
      <Text variant="titleLarge">{formatHonap(honap)}</Text>
      <IconButton icon="chevron-right" onPress={() => leptet(1)} accessibilityLabel="Következő hónap" />
    </View>
  );
}

const styles = StyleSheet.create({
  sor: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
});
