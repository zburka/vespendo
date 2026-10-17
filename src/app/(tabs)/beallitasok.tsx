import { useState } from 'react';
import { Alert, ScrollView, StyleSheet, View } from 'react-native';
import {
  Button,
  Card,
  Dialog,
  Divider,
  List,
  Portal,
  Switch,
  Text,
  TextInput,
} from 'react-native-paper';

import { SzemelyValaszto } from '../../components/SzemelyValaszto';
import { N8N_BASE_URL } from '../../config';
import { ELO_API } from '../../services/api';
import { useStore } from '../../store/useStore';
import type { Szemely } from '../../types';

export default function BeallitasokScreen() {
  const szerep = useStore((s) => s.szerep);
  const setSzerep = useStore((s) => s.setSzerep);
  const szemelyek = useStore((s) => s.szemelyek);
  const mentSzemely = useStore((s) => s.mentSzemely);
  const setKulcsSzukseges = useStore((s) => s.setKulcsSzukseges);
  const betoltes = useStore((s) => s.betoltes);
  const toltes = useStore((s) => s.toltes);
  const tetelszam = useStore((s) => s.tranzakciok.length);

  // személy szerkesztő: null = zárva, { szemely: undefined } = új személy
  const [szerkesztes, setSzerkesztes] = useState<{ szemely?: Szemely } | null>(null);
  const [nev, setNev] = useState('');
  const [mentes, setMentes] = useState(false);

  const megnyit = (szemely?: Szemely) => {
    setNev(szemely?.nev ?? '');
    setSzerkesztes({ szemely });
  };

  const hiba = (e: unknown) =>
    Alert.alert('Mentés', e instanceof Error ? e.message : 'A mentés nem sikerült.');

  const ment = async () => {
    if (!szerkesztes || !nev.trim()) return Alert.alert('Hiba', 'Add meg a nevet.');
    setMentes(true);
    try {
      await mentSzemely(szerkesztes.szemely?.kulcs, nev.trim(), szerkesztes.szemely?.aktiv ?? true);
      setSzerkesztes(null);
    } catch (e) {
      hiba(e);
    }
    setMentes(false);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card>
        <Card.Title
          title="Ki vagyok én?"
          subtitle="Az importoknál és az új tételeknél ez az alapértelmezett"
        />
        <Card.Content>
          <SzemelyValaszto ertek={szerep ?? ''} onChange={setSzerep} kozos={false} />
        </Card.Content>
      </Card>

      <Card>
        <Card.Title
          title="Személyek"
          subtitle="A tételek tulajdonosa: átnevezhető, új személy (pl. gyerek) felvehető"
        />
        <Card.Content>
          {szemelyek.map((p, i) => (
            <View key={p.kulcs}>
              {i > 0 && <Divider />}
              <List.Item
                title={p.nev}
                description={`kulcs: ${p.kulcs}${p.aktiv ? '' : ' · kikapcsolva'}`}
                right={() =>
                  p.kulcs === 'kozos' ? null : (
                    <Switch
                      value={p.aktiv}
                      onValueChange={(aktiv) => mentSzemely(p.kulcs, p.nev, aktiv).catch(hiba)}
                    />
                  )
                }
                onPress={() => megnyit(p)}
              />
            </View>
          ))}
        </Card.Content>
        <Card.Actions>
          <Button icon="account-plus" onPress={() => megnyit()}>
            Új személy
          </Button>
        </Card.Actions>
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

      <Portal>
        <Dialog visible={szerkesztes !== null} onDismiss={() => !mentes && setSzerkesztes(null)}>
          <Dialog.Title>{szerkesztes?.szemely ? 'Személy átnevezése' : 'Új személy'}</Dialog.Title>
          <Dialog.Content>
            <TextInput mode="outlined" label="Név" value={nev} onChangeText={setNev} autoFocus />
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setSzerkesztes(null)} disabled={mentes}>
              Mégse
            </Button>
            <Button onPress={ment} loading={mentes} disabled={mentes}>
              Mentés
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
});
