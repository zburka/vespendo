import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, ScrollView, StyleSheet, View } from 'react-native';
import { Button, Chip, SegmentedButtons, Text, TextInput, useTheme } from 'react-native-paper';

import { kategoriaModositas, tranzakcioModositas, tranzakcioTorles } from '../../services/api';
import { SzemelyValaszto } from '../../components/SzemelyValaszto';
import { useStore } from '../../store/useStore';
import type { FizetesiMod, Tulajdonos } from '../../types';
import { formatFt } from '../../utils/format';
import { azonnaliTetel, kereskedoKulcs } from '../../utils/kereskedo';
import { QvikLogo } from '../../components/QvikLogo';

export default function TranzakcioSzerkeszto() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const theme = useTheme();
  const tranzakcio = useStore((s) => s.tranzakciok.find((t) => t.id === id));
  const kategoriak = useStore((s) => s.kategoriak);
  const modositTranzakcio = useStore((s) => s.modositTranzakcio);
  const modositKategoria = useStore((s) => s.modositKategoria);
  const torolTranzakcioLokal = useStore((s) => s.torolTranzakcioLokal);

  const [nev, setNev] = useState(tranzakcio?.kereskedo ?? '');
  const [osszeg, setOsszeg] = useState(tranzakcio ? String(tranzakcio.osszeg) : '');
  const [datum, setDatum] = useState(tranzakcio?.datum ?? '');
  const [megjegyzes, setMegjegyzes] = useState(tranzakcio?.megjegyzes ?? '');
  const [mod, setMod] = useState<FizetesiMod>(tranzakcio?.fizetesi_mod ?? 'kartya');
  const [kategoriaId, setKategoriaId] = useState(tranzakcio?.kategoria_id ?? '');
  const [tulajdonos, setTulajdonos] = useState<Tulajdonos>(tranzakcio?.tulajdonos ?? 'kozos');
  const [mentes, setMentes] = useState(false);

  if (!tranzakcio) {
    return (
      <View style={styles.container}>
        <Stack.Screen options={{ title: 'Tétel' }} />
        <Text>A tétel nem található.</Text>
      </View>
    );
  }

  const bevetel = tranzakcio.tipus !== 'kiadas';
  const valaszthato = kategoriak.filter(
    (k) => k.tipus === (bevetel ? 'bevetel' : 'kiadas') || k.tipus === 'atvezetes',
  );
  const minta =
    kereskedoKulcs(tranzakcio.kereskedo) ?? tranzakcio.kereskedo.toLowerCase().slice(0, 60);

  const ment = async () => {
    const ertek = Number(osszeg.replace(/[\s ]/g, '').replace(',', '.'));
    if (!nev.trim()) return Alert.alert('Hiba', 'A megnevezés nem lehet üres.');
    if (!isFinite(ertek) || ertek <= 0)
      return Alert.alert('Hiba', 'Az összeg legyen pozitív szám.');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(datum) || isNaN(Date.parse(datum))) {
      return Alert.alert('Hiba', 'A dátum formátuma: ÉÉÉÉ-HH-NN');
    }

    const reszletek = {
      ...(nev.trim() !== tranzakcio.kereskedo && { kereskedo: nev.trim() }),
      ...(ertek !== tranzakcio.osszeg && { osszeg: ertek }),
      ...(datum !== tranzakcio.datum && { datum }),
      ...(megjegyzes !== (tranzakcio.megjegyzes ?? '') && { megjegyzes }),
      ...(mod !== tranzakcio.fizetesi_mod && { fizetesi_mod: mod }),
    };
    const katValtozott = kategoriaId !== tranzakcio.kategoria_id;
    const tulValtozott = tulajdonos !== tranzakcio.tulajdonos;
    if (!Object.keys(reszletek).length && !katValtozott && !tulValtozott) return router.back();

    setMentes(true);
    try {
      if (Object.keys(reszletek).length) {
        await tranzakcioModositas({ id: tranzakcio.id, ...reszletek });
      }
      if (katValtozott || tulValtozott) {
        await kategoriaModositas({
          tranzakcio_id: tranzakcio.id,
          ...(katValtozott && { uj_kategoria_id: kategoriaId, kereskedo_minta: minta }),
          ...(tulValtozott && { uj_tulajdonos: tulajdonos }),
        });
      }
      // helyi állapot (a szerver már elfogadta)
      if (Object.keys(reszletek).length) modositTranzakcio(tranzakcio.id, reszletek);
      if (katValtozott) modositKategoria(tranzakcio.id, kategoriaId);
      if (tulValtozott) modositTranzakcio(tranzakcio.id, { tulajdonos });
      router.back();
    } catch (e) {
      setMentes(false);
      Alert.alert('Mentés', e instanceof Error ? e.message : 'A mentés nem sikerült.');
    }
  };

  const torol = () =>
    Alert.alert(
      'Tétel törlése',
      `Biztosan törlöd: ${tranzakcio.kereskedo}?` +
        (tranzakcio.forras === 'bank_import'
          ? '\n\nFigyelem: ha ugyanazt a kivonatot újra betöltöd, a tétel visszakerülhet.'
          : ''),
      [
        { text: 'Mégse', style: 'cancel' },
        {
          text: 'Törlés',
          style: 'destructive',
          onPress: async () => {
            try {
              await tranzakcioTorles(tranzakcio.id);
              torolTranzakcioLokal(tranzakcio.id);
              router.back();
            } catch (e) {
              Alert.alert('Törlés', e instanceof Error ? e.message : 'A törlés nem sikerült.');
            }
          },
        },
      ],
    );

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
      automaticallyAdjustKeyboardInsets
    >
      <Stack.Screen options={{ title: 'Tétel szerkesztése' }} />
      <View style={styles.osszegSor}>
        <Text variant="headlineSmall">
          {bevetel ? '+' : '−'}
          {formatFt(Number(osszeg.replace(/[\s ]/g, '').replace(',', '.')) || 0)}
        </Text>
        {azonnaliTetel(tranzakcio) && <QvikLogo magassag={30} />}
      </View>

      <TextInput mode="outlined" label="Megnevezés" value={nev} onChangeText={setNev} />
      <TextInput
        mode="outlined"
        label="Összeg (Ft)"
        keyboardType="numeric"
        value={osszeg}
        onChangeText={setOsszeg}
      />
      <TextInput
        mode="outlined"
        label="Dátum (ÉÉÉÉ-HH-NN)"
        value={datum}
        onChangeText={setDatum}
        autoCapitalize="none"
      />
      <TextInput
        mode="outlined"
        label="Megjegyzés"
        value={megjegyzes}
        onChangeText={setMegjegyzes}
        multiline
      />

      <Text variant="titleSmall" style={styles.cim}>
        Fizetési mód
      </Text>
      <SegmentedButtons
        value={mod}
        onValueChange={(v) => setMod(v as FizetesiMod)}
        buttons={[
          { value: 'kartya', label: 'Kártya' },
          { value: 'keszpenz', label: 'Készpénz' },
          { value: 'atutalas', label: 'Átutalás' },
        ]}
      />

      <Text variant="titleSmall" style={styles.cim}>
        Kategória
      </Text>
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
          Mentéskor szabály jön létre: „{minta}” a jövőben ebbe a kategóriába kerül.
        </Text>
      )}

      <Text variant="titleSmall" style={styles.cim}>
        Tulajdonos
      </Text>
      <SzemelyValaszto ertek={tulajdonos} onChange={setTulajdonos} />

      <Button
        mode="contained"
        onPress={ment}
        loading={mentes}
        disabled={mentes}
        style={styles.gomb}
      >
        Mentés
      </Button>
      <Button textColor={theme.colors.error} onPress={torol} disabled={mentes}>
        Tétel törlése
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 8 },
  cim: { marginTop: 12 },
  osszegSor: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  chipek: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  gomb: { marginTop: 24 },
});
