import { ScrollView, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';

export default function CelokScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text variant="headlineMedium">Célok és Keretek</Text>
      <Text variant="bodyMedium">Megtakarítási célok és költségkeretek beállítása ide kerül.</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 16,
    gap: 8,
  },
});
