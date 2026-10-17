import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Image, ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Button,
  Card,
  SegmentedButtons,
  Text,
  TextInput,
} from 'react-native-paper';

import { feltoltNyugta } from '../services/api';
import { tomorit } from '../services/kepTomorites';
import { useStore } from '../store/useStore';
import type { NyugtaValasz } from '../types';
import { formatFt } from '../utils/format';

type Fazis = 'szerkesztes' | 'tomorites' | 'feltoltes' | 'kesz' | 'hiba';

const FAZIS_SZOVEG: Partial<Record<Fazis, string>> = {
  tomorites: 'Kép tömörítése…',
  feltoltes: 'Nyugta elemzése…',
};

export default function NyugtaScreen() {
  const { uri, szelesseg } = useLocalSearchParams<{ uri: string; szelesseg: string }>();
  const router = useRouter();
  const kategoriak = useStore((s) => s.kategoriak);
  const hozzaadTranzakcio = useStore((s) => s.hozzaadTranzakcio);

  const [megjegyzes, setMegjegyzes] = useState('');
  const [feltolto, setFeltolto] = useState<'ferj' | 'feleseg'>('ferj');
  const [fazis, setFazis] = useState<Fazis>('szerkesztes');
  const [valasz, setValasz] = useState<NyugtaValasz['data'] | null>(null);
  const [hiba, setHiba] = useState('');

  const kuldes = async () => {
    try {
      setFazis('tomorites');
      const kep_base64 = await tomorit(uri, Number(szelesseg));
      setFazis('feltoltes');
      const { data } = await feltoltNyugta({ kep_base64, megjegyzes, feltolto });

      const fo = [...data.bontott_tetelek].sort((a, b) => b.osszeg - a.osszeg)[0];
      const kategoria = kategoriak.find((k) => k.nev === fo?.kategoria && k.tipus === 'kiadas');
      hozzaadTranzakcio({
        datum: data.datum,
        osszeg: data.osszeg,
        kereskedo: data.kereskedo,
        kategoria_id: kategoria?.id ?? kategoriak.find((k) => k.tipus === 'kiadas')!.id,
        tipus: 'kiadas',
        tulajdonos: feltolto,
        fizetesi_mod: data.fizetesi_mod,
        forras: 'nyugta_foto',
        allapot: data.allapot,
        megjegyzes: megjegyzes || undefined,
        nyugta_kep_url: uri,
      });
      setValasz(data);
      setFazis('kesz');
    } catch (e) {
      setHiba(e instanceof Error ? e.message : 'Ismeretlen hiba');
      setFazis('hiba');
    }
  };

  const folyamatban = fazis === 'tomorites' || fazis === 'feltoltes';

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <Stack.Screen options={{ title: 'Nyugta rögzítése' }} />
      <Image source={{ uri }} style={styles.kep} resizeMode="cover" />

      {folyamatban && (
        <View style={styles.betolto}>
          <ActivityIndicator size="large" />
          <Text variant="bodyLarge">{FAZIS_SZOVEG[fazis]}</Text>
        </View>
      )}

      {(fazis === 'szerkesztes' || fazis === 'hiba') && (
        <>
          <TextInput
            mode="outlined"
            label="Egyéni megjegyzés / Tételbontás (pl. 5000 ruha, 3000 kaja)"
            value={megjegyzes}
            onChangeText={setMegjegyzes}
            multiline
          />
          <Text variant="titleSmall">Ki fizetett?</Text>
          <SegmentedButtons
            value={feltolto}
            onValueChange={(v) => setFeltolto(v as 'ferj' | 'feleseg')}
            buttons={[
              { value: 'ferj', label: 'Férj' },
              { value: 'feleseg', label: 'Feleség' },
            ]}
          />
          {fazis === 'hiba' && <Text style={styles.hiba}>Hiba: {hiba}</Text>}
          <Button mode="contained" icon="send" onPress={kuldes}>
            {fazis === 'hiba' ? 'Újrapróbálás' : 'Küldés'}
          </Button>
        </>
      )}

      {fazis === 'kesz' && valasz && (
        <>
          <Card>
            <Card.Title
              title={valasz.kereskedo}
              subtitle={`${valasz.datum} · ${valasz.fizetesi_mod}`}
            />
            <Card.Content style={styles.tetelek}>
              <Text variant="headlineSmall">{formatFt(valasz.osszeg)}</Text>
              {valasz.bontott_tetelek.map((t) => (
                <Text key={t.kategoria} variant="bodyMedium">
                  {t.kategoria}: {formatFt(t.osszeg)}
                </Text>
              ))}
              <Text variant="bodySmall">Banki egyeztetésre vár.</Text>
            </Card.Content>
          </Card>
          <Button mode="contained" onPress={() => router.back()}>
            Kész
          </Button>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  kep: { width: '100%', height: 260, borderRadius: 12 },
  betolto: { alignItems: 'center', gap: 12, paddingVertical: 24 },
  tetelek: { gap: 4 },
  hiba: { color: '#d32f2f' },
});
