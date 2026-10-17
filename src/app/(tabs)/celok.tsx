import { Ionicons } from '@expo/vector-icons';
import { useMemo, useState } from 'react';
import { Keyboard, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Alert } from '../../utils/uzenet';
import {
  Button,
  Card,
  Chip,
  Dialog,
  Divider,
  List,
  Portal,
  ProgressBar,
  Switch,
  Text,
  TextInput,
  useTheme,
} from 'react-native-paper';

import { AdatAllapot } from '../../components/AdatAllapot';
import { useKeyboardHeight } from '../../hooks/useKeyboardHeight';
import { useStore } from '../../store/useStore';
import type { Elofizetes, Kategoria, MegtakaritasiCel } from '../../types';
import { type ElofizetesJavaslat, elofizetesJavaslatok } from '../../utils/elofizetes';
import { formatFt } from '../../utils/format';

type Szerkesztes =
  | { tipus: 'cel'; cel?: MegtakaritasiCel }
  | { tipus: 'keret'; kategoria: Kategoria }
  | { tipus: 'elofizetes'; ef?: Elofizetes }
  | null;

/** '12 000', '12000,5' -> szám; érvénytelen esetén NaN */
const szam = (s: string) => Number(s.replace(/[\s ]/g, '').replace(',', '.'));

