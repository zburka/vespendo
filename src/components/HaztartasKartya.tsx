import { View } from 'react-native';
import { useState } from 'react';
import { Button, Card, Dialog, Divider, List, Portal, Text } from 'react-native-paper';

import { tagEltavolit, tagJelszoVisszaallitas, ujMeghivokod } from '../services/auth';
import { useStore } from '../store/useStore';
import { masol } from '../utils/masol';
import { Alert } from '../utils/uzenet';

/** A háztartás: tagok, meghívókód (csak adminnak), tagkezelés. */
export function HaztartasKartya() {
  const en = useStore((s) => s.en);
  const szemelyek = useStore((s) => s.szemelyek);
  const profilFrissit = useStore((s) => s.profilFrissit);
  const [ideiglenes, setIdeiglenes] = useState<{ nev: string; jelszo: string } | null>(null);

  if (!en) return null;
  const admin = en.haztartas.szerep === 'admin';
  const hiba = (e: unknown) => Alert.alert('Hiba', e instanceof Error ? e.message : 'A művelet nem sikerült.');

  const meghivo = async () => {
    const kod = en.haztartas.meghivokod;
    if (!kod) return;
    try {
      const mod = await masol(`VeSpendo meghívókód: ${kod}`);
      if (mod === 'masolva') Alert.alert('Meghívókód', 'A meghívókód a vágólapra került.');
    } catch (e) {
      hiba(e);
    }
  };

  const ujKod = () =>
    Alert.alert('Új meghívókód', 'A régi kód érvényét veszti. Folytatod?', [
      { text: 'Mégse', style: 'cancel' },
      {
        text: 'Új kód',
        onPress: () =>
          ujMeghivokod()
            .then(profilFrissit)
            .catch(hiba),
      },
    ]);

  const eltavolit = (id: number, nev: string) =>
    Alert.alert('Tag eltávolítása', `${nev} nem fér hozzá többé a háztartáshoz. Folytatod?`, [
      { text: 'Mégse', style: 'cancel' },
      { text: 'Eltávolítás', style: 'destructive', onPress: () => tagEltavolit(id).then(profilFrissit).catch(hiba) },
    ]);

  const visszaallit = (id: number, nev: string) =>
    Alert.alert('Jelszó visszaállítása', `${nev} kap egy ideiglenes jelszót, és minden eszközén kijelentkezik.`, [
      { text: 'Mégse', style: 'cancel' },
      {
        text: 'Visszaállítás',
        onPress: () =>
          tagJelszoVisszaallitas(id)
            .then((jelszo) => setIdeiglenes({ nev, jelszo }))
            .catch(hiba),
      },
    ]);

  return (
    <Card>
      <Card.Title title={en.haztartas.nev} subtitle="Háztartás: az adataitokat csak a tagok látják" />
      <Card.Content>
        {en.tagok.map((t, i) => {
          const szemely = szemelyek.find((p) => p.kulcs === t.szemely_kulcs);
          return (
            <View key={t.id}>
              {i > 0 && <Divider />}
              <List.Item
                title={`${t.nev}${t.id === en.felhasznalo.id ? ' (te)' : ''}`}
                description={[t.szerep === 'admin' ? 'admin' : 'tag', szemely?.nev, t.email].filter(Boolean).join(' · ')}
              />
              {admin && t.id !== en.felhasznalo.id && (
                <View style={{ flexDirection: 'row', gap: 4 }}>
                  <Button compact onPress={() => visszaallit(t.id, t.nev)}>
                    Jelszó visszaállítása
                  </Button>
                  <Button compact textColor="#b3261e" onPress={() => eltavolit(t.id, t.nev)}>
                    Eltávolítás
                  </Button>
                </View>
              )}
            </View>
          );
        })}
        {admin && en.haztartas.meghivokod && (
          <View style={{ marginTop: 12 }}>
            <Text variant="bodySmall">Meghívókód új tagnak (a regisztrációnál a „Csatlakozás” fülön kell megadni):</Text>
            <Text variant="headlineSmall" selectable style={{ letterSpacing: 2 }}>
              {en.haztartas.meghivokod}
            </Text>
          </View>
        )}
      </Card.Content>
      {admin && (
        <Card.Actions>
          <Button icon="share-variant" onPress={meghivo}>
            Meghívókód küldése
          </Button>
          <Button onPress={ujKod}>Új kód</Button>
        </Card.Actions>
      )}
      <Portal>
        <Dialog visible={ideiglenes !== null} onDismiss={() => setIdeiglenes(null)}>
          <Dialog.Title>Ideiglenes jelszó</Dialog.Title>
          <Dialog.Content style={{ gap: 8 }}>
            <Text>{ideiglenes?.nev} új, ideiglenes jelszava (csak most látható):</Text>
            <Text variant="titleMedium" selectable>
              {ideiglenes?.jelszo}
            </Text>
            <Text variant="bodySmall">Belépés után ajánlott a jelszócsere.</Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setIdeiglenes(null)}>Rendben</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </Card>
  );
}
