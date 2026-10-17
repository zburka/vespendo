import { ScrollView, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';

export default function TranzakciokScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text variant="headlineMedium">Tranzakciók</Text>
      <Text variant="bodyMedium">
        Dátum szerint csoportosított lista és tulajdonos szerinti szűrés (Mind / Közös / Férj /
        Feleség) ide kerül.
      </Text>
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
