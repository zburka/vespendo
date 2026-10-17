import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Chip, SegmentedButtons, Text } from 'react-native-paper';

import { useStore } from '../../store/useStore';
import type { Tulajdonos } from '../../types';
import { formatFt, formatNap } from '../../utils/format';

export default function TranzakcioSzerkeszto() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const tranzakcio = useStore((s) => s.tranzakciok.find((t) => t.id === id));
  const kategoriak = useStore((s) => s.kategoriak);
  const modositTranzakcio = useStore((s) => s.modositTranzakcio);
  const modositKategoria = useStore((s) => s.modositKategoria);

  const [kategoriaId, setKategoriaId] = useState(tranzakcio?.kategoria_id ?? '');
  const [tulajdonos, setTulajdonos] = useState<Tulajdonos>(tranzakcio?.tulajdonos ?? 'kozos');

  if (!tranzakcio) {
    return (
      <View style={styles.container}>
        <Stack.Screen options={{ title: 'Tétel' }} />
        <Text>A tétel nem található.</Text>
      </View>
    );
  }

  const bevetel = tranzakcio.tipus !== 'kiadas';
  const valaszthato = kategoriak.filter((k) => k.tipus === (bevetel ? 'bevetel' : 'kiadas'));

  const mentes = () => {
    if (kategoriaId !== tranzakcio.kategoria_id) modositKategoria(tranzakcio.id, kategoriaId);
    if (tulajdonos !== tranzakcio.tulajdonos) modositTranzakcio(tranzakcio.id, { tulajdonos });
    router.back();
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Stack.Screen options={{ title: tranzakcio.kereskedo }} />
      <Text variant="headlineMedium">
        {bevetel ? '+' : '−'}
        {formatFt(tranzakcio.osszeg)}
      </Text>
      <Text variant="bodyMedium">
        {formatNap(tranzakcio.datum)} · {tranzakcio.fizetesi_mod}
      </Text>
      {tranzakcio.megjegyzes ? (
        <Text variant="bodyMedium">Megjegyzés: {tranzakcio.megjegyzes}</Text>
      ) : null}

      <Text variant="titleSmall" style={styles.cim}>Kategória</Text>
      <View style={styles.chipek}>
        {valaszthato.map((k) => (
          <Chip
            key={k.id}
            icon={k.ikon}
            selected={k.id === kategoriaId}
            showSelectedOverlay
            onPress={() => setKategoriaId(k.id)}
          >
            {k.nev}
          </Chip>
        ))}
      </View>
      {kategoriaId !== tranzakcio.kategoria_id && (
        <Text variant="bodySmall">
          Mentéskor szabály jön létre: „{tranzakcio.kereskedo.toLowerCase()}” a jövőben ebbe a
          kategóriába kerül.
        </Text>
      )}

      <Text variant="titleSmall" style={styles.cim}>Tulajdonos</Text>
      <SegmentedButtons
        value={tulajdonos}
        onValueChange={(v) => setTulajdonos(v as Tulajdonos)}
        buttons={[
          { value: 'kozos', label: 'Közös' },
          { value: 'ferj', label: 'Férj' },
          { value: 'feleseg', label: 'Feleség' },
        ]}
      />

      <Button mode="contained" onPress={mentes} style={styles.gomb}>
        Mentés
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 8 },
  cim: { marginTop: 12 },
  chipek: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  gomb: { marginTop: 24 },
});
