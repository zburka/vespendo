import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { File } from 'expo-file-system';
import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Button,
  Card,
  Divider,
  SegmentedButtons,
  Text,
} from 'react-native-paper';

import { bankiImport, ELO_API, elemezBankiFajl } from '../services/api';
import { dekodol, parseBankiCsv } from '../services/csvParser';
import { useStore } from '../store/useStore';
import type { FajlElemzesValasz, ImportOsszegzes } from '../types';
import { formatFt, formatNap } from '../utils/format';

type Fazis = 'beolvasas' | 'elonezet' | 'kuldes' | 'kesz' | 'hiba';

export default function ImportScreen() {
  const { uri, nev } = useLocalSearchParams<{ uri: string; nev: string }>();
  const router = useRouter();
  const mockBankiImport = useStore((s) => s.mockBankiImport);
  const betoltes = useStore((s) => s.betoltes);

  const [fazis, setFazis] = useState<Fazis>('beolvasas');
  const [csv, setCsv] = useState<NonNullable<FajlElemzesValasz['data']> | null>(null);
  const [feltolto, setFeltolto] = useState<'ferj' | 'feleseg'>(
    useStore.getState().szerep ?? 'ferj',
  );
  const [osszegzes, setOsszegzes] = useState<ImportOsszegzes | null>(null);
  const [hiba, setHiba] = useState('');

  useEffect(() => {
    (async () => {
      try {
        let eredmeny: NonNullable<FajlElemzesValasz['data']>;
        if (ELO_API) {
          // PDF / XLSX / CSV: a szerveroldali elemző kezeli, formátumtól függetlenül
          const fajl_base64 = await new File(uri).base64();
          eredmeny = await elemezBankiFajl({ fajl_nev: nev ?? 'kivonat', fajl_base64 });
        } else {
          if (!/\.csv$/i.test(nev ?? '')) {
            throw new Error(
              'Az app mock módban fut (EXPO_PUBLIC_MOCK=1), ezért csak CSV olvasható. Töröld ezt a beállítást, és indítsd újra az appot.',
            );
          }
          const csv = parseBankiCsv(dekodol(await new File(uri).bytes()));
          eredmeny = { ...csv, megbizhatosag: 'magas', figyelmeztetesek: [] };
        }
        if (eredmeny.tranzakciok.length === 0)
          throw new Error('A fájlban nincs feldolgozható tétel.');
        setCsv(eredmeny);
        setFazis('elonezet');
      } catch (e) {
        setHiba(e instanceof Error ? e.message : 'A fájl beolvasása nem sikerült');
        setFazis('hiba');
      }
    })();
  }, [uri, nev]);

  const kuldes = async () => {
    if (!csv) return;
    const keres = { feltolto, tranzakciok: csv.tranzakciok };
    try {
      setFazis('kuldes');
      const valasz = await bankiImport(keres);
      if (ELO_API) await betoltes();
      setOsszegzes(valasz ?? (ELO_API ? null : mockBankiImport(keres)));
      setFazis('kesz');
    } catch (e) {
      setHiba(e instanceof Error ? e.message : 'Az import nem sikerült');
      setFazis('hiba');
    }
  };

  const kiadas = csv?.tranzakciok.filter((t) => t.irany === 'kiadas') ?? [];
  const bevetel = csv?.tranzakciok.filter((t) => t.irany === 'bevetel') ?? [];
  const sum = (l: typeof kiadas) => l.reduce((s, t) => s + t.osszeg, 0);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Stack.Screen options={{ title: 'Banki import' }} />
      <Text variant="titleMedium">{nev}</Text>

      {(fazis === 'beolvasas' || fazis === 'kuldes') && (
        <View style={styles.betolto}>
          <ActivityIndicator size="large" />
          <Text variant="bodyLarge">
            {fazis === 'beolvasas' ? 'Fájl feldolgozása…' : 'Tételek küldése…'}
          </Text>
        </View>
      )}

      {fazis === 'hiba' && (
        <>
          <Text style={styles.hiba}>{hiba}</Text>
          {csv ? (
            <Button mode="contained" onPress={kuldes}>
              Újrapróbálás
            </Button>
          ) : (
            <Button mode="outlined" onPress={() => router.back()}>
              Vissza
            </Button>
          )}
        </>
      )}

      {fazis === 'elonezet' && csv && (
        <>
          <Card>
            <Card.Content style={styles.osszegzo}>
              <Text variant="bodyLarge">{csv.tranzakciok.length} tétel</Text>
              <Text variant="bodyMedium">
                Kiadás: {kiadas.length} db · {formatFt(sum(kiadas))}
              </Text>
              <Text variant="bodyMedium">
                Bevétel: {bevetel.length} db · {formatFt(sum(bevetel))}
              </Text>
              {csv.kihagyott > 0 && (
                <Text variant="bodySmall">{csv.kihagyott} sor kihagyva (hiányos adat).</Text>
              )}
              {csv.egyenleg_ellenorzes?.egyezik && (
                <Text variant="bodySmall" style={styles.rendben}>
                  ✓ Egyenleg egyezik: {formatFt(csv.egyenleg_ellenorzes.nyito)} →{' '}
                  {formatFt(csv.egyenleg_ellenorzes.zaro)}
                </Text>
              )}
              {csv.megbizhatosag !== 'magas' && (
                <Text variant="bodySmall" style={styles.figyelmeztetes}>
                  Felismerés megbízhatósága:{' '}
                  {csv.megbizhatosag === 'kozepes' ? 'közepes' : 'alacsony'}
                </Text>
              )}
              {csv.figyelmeztetesek.map((f) => (
                <Text key={f} variant="bodySmall" style={styles.figyelmeztetes}>
                  ⚠ {f}
                </Text>
              ))}
            </Card.Content>
          </Card>

          <Card>
            <Card.Title title="Első tételek" />
            <Card.Content>
              {csv.tranzakciok.slice(0, 5).map((t, i) => (
                <View key={i}>
                  {i > 0 && <Divider style={styles.elvalaszto} />}
                  <View style={styles.sor}>
                    <View style={styles.sorBal}>
                      <Text variant="bodyMedium">{t.kereskedo_nyers || '—'}</Text>
                      <Text variant="bodySmall">{formatNap(t.datum)}</Text>
                    </View>
                    <Text variant="bodyMedium">
                      {t.irany === 'kiadas' ? '−' : '+'}
                      {formatFt(t.osszeg)}
                    </Text>
                  </View>
                </View>
              ))}
            </Card.Content>
          </Card>

          <Text variant="titleSmall">Ki töltötte fel?</Text>
          <SegmentedButtons
            value={feltolto}
            onValueChange={(v) => setFeltolto(v as 'ferj' | 'feleseg')}
            buttons={[
              { value: 'ferj', label: 'Férj' },
              { value: 'feleseg', label: 'Feleség' },
            ]}
          />
          <Button mode="contained" icon="upload" onPress={kuldes}>
            Import indítása
          </Button>
        </>
      )}

      {fazis === 'kesz' && (
        <>
          <Card>
            <Card.Title title="Import kész" />
            <Card.Content style={styles.osszegzo}>
              {osszegzes ? (
                <>
                  <Text>Új tétel: {osszegzes.uj}</Text>
                  <Text>Szabállyal besorolva: {osszegzes.szaballyal}</Text>
                  <Text>Nyugtával párosítva: {osszegzes.egyeztetve}</Text>
                  <Text>Ismeretlen (Egyéb kategória): {osszegzes.ismeretlen}</Text>
                  {!!osszegzes.duplikalt && (
                    <Text>Már rögzített, kihagyva: {osszegzes.duplikalt}</Text>
                  )}
                </>
              ) : (
                <Text>A tételeket elküldtük feldolgozásra.</Text>
              )}
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
  betolto: { alignItems: 'center', gap: 12, paddingVertical: 24 },
  osszegzo: { gap: 4 },
  sor: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sorBal: { flex: 1 },
  elvalaszto: { marginVertical: 8 },
  hiba: { color: '#d32f2f' },
  figyelmeztetes: { color: '#b26a00' },
  rendben: { color: '#2e7d32' },
});
