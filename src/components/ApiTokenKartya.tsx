import { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';
import { Button, Card, Dialog, Divider, List, Portal, Text, TextInput } from 'react-native-paper';

import { useKeyboardHeight } from '../hooks/useKeyboardHeight';
import { type ApiToken, apiTokenek, apiTokenLetrehoz, apiTokenTorol } from '../services/auth';
import { masol } from '../utils/masol';
import { Alert } from '../utils/uzenet';

/** API tokenek az iOS Parancsokhoz (banki kivonat megosztása az appba lépés nélkül). A token csak létrehozáskor látható. */
export function ApiTokenKartya() {
  const [tokenek, setTokenek] = useState<ApiToken[]>([]);
  const [nev, setNev] = useState('');
  const [nyitva, setNyitva] = useState(false);
  const [uj, setUj] = useState<string | null>(null);
  const [folyamatban, setFolyamatban] = useState(false);
  const billentyuzet = useKeyboardHeight();

  const frissit = useCallback(() => apiTokenek().then(setTokenek).catch(() => {}), []);
  useEffect(() => {
    frissit();
  }, [frissit]);

  const hiba = (e: unknown) => Alert.alert('Hiba', e instanceof Error ? e.message : 'A művelet nem sikerült.');

  const letrehoz = async () => {
    setFolyamatban(true);
    try {
      const t = await apiTokenLetrehoz(nev.trim() || 'iPhone Parancsok');
      setNyitva(false);
      setNev('');
      setUj(t.token);
      await frissit();
    } catch (e) {
      hiba(e);
    }
    setFolyamatban(false);
  };

  return (
    <Card>
      <Card.Title
        title="API tokenek"
        subtitle="Az iOS Parancsok bejelentkezés nélkül tölthet fel banki kivonatot (csak erre jó)"
      />
      <Card.Content>
        {tokenek.length === 0 && <Text variant="bodySmall">Nincs létrehozott token.</Text>}
        {tokenek.map((t, i) => (
          <View key={t.id}>
            {i > 0 && <Divider />}
            <List.Item
              title={t.nev}
              description={`létrehozva: ${t.letrehozva.slice(0, 10)} · utoljára: ${t.utolso ? t.utolso.slice(0, 10) : 'még nem'}`}
              right={() => (
                <Button
                  compact
                  textColor="#b3261e"
                  onPress={() =>
                    Alert.alert('Token törlése', `A(z) „${t.nev}” token azonnal érvényét veszti.`, [
                      { text: 'Mégse', style: 'cancel' },
                      { text: 'Törlés', style: 'destructive', onPress: () => apiTokenTorol(t.id).then(frissit).catch(hiba) },
                    ])
                  }
                >
                  Törlés
                </Button>
              )}
            />
          </View>
        ))}
      </Card.Content>
      <Card.Actions>
        <Button icon="key-plus" onPress={() => setNyitva(true)}>
          Új token
        </Button>
      </Card.Actions>
      <Portal>
        <Dialog visible={nyitva} dismissable={false} style={{ marginBottom: billentyuzet }}>
          <Dialog.Title>Új API token</Dialog.Title>
          <Dialog.Content>
            <TextInput mode="outlined" label="Név (pl. iPhone Parancsok)" value={nev} onChangeText={setNev} />
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setNyitva(false)} disabled={folyamatban}>
              Mégse
            </Button>
            <Button onPress={letrehoz} loading={folyamatban} disabled={folyamatban}>
              Létrehozás
            </Button>
          </Dialog.Actions>
        </Dialog>
        <Dialog visible={uj !== null} dismissable={false}>
          <Dialog.Title>A token</Dialog.Title>
          <Dialog.Content style={{ gap: 8 }}>
            <Text variant="bodySmall">Most láthatod utoljára. Másold be a Parancsba (Authorization: Bearer …).</Text>
            <Text selectable>{uj}</Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => uj && masol(uj).catch(hiba)}>Másolás</Button>
            <Button onPress={() => setUj(null)}>Kész</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </Card>
  );
}
