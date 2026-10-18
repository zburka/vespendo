import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Dialog, Divider, List, Portal, Text, TextInput, useTheme } from 'react-native-paper';

import { useKeyboardHeight } from '../hooks/useKeyboardHeight';
import { useStore } from '../store/useStore';
import type { Kategoria } from '../types';
import { Alert } from '../utils/uzenet';

const IKONOK = [
  'cart', 'silverware-fork-knife', 'flash', 'film', 'shirt', 'car', 'heart-pulse', 'calendar-sync', 'bank', 'credit-card-clock',
  'sprout', 'paw', 'gift', 'airplane', 'school', 'home', 'baby-face-outline', 'dumbbell', 'cash', 'cash-plus', 'tag',
];

/** Kategóriák kezelése: új felvétele, átnevezés, ikoncsere, törlés (a tételek áthelyezésével). */
export function KategoriaKartya() {
  const theme = useTheme();
  const kategoriak = useStore((s) => s.kategoriak);
  const tranzakciok = useStore((s) => s.tranzakciok);
  const mentKategoria = useStore((s) => s.mentKategoria);
  const torolKategoria = useStore((s) => s.torolKategoria);
  const billentyuzet = useKeyboardHeight();

  // szerkesztő: null = zárva, { kategoria: undefined } = új
  const [szerkesztes, setSzerkesztes] = useState<{ kategoria?: Kategoria } | null>(null);
  const [nev, setNev] = useState('');
  const [tipus, setTipus] = useState<'kiadas' | 'bevetel'>('kiadas');
  const [ikon, setIkon] = useState('tag');
  const [torles, setTorles] = useState<Kategoria | null>(null);
  const [folyamatban, setFolyamatban] = useState(false);

  const megnyit = (kategoria?: Kategoria) => {
    setNev(kategoria?.nev ?? '');
    setTipus(kategoria?.tipus === 'bevetel' ? 'bevetel' : 'kiadas');
    setIkon(kategoria?.ikon || 'tag');
    setSzerkesztes({ kategoria });
  };

  const hiba = (e: unknown) =>
    Alert.alert('Kategória', e instanceof Error ? e.message : 'A művelet nem sikerült.');

  const ment = async () => {
    setFolyamatban(true);
    try {
      await mentKategoria(szerkesztes?.kategoria?.id, nev.trim(), tipus, ikon);
      setSzerkesztes(null);
    } catch (e) {
      hiba(e);
    }
    setFolyamatban(false);
  };

  const torol = async (cel: Kategoria) => {
    if (!torles) return;
    setFolyamatban(true);
    try {
      await torolKategoria(torles.id, cel.id);
      setTorles(null);
      setSzerkesztes(null);
    } catch (e) {
      hiba(e);
    }
    setFolyamatban(false);
  };

  const csoportok: { cim: string; lista: Kategoria[] }[] = [
    { cim: 'Kiadás', lista: kategoriak.filter((k) => k.tipus === 'kiadas') },
    { cim: 'Bevétel', lista: kategoriak.filter((k) => k.tipus === 'bevetel') },
    { cim: 'Belső átvezetés', lista: kategoriak.filter((k) => k.tipus === 'atvezetes') },
  ].filter((c) => c.lista.length > 0);

  const darab = (id: string) => tranzakciok.filter((t) => t.kategoria_id === id).length;
  const celok = torles ? kategoriak.filter((k) => k.id !== torles.id && k.tipus === torles.tipus) : [];

  return (
    <Card>
      <Card.Title title="Kategóriák" subtitle="Saját kategória felvétele, átnevezése, törlése" />
      <Card.Content>
        {csoportok.map((c) => (
          <View key={c.cim}>
            <Text variant="titleSmall" style={styles.csoport}>
              {c.cim}
            </Text>
            {c.lista.map((k, i) => (
              <View key={k.id}>
                {i > 0 && <Divider />}
                <List.Item
                  title={k.nev}
                  description={`${darab(k.id)} tétel`}
                  left={(p) => <List.Icon {...p} icon={k.ikon || 'tag'} />}
                  onPress={() => megnyit(k)}
                />
              </View>
            ))}
          </View>
        ))}
      </Card.Content>
      <Card.Actions>
        <Button icon="plus" onPress={() => megnyit()}>
          Új kategória
        </Button>
      </Card.Actions>

      <Portal>
        <Dialog
          visible={szerkesztes !== null && torles === null}
          dismissable={false}
          style={{ marginBottom: billentyuzet, maxHeight: '90%' }}
        >
          <Dialog.Title>{szerkesztes?.kategoria ? 'Kategória szerkesztése' : 'Új kategória'}</Dialog.Title>
          <Dialog.ScrollArea style={styles.gorgetes}>
            <ScrollView contentContainerStyle={{ gap: 12, paddingVertical: 8 }}>
              <TextInput mode="outlined" label="Név" value={nev} onChangeText={setNev} autoFocus maxLength={40} />
              {!szerkesztes?.kategoria && (
                <View style={styles.sor}>
                  <Chip selected={tipus === 'kiadas'} showSelectedOverlay onPress={() => setTipus('kiadas')}>
                    Kiadás
                  </Chip>
                  <Chip selected={tipus === 'bevetel'} showSelectedOverlay onPress={() => setTipus('bevetel')}>
                    Bevétel
                  </Chip>
                </View>
              )}
              <Text variant="bodySmall">Ikon</Text>
              <View style={styles.sor}>
                {IKONOK.map((i) => (
                  <Chip
                    key={i}
                    icon={i}
                    compact
                    selected={ikon === i}
                    showSelectedOverlay
                    onPress={() => setIkon(i)}
                    style={ikon === i ? { backgroundColor: theme.colors.secondaryContainer } : undefined}
                  >
                    {''}
                  </Chip>
                ))}
              </View>
            </ScrollView>
          </Dialog.ScrollArea>
          <Dialog.Actions>
            {szerkesztes?.kategoria && szerkesztes.kategoria.tipus !== 'atvezetes' && (
              <Button textColor={theme.colors.error} onPress={() => setTorles(szerkesztes.kategoria!)} disabled={folyamatban}>
                Törlés
              </Button>
            )}
            <Button onPress={() => setSzerkesztes(null)} disabled={folyamatban}>
              Mégse
            </Button>
            <Button onPress={ment} loading={folyamatban} disabled={folyamatban || !nev.trim()}>
              Mentés
            </Button>
          </Dialog.Actions>
        </Dialog>

        <Dialog visible={torles !== null} dismissable={false} style={{ maxHeight: '90%' }}>
          <Dialog.Title>„{torles?.nev}” törlése</Dialog.Title>
          <Dialog.ScrollArea style={styles.gorgetes}>
            <ScrollView contentContainerStyle={{ gap: 12, paddingVertical: 8 }}>
              <Text variant="bodyMedium">
                {torles ? darab(torles.id) : 0} tétel (és a hozzá tartozó szabályok, előfizetések) átkerül egy másik kategóriába, a
                költségkeret megszűnik. Melyikbe kerüljenek?
              </Text>
              {celok.length === 0 ? (
                <Text variant="bodySmall">Nincs másik azonos típusú kategória: előbb vegyél fel egyet.</Text>
              ) : (
                <View style={styles.sor}>
                  {celok.map((k) => (
                    <Chip key={k.id} icon={k.ikon || 'tag'} disabled={folyamatban} onPress={() => torol(k)}>
                      {k.nev}
                    </Chip>
                  ))}
                </View>
              )}
            </ScrollView>
          </Dialog.ScrollArea>
          <Dialog.Actions>
            <Button onPress={() => setTorles(null)} disabled={folyamatban}>
              Mégse
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </Card>
  );
}

const styles = StyleSheet.create({
  csoport: { marginTop: 8 },
  sor: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  gorgetes: { paddingHorizontal: 24, maxHeight: 420 },
});
