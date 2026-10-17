import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useMemo } from 'react';
import { SectionList, StyleSheet, View } from 'react-native';
import { Divider, List, SegmentedButtons, Text, useTheme } from 'react-native-paper';

import { AdatAllapot } from '../../components/AdatAllapot';
import { HonapValaszto } from '../../components/HonapValaszto';
import { type TulajdonosSzuro, useStore } from '../../store/useStore';
import type { Tranzakcio } from '../../types';
import { formatFt, formatNap } from '../../utils/format';

const TULAJDONOS_CIMKE = { kozos: 'Közös', ferj: 'Férj', feleseg: 'Feleség' } as const;

export default function TranzakciokScreen() {
  const theme = useTheme();
  const router = useRouter();
  const honap = useStore((s) => s.honap);
  const szuro = useStore((s) => s.szuro);
  const setSzuro = useStore((s) => s.setSzuro);
  const tranzakciok = useStore((s) => s.tranzakciok);
  const kategoriak = useStore((s) => s.kategoriak);
  const toltes = useStore((s) => s.toltes);
  const betoltes = useStore((s) => s.betoltes);

  const szekciok = useMemo(() => {
    const lista = tranzakciok
      .filter((t) => t.datum.startsWith(honap) && (szuro === 'mind' || t.tulajdonos === szuro))
      .sort((a, b) => b.datum.localeCompare(a.datum));
    const csoportok = new Map<string, Tranzakcio[]>();
    for (const t of lista) csoportok.set(t.datum, [...(csoportok.get(t.datum) ?? []), t]);
    return [...csoportok].map(([datum, data]) => ({ title: formatNap(datum), data }));
  }, [tranzakciok, honap, szuro]);

  return (
    <View style={styles.container}>
      <View style={styles.fejlec}>
        <HonapValaszto />
        <AdatAllapot />
        <SegmentedButtons
          value={szuro}
          onValueChange={(v) => setSzuro(v as TulajdonosSzuro)}
          buttons={[
            { value: 'mind', label: 'Mind' },
            { value: 'kozos', label: 'Közös' },
            { value: 'ferj', label: 'Férj' },
            { value: 'feleseg', label: 'Feleség' },
          ]}
        />
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
              title={item.kereskedo}
              description={`${kat?.nev ?? '?'} · ${TULAJDONOS_CIMKE[item.tulajdonos]}${
                item.fizetesi_mod === 'keszpenz' ? ' · készpénz' : ''
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
                <Text
                  variant="bodyLarge"
                  style={{
                    color: bevetel ? '#2e7d32' : theme.colors.onSurface,
                    alignSelf: 'center',
                  }}
                >
                  {bevetel ? '+' : '−'}
                  {formatFt(item.osszeg)}
                </Text>
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
  szekcio: { paddingHorizontal: 16, paddingVertical: 6 },
  ikon: { alignSelf: 'center', marginLeft: 8 },
  ures: { textAlign: 'center', marginTop: 32 },
});