export default function CelokScreen() {
  const theme = useTheme();
  const celok = useStore((s) => s.celok);
  const keretek = useStore((s) => s.keretek);
  const kategoriak = useStore((s) => s.kategoriak);
  const mentKeret = useStore((s) => s.mentKeret);
  const mentCel = useStore((s) => s.mentCel);
  const torolCel = useStore((s) => s.torolCel);
  const elofizetesek = useStore((s) => s.elofizetesek);
  const tranzakciok = useStore((s) => s.tranzakciok);
  const elutasitott = useStore((s) => s.elutasitott);
  const elvetJavaslat = useStore((s) => s.elvetJavaslat);
  const mentElofizetes = useStore((s) => s.mentElofizetes);
  const torolElofizetes = useStore((s) => s.torolElofizetes);

  const [szerkesztes, setSzerkesztes] = useState<Szerkesztes>(null);
  const [nev, setNev] = useState('');
  const [osszeg, setOsszeg] = useState('');
  const [aktualis, setAktualis] = useState('');
  const [aktiv, setAktiv] = useState(true);
  const [nap, setNap] = useState('');
  const [efKategoria, setEfKategoria] = useState('');
  const [mentes, setMentes] = useState(false);
  const billentyuzet = useKeyboardHeight();

  const kiadasKategoriak = kategoriak.filter((k) => k.tipus === 'kiadas');
  const javaslatok = useMemo(
    () => elofizetesJavaslatok(tranzakciok, kategoriak, elofizetesek, elutasitott),
    [tranzakciok, kategoriak, elofizetesek, elutasitott],
  );

  const megnyitCel = (cel?: MegtakaritasiCel) => {
    setNev(cel?.cel_neve ?? '');
    setOsszeg(cel ? String(cel.celosszeg) : '');
    setAktualis(cel ? String(cel.aktualis_osszeg) : '0');
    setSzerkesztes({ tipus: 'cel', cel });
  };
  // a javaslat az űrlapot előre kitölti, a mentés előtt módosítható
  const megnyitEf = (ef?: Elofizetes, javaslat?: ElofizetesJavaslat) => {
    setNev(ef?.megnevezes ?? javaslat?.nev ?? '');
    setOsszeg(ef ? String(ef.varhato_osszeg) : javaslat ? String(javaslat.osszeg) : '');
    setNap(ef ? String(ef.esedekesseg_napja) : javaslat ? String(javaslat.nap) : '1');
    setEfKategoria(
      ef?.kategoria_id ??
        javaslat?.kategoria_id ??
        kategoriak.find((k) => k.nev === 'Előfizetés')?.id ??
        kiadasKategoriak[0]?.id ??
        '',
    );
    setSzerkesztes({ tipus: 'elofizetes', ef });
  };
  const megnyitKeret = (kategoria: Kategoria) => {
    const keret = keretek.find((k) => k.kategoria_id === kategoria.id);
    setOsszeg(keret ? String(keret.havi_keret) : '');
    setAktiv(keret?.aktiv ?? true);
    setSzerkesztes({ tipus: 'keret', kategoria });
  };

  const bezar = () => !mentes && setSzerkesztes(null);

  const ment = async () => {
    if (!szerkesztes) return;
    const ertek = szam(osszeg);
    try {
      if (szerkesztes.tipus === 'keret') {
        if (!isFinite(ertek) || ertek < 0) return Alert.alert('Hiba', 'Adj meg érvényes összeget.');
        setMentes(true);
        await mentKeret(szerkesztes.kategoria.id, szerkesztes.kategoria.nev, ertek, aktiv);
      } else if (szerkesztes.tipus === 'elofizetes') {
        const napSzam = Number(nap);
        if (!nev.trim()) return Alert.alert('Hiba', 'Add meg az előfizetés nevét.');
        if (!isFinite(ertek) || ertek <= 0) return Alert.alert('Hiba', 'Az összeg legyen pozitív.');
        if (!Number.isInteger(napSzam) || napSzam < 1 || napSzam > 31) {
          return Alert.alert('Hiba', 'Az esedékesség napja 1 és 31 közötti szám legyen.');
        }
        if (!efKategoria) return Alert.alert('Hiba', 'Válassz kategóriát.');
        setMentes(true);
        await mentElofizetes({
          id: szerkesztes.ef?.id,
          megnevezes: nev.trim(),
          varhato_osszeg: ertek,
          esedekesseg_napja: napSzam,
          kategoria_id: efKategoria,
        });
      } else {
        const akt = szam(aktualis);
        if (!nev.trim()) return Alert.alert('Hiba', 'Add meg a cél nevét.');
        if (!isFinite(ertek) || ertek <= 0)
          return Alert.alert('Hiba', 'A célösszeg legyen pozitív.');
        if (!isFinite(akt) || akt < 0) return Alert.alert('Hiba', 'Érvénytelen aktuális összeg.');
        setMentes(true);
        await mentCel({
          id: szerkesztes.cel?.id,
          cel_neve: nev.trim(),
          celosszeg: ertek,
          aktualis_osszeg: akt,
        });
      }
      setMentes(false);
      setSzerkesztes(null);
    } catch (e) {
      setMentes(false);
      Alert.alert('Mentés', e instanceof Error ? e.message : 'A mentés nem sikerült.');
    }
  };

  const torolEf = (ef: Elofizetes) =>
    Alert.alert('Előfizetés törlése', `Biztosan törlöd: ${ef.megnevezes}?`, [
      { text: 'Mégse', style: 'cancel' },
      {
        text: 'Törlés',
        style: 'destructive',
        onPress: () =>
          torolElofizetes(ef.id).catch((e) =>
            Alert.alert('Törlés', e instanceof Error ? e.message : 'A törlés nem sikerült.'),
          ),
      },
    ]);

  const torol = (cel: MegtakaritasiCel) =>
    Alert.alert('Cél törlése', `Biztosan törlöd: ${cel.cel_neve}?`, [
      { text: 'Mégse', style: 'cancel' },
      {
        text: 'Törlés',
        style: 'destructive',
        onPress: () =>
          torolCel(cel.id).catch((e) =>
            Alert.alert('Törlés', e instanceof Error ? e.message : 'A törlés nem sikerült.'),
          ),
      },
    ]);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <AdatAllapot />

      <View style={styles.fejlec}>
        <Text variant="titleLarge">Megtakarítási célok</Text>
        <Button icon="plus" mode="text" onPress={() => megnyitCel()}>
          Új cél
        </Button>
      </View>
      {celok.length === 0 && <Text variant="bodyMedium">Még nincs megtakarítási cél.</Text>}
      {celok.map((c) => {
        const arany = c.celosszeg > 0 ? c.aktualis_osszeg / c.celosszeg : 0;
        return (
          <Card key={c.id}>
            <Card.Title title={c.cel_neve} subtitle={`${Math.round(arany * 100)}%`} />
            <Card.Content style={styles.kartyaTartalom}>
              <ProgressBar progress={Math.min(arany, 1)} style={styles.sav} />
              <Text variant="bodyMedium">
                {formatFt(c.aktualis_osszeg)} / {formatFt(c.celosszeg)}
              </Text>
            </Card.Content>
            <Card.Actions>
              <Button onPress={() => torol(c)} textColor={theme.colors.error}>
                Törlés
              </Button>
              <Button onPress={() => megnyitCel(c)}>Szerkesztés</Button>
            </Card.Actions>
          </Card>
        );
      })}

      <View style={[styles.fejlec, styles.szekcio]}>
        <Text variant="titleLarge">Fix előfizetések</Text>
        <Button icon="plus" mode="text" onPress={() => megnyitEf()}>
          Új előfizetés
        </Button>
      </View>
      {javaslatok.length > 0 && (
        <Card mode="outlined">
          <Card.Title
            title="Javaslatok a tranzakciókból"
            subtitle="Havonta ismétlődő, azonos összegű tételek"
            left={(p) => (
              <Ionicons name="bulb-outline" size={p.size} color={theme.colors.primary} />
            )}
          />
          <Card.Content>
            {javaslatok.map((j, i) => (
              <View key={j.kulcs}>
                {i > 0 && <Divider style={styles.elvalaszto} />}
                <Text variant="bodyLarge">{j.nev}</Text>
                <Text variant="bodySmall">
                  ~{formatFt(j.osszeg)} · minden hónap {j.nap}. napja körül · {j.honapok} hónapban ·{' '}
                  {kategoriak.find((k) => k.id === j.kategoria_id)?.nev ?? ''}
                </Text>
                <View style={styles.javaslatGombok}>
                  <Button compact onPress={() => elvetJavaslat(j.kulcs)}>
                    Elvetés
                  </Button>
                  <Button compact mode="contained-tonal" onPress={() => megnyitEf(undefined, j)}>
                    Hozzáadás
                  </Button>
                </View>
              </View>
            ))}
          </Card.Content>
        </Card>
      )}
      {elofizetesek.length === 0 && javaslatok.length === 0 && (
        <Text variant="bodyMedium">Még nincs előfizetés felvéve.</Text>
      )}
      {elofizetesek.map((ef) => (
        <Card key={ef.id}>
          <Card.Title
            title={ef.megnevezes}
            subtitle={`${formatFt(ef.varhato_osszeg)} · minden hónap ${ef.esedekesseg_napja}. napján`}
          />
          <Card.Actions>
            <Button onPress={() => torolEf(ef)} textColor={theme.colors.error}>
              Törlés
            </Button>
            <Button onPress={() => megnyitEf(ef)}>Szerkesztés</Button>
          </Card.Actions>
        </Card>
      ))}

      <Text variant="titleLarge" style={styles.szekcio}>
        Költségkeretek
      </Text>
      <Card>
        {kiadasKategoriak.map((k, i) => {
          const keret = keretek.find((x) => x.kategoria_id === k.id);
          return (
            <View key={k.id}>
              {i > 0 && <Divider />}
              <List.Item
                title={k.nev}
                description={
                  keret
                    ? `${formatFt(keret.havi_keret)} / hó${keret.aktiv ? '' : ' (kikapcsolva)'}`
                    : 'Nincs keret'
                }
                right={(p) => <List.Icon {...p} icon="pencil" />}
                onPress={() => megnyitKeret(k)}
              />
            </View>
          );
        })}
      </Card>

      <Portal>
        <Dialog
          visible={szerkesztes !== null}
          dismissable={false}
          onDismiss={bezar}
          style={{ marginBottom: billentyuzet }}
        >
          <Dialog.Title>
            {szerkesztes?.tipus === 'keret'
              ? `Keret: ${szerkesztes.kategoria.nev}`
              : szerkesztes?.tipus === 'elofizetes'
                ? szerkesztes.ef
                  ? 'Előfizetés szerkesztése'
                  : 'Új előfizetés'
                : szerkesztes?.cel
                  ? 'Cél szerkesztése'
                  : 'Új cél'}
          </Dialog.Title>
          <Dialog.Content>
            <Pressable onPress={Keyboard.dismiss} style={styles.dialogus}>
              {szerkesztes?.tipus === 'cel' && (
                <TextInput mode="outlined" label="Cél neve" value={nev} onChangeText={setNev} />
              )}
              {szerkesztes?.tipus === 'elofizetes' && (
                <TextInput mode="outlined" label="Megnevezés" value={nev} onChangeText={setNev} />
              )}
              <TextInput
                mode="outlined"
                label={
                  szerkesztes?.tipus === 'keret'
                    ? 'Havi keret (Ft)'
                    : szerkesztes?.tipus === 'elofizetes'
                      ? 'Havi összeg (Ft)'
                      : 'Célösszeg (Ft)'
                }
                keyboardType="numeric"
                value={osszeg}
                onChangeText={setOsszeg}
              />
              {szerkesztes?.tipus === 'cel' && (
                <TextInput
                  mode="outlined"
                  label="Eddig megtakarítva (Ft)"
                  keyboardType="numeric"
                  value={aktualis}
                  onChangeText={setAktualis}
                />
              )}
              {szerkesztes?.tipus === 'elofizetes' && (
                <>
                  <TextInput
                    mode="outlined"
                    label="Esedékesség napja (1–31)"
                    keyboardType="numeric"
                    value={nap}
                    onChangeText={setNap}
                  />
                  <View style={styles.chipek}>
                    {kiadasKategoriak.map((k) => (
                      <Chip
                        key={k.id}
                        selected={k.id === efKategoria}
                        showSelectedOverlay
                        onPress={() => setEfKategoria(k.id)}
                      >
                        {k.nev}
                      </Chip>
                    ))}
                  </View>
                </>
              )}
              {szerkesztes?.tipus === 'keret' && (
                <View style={styles.kapcsolo}>
                  <Text variant="bodyLarge">Aktív</Text>
                  <Switch value={aktiv} onValueChange={setAktiv} />
                </View>
              )}
            </Pressable>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={bezar} disabled={mentes}>
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
  fejlec: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  szekcio: { marginTop: 12 },
  kartyaTartalom: { gap: 8 },
  sav: { height: 10, borderRadius: 5 },
  dialogus: { gap: 12 },
  chipek: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  elvalaszto: { marginVertical: 10 },
  javaslatGombok: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 4 },
  kapcsolo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
});
