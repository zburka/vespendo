import { ScrollView, StyleSheet } from 'react-native';
import { Button, Card, List, SegmentedButtons, Text } from 'react-native-paper';

import { N8N_BASE_URL } from '../../config';
import { ELO_API } from '../../services/api';
import { useStore } from '../../store/useStore';

export default function BeallitasokScreen() {
  const szerep = useStore((s) => s.szerep);
  const setSzerep = useStore((s) => s.setSzerep);
  const setKulcsSzukseges = useStore((s) => s.setKulcsSzukseges);
  const betoltes = useStore((s) => s.betoltes);
  const toltes = useStore((s) => s.toltes);
  const tetelszam = useStore((s) => s.tranzakciok.length);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card>
        <Card.Title
          title="Ki vagyok én?"
          subtitle="Az importoknál ez az alapértelmezett feltöltő"
        />
        <Card.Content>
          <SegmentedButtons
            value={szerep ?? ''}
            onValueChange={(v) => setSzerep(v as 'ferj' | 'feleseg')}
            buttons={[
              { value: 'ferj', label: 'Férj' },
              { value: 'feleseg', label: 'Feleség' },
            ]}
          />
        </Card.Content>
      </Card>

      <Card>
        <Card.Title title="Szerver" />
        <Card.Content>
          <List.Item
            title="Mód"
            description={ELO_API ? 'Élő (n8n szerver)' : 'Mock (minta adatok, EXPO_PUBLIC_MOCK=1)'}
          />
          {ELO_API && <List.Item title="Cím" description={N8N_BASE_URL} />}
          <List.Item title="Betöltött tételek" description={`${tetelszam} db`} />
        </Card.Content>
        <Card.Actions>
          <Button onPress={betoltes} loading={toltes} disabled={toltes}>
            Frissítés
          </Button>
          {ELO_API && <Button onPress={() => setKulcsSzukseges(true)}>Kulcs cseréje</Button>}
        </Card.Actions>
      </Card>

      <Text variant="bodySmall">VeSpendo</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
});
