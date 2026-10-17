import { ScrollView, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';

export default function DashboardScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text variant="headlineMedium">Dashboard</Text>
      <Text variant="bodyMedium">Havi összegzés, költségkeretek és AI elemzés ide kerül.</Text>
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
