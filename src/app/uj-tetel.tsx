import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, ScrollView, StyleSheet, View } from 'react-native';
import { Button, Chip, SegmentedButtons, Text, TextInput } from 'react-native-paper';

import { ELO_API, ujTranzakcio } from '../services/api';
import { useStore } from '../store/useStore';
import type { FizetesiMod, TranzakcioTipus, Tulajdonos } from '../types';

const maiNap = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export default function UjTetelScreen() {
  const router = useRouter();
  const kategoriak = useStore((s) => s.kategoriak);
  const hozzaadTranzakcio = useStore((s) => s.hozzaadTranzakcio);
  const betoltes = useStore((s) => s.betoltes);
  const setHonap = useStore((s) => s.setHonap);

  const [tipus, setTipus] = useState<'kiadas' | 'bevetel'>('kiadas');
  const [nev, setNev] = useState('');
  const [osszeg, setOsszeg] = useState('');
  const [datum, setDatum] = useState(maiNap());
  const [kategoriaId, setKategoriaId] = useState('');
  const [tulajdonos, setTulajdonos] = useState<Tulajdonos>('kozos');
  const [mod, setMod] = useState<FizetesiMod>('keszpenz');
  const [mentes, setMentes] = useState(false);

  const valaszthato = kategoriak.filter((k) => k.tipus === tipus);
  const aktivKategoria = valaszthato.some((k) => k.id === kategoriaId)
    ? kategoriaId
    : (valaszthato[0]?.id ?? '');

  const ment = async () => {
    const ertek = Number(osszeg.replace(/[\s ]/g, '').replace(',', '.'));
    if (!nev.trim()) return Alert.alert('Hiba', 'Add meg a megnevezést.');
    if (!isFinite(ertek) || ertek <= 0)
      return Alert.alert('Hiba', 'Az összeg legyen pozitív szám.');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(datum) || isNaN(Date.parse(datum))) {
      return Alert.alert('Hiba', 'A dátum formátuma: ÉÉÉÉ-HH-NN');
    }
    if (!aktivKategoria) return Alert.alert('Hiba', 'Válassz kategóriát.');

    const tranzakcioTipus: TranzakcioTipus = tipus === 'kiadas' ? 'kiadas' : 'bevetel_egyszeri';
    setMentes(true);
    try {
      if (ELO_API) {
        await ujTranzakcio({
          osszeg: ertek,
          datum,
          kereskedo: nev.trim(),
          kategoria_id: aktivKategoria,
          tipus: tranzakcioTipus,
          tulajdonos,
          fizetesi_mod: mod,
        });
        await betoltes();
      } else {
        hozzaadTranzakcio({
          datum,
          osszeg: ertek,
          kereskedo: nev.trim(),
          kategoria_id: aktivKategoria,
          tipus: tranzakcioTipus,
          tulajdonos,
          fizetesi_mod: mod,
          forras: 'kezi',
          allapot: 'lezart',
        });
      }
      setHonap(datum.slice(0, 7)); // a rögzített tétel hónapjára ugrik, hogy látszódjon
      router.back();
    } catch (e) {
      setMentes(false);
      Alert.alert('Mentés', e instanceof Error ? e.message : 'A mentés nem sikerült.');
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <SegmentedButtons
        value={tipus}
        onValueChange={(v) => setTipus(v as 'kiadas' | 'bevetel')}
        buttons={[
          { value: 'kiadas', label: 'Kiadás' },
          { value: 'bevetel', label: 'Bevétel' },
        ]}
      />
      <TextInput
        mode="outlined"
        label="Megnevezés (pl. piac, taxi)"
        value={nev}
        onChangeText={setNev}
      />
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

      <Text variant="titleSmall">Kategória</Text>
      <View style={styles.chipek}>
        {valaszthato.map((k) => (
          <Chip
            key={k.id}
            icon={k.ikon}
            selected={k.id === aktivKategoria}
            showSelectedOverlay
            onPress={() => setKategoriaId(k.id)}
          >
            {k.nev}
          </Chip>
        ))}
      </View>

      <Text variant="titleSmall">Tulajdonos</Text>
      <SegmentedButtons
        value={tulajdonos}
        onValueChange={(v) => setTulajdonos(v as Tulajdonos)}
        buttons={[
          { value: 'kozos', label: 'Közös' },
          { value: 'ferj', label: 'Férj' },
          { value: 'feleseg', label: 'Feleség' },
        ]}
      />

      <Text variant="titleSmall">Fizetési mód</Text>
      <SegmentedButtons
        value={mod}
        onValueChange={(v) => setMod(v as FizetesiMod)}
        buttons={[
          { value: 'keszpenz', label: 'Készpénz' },
          { value: 'kartya', label: 'Kártya' },
          { value: 'atutalas', label: 'Átutalás' },
        ]}
      />

      <Button
        mode="contained"
        onPress={ment}
        loading={mentes}
        disabled={mentes}
        style={styles.gomb}
      >
        Mentés
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  chipek: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  gomb: { marginTop: 12 },
});
