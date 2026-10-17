import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useMemo } from 'react';
import { SectionList, StyleSheet, View } from 'react-native';
import { Chip, Divider, List, Text, useTheme } from 'react-native-paper';

import { AdatAllapot } from '../../components/AdatAllapot';
import { HonapValaszto } from '../../components/HonapValaszto';
import { QvikLogo } from '../../components/QvikLogo';
import { SzemelyValaszto } from '../../components/SzemelyValaszto';
import { useStore } from '../../store/useStore';
import type { Tranzakcio } from '../../types';
import { formatFt, formatNap } from '../../utils/format';
import { azonnaliTetel, devizaInfo, megjelenitettNev } from '../../utils/kereskedo';
import { szemelyNev } from '../../utils/szemely';

export default function TranzakciokScreen() {
  const theme = useTheme();
  const router = useRouter();
  const honap = useStore((s) => s.honap);
  const szuro = useStore((s) => s.szuro);
  const setSzuro = useStore((s) => s.setSzuro);
  const tranzakciok = useStore((s) => s.tranzakciok);
  const szemelyek = useStore((s) => s.szemelyek);
  const kategoriaSzuro = useStore((s) => s.kategoriaSzuro);
  const setKategoriaSzuro = useStore((s) => s.setKategoriaSzuro);
  const kategoriak = useStore((s) => s.kategoriak);
  const toltes = useStore((s) => s.toltes);
  const betoltes = useStore((s) => s.betoltes);

  const szekciok = useMemo(() => {
    const lista = tranzakciok
      .filter(
        (t) =>
          t.datum.startsWith(honap) &&
          (szuro === 'mind' || t.tulajdonos === szuro) &&
          (!kategoriaSzuro || t.kategoria_id === kategoriaSzuro),
      )
      .sort((a, b) => b.datum.localeCompare(a.datum));
    const csoportok = new Map<string, Tranzakcio[]>();
    for (const t of lista) csoportok.set(t.datum, [...(csoportok.get(t.datum) ?? []), t]);
    return [...csoportok].map(([datum, data]) => ({ title: formatNap(datum), data }));
  }, [tranzakciok, honap, szuro, kategoriaSzuro]);
  const szuroKategoria = kategoriak.find((k) => k.id === kategoriaSzuro);

  return (
    <View style={styles.container}>
      <View style={styles.fejlec}>
        <HonapValaszto />
        <AdatAllapot />
        <SzemelyValaszto ertek={szuro} onChange={setSzuro} mind />
        {szuroKategoria && (
          <View style={styles.szuroSor}>
            <Chip icon="filter" onClose={() => setKategoriaSzuro(null)}>
              Kategória: {szuroKategoria.nev}
            </Chip>
          </View>
        )}
      </View>
      <SectionList
        sections={szekciok}
        keyExtractor={(t) => t.id}
        stickySectionHeadersEnabled
        refreshing={toltes}
        onRefresh={betoltes}
        ItemSeparatorComponent={Divider}
        ListEmptyComponent={<Text style={styles.ures}>Nincs tétel ebben a hónapban.</Text>}
        renderSectionHeader={({ section }) => (
          <Text
            variant="labelLarge"
            style={[styles.szekcio, { backgroundColor: theme.colors.background }]}
          >
            {section.title}
          </Text>
        )}
        renderItem={({ item }) => {
          const kat = kategoriak.find((k) => k.id === item.kategoria_id);
          const bevetel = item.tipus !== 'kiadas';
          return (
            <List.Item
              title={megjelenitettNev(item.kereskedo)}
              description={`${kat?.nev ?? '?'} · ${szemelyNev(szemelyek, item.tulajdonos)}${
                item.fizetesi_mod === 'keszpenz' ? ' · készpénz' : ''
              }${
                devizaInfo(item.kereskedo, item.megjegyzes)
                  ? ` · ${devizaInfo(item.kereskedo, item.megjegyzes)}`
                  : ''
              }${item.allapot === 'banki_egyeztetesre_var' ? ' · egyeztetésre vár' : ''}`}
              left={(p) => (
                <Ionicons
                  name={bevetel ? 'arrow-down-circle' : 'arrow-up-circle'}
                  size={28}
                  color={bevetel ? '#2e7d32' : p.color}
                  style={styles.ikon}
                />
              )}
              right={() => (
                <View style={styles.osszegOszlop}>
                  <Text
                    variant="bodyLarge"
                    style={{ color: bevetel ? '#2e7d32' : theme.colors.onSurface }}
                  >
                    {bevetel ? '+' : '−'}
                    {formatFt(item.osszeg)}
                  </Text>
                  {azonnaliTetel(item) && <QvikLogo />}
                </View>
              )}
              onPress={() => router.push(`/tranzakcio/${item.id}`)}
            />
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  fejlec: { padding: 16, paddingBottom: 8, gap: 8 },
  szuroSor: { flexDirection: 'row' },
  osszegOszlop: { alignItems: 'flex-end', justifyContent: 'center', gap: 4 },
  szekcio: { paddingHorizontal: 16, paddingVertical: 6 },
  ikon: { alignSelf: 'center', marginLeft: 8 },
  ures: { textAlign: 'center', marginTop: 32 },
});
