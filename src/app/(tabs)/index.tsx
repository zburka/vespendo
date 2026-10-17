import { Ionicons } from '@expo/vector-icons';
import { useMemo } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ActivityIndicator, Button, Card, ProgressBar, Text, useTheme } from 'react-native-paper';

import { AdatAllapot } from '../../components/AdatAllapot';
import { HonapValaszto } from '../../components/HonapValaszto';
import { useStore } from '../../store/useStore';
import { useHaviOsszesito } from '../../hooks/useHaviOsszesito';
import { formatFt, keretSzin } from '../../utils/format';
import { keszpenzAllapot } from '../../utils/osszesito';

export default function DashboardScreen() {
  const theme = useTheme();
  const { osszesito: o, hiba, betolt } = useHaviOsszesito();
  const router = useRouter();
  const tranzakciok = useStore((s) => s.tranzakciok);
  const keszpenz = useMemo(() => keszpenzAllapot(tranzakciok), [tranzakciok]);
  const honap = useStore((s) => s.honap);
  const kategoriak = useStore((s) => s.kategoriak);
  const szemelyek = useStore((s) => s.szemelyek);
  const setSzuro = useStore((s) => s.setSzuro);
  const setKategoriaSzuro = useStore((s) => s.setKategoriaSzuro);

  // a hónap kiadásai kategóriánként (a lista alapja a kategóriára szűréshez)
  const kategoriaBontas = useMemo(() => {
    const osszegek = new Map<string, number>();
    for (const t of tranzakciok) {
      if (t.tipus === 'kiadas' && t.datum.startsWith(honap)) {
        osszegek.set(t.kategoria_id, (osszegek.get(t.kategoria_id) ?? 0) + t.osszeg);
      }
    }
    return [...osszegek]
      .map(([id, osszeg]) => ({ id, nev: kategoriak.find((k) => k.id === id)?.nev ?? '?', osszeg }))
      .sort((a, b) => b.osszeg - a.osszeg);
  }, [tranzakciok, honap, kategoriak]);
  const kategoriaOsszeg = kategoriaBontas.reduce((s, k) => s + k.osszeg, 0);

  const bontas: Record<string, number> = o.bontas_szemely_szerint ?? {};
  const szemelySorok = [
    ...szemelyek.filter((p) => p.aktiv || (bontas[p.kulcs] ?? 0) > 0),
    ...Object.keys(bontas)
      .filter((kulcs) => !szemelyek.some((p) => p.kulcs === kulcs))
      .map((kulcs) => ({ kulcs, nev: kulcs, aktiv: true })),
  ];

  const szuresKategoriara = (id?: string) => {
    if (!id) return;
    setSzuro('mind');
    setKategoriaSzuro(id);
    router.navigate('/tranzakciok');
  };
  const szuresSzemelyre = (kulcs: string) => {
    setKategoriaSzuro(null);
    setSzuro(kulcs);
    router.navigate('/tranzakciok');
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <HonapValaszto />
      <AdatAllapot />
      {betolt && <ActivityIndicator />}
      {hiba && (
        <Text variant="bodySmall" style={{ color: theme.colors.error }}>
          Az élő adatok nem érhetők el, helyi adatokat látsz.
        </Text>
      )}

      <View style={styles.sor}>
        <OsszegKartya cim="Bevétel" ertek={o.osszes_bevetel} szin="#2e7d32" />
        <OsszegKartya cim="Kiadás" ertek={o.osszes_kiadas} szin="#d32f2f" />
      </View>
      <OsszegKartya
        cim="Maradvány"
        ertek={o.egyenleg}
        szin={o.egyenleg >= 0 ? '#2e7d32' : '#d32f2f'}
      />

      <Card>
        <Card.Title
          title="Készpénz"
          left={(p) => <Ionicons name="wallet" size={p.size} color={theme.colors.primary} />}
        />
        <Card.Content>
          <Text
            variant="headlineSmall"
            style={{ color: keszpenz.egyenleg >= 0 ? '#2e7d32' : '#d32f2f' }}
          >
            {formatFt(keszpenz.egyenleg)}
          </Text>
          <Text variant="bodySmall">
            Kapott: {formatFt(keszpenz.bevetel)} · Elköltött: {formatFt(keszpenz.kiadas)}
          </Text>
        </Card.Content>
        <Card.Actions>
          <Button
            icon="cash-plus"
            onPress={() => router.push('/uj-tetel?tipus=bevetel&mod=keszpenz')}
          >
            Kapott készpénz
          </Button>
          <Button
            icon="cash-minus"
            onPress={() => router.push('/uj-tetel?tipus=kiadas&mod=keszpenz')}
          >
            Készpénzes kiadás
          </Button>
        </Card.Actions>
      </Card>

      <Card>
        <Card.Title title="Kiadások tulajdonos szerint" />
        <Card.Content style={styles.lista}>
          {szemelySorok.map((p) => {
            const ertek = bontas[p.kulcs] ?? 0;
            return (
              <Pressable key={p.kulcs} onPress={() => szuresSzemelyre(p.kulcs)}>
                <View style={styles.keret}>
                  <View style={styles.keretFejlec}>
                    <Text variant="bodyLarge">{p.nev}</Text>
                    <Text variant="bodySmall">{formatFt(ertek)}</Text>
                  </View>
                  <ProgressBar
                    progress={o.osszes_kiadas > 0 ? ertek / o.osszes_kiadas : 0}
                    style={styles.sav}
                  />
                </View>
              </Pressable>
            );
          })}
        </Card.Content>
      </Card>

      <Card>
        <Card.Title
          title="Kiadások kategóriánként"
          subtitle="Koppints egy kategóriára a tételek megtekintéséhez"
        />
        <Card.Content style={styles.lista}>
          {kategoriaBontas.length === 0 && (
            <Text variant="bodyMedium">Ebben a hónapban nincs kiadás.</Text>
          )}
          {kategoriaBontas.map((k) => (
            <Pressable key={k.id} onPress={() => szuresKategoriara(k.id)}>
              <View style={styles.keret}>
                <View style={styles.keretFejlec}>
                  <Text variant="bodyLarge">{k.nev}</Text>
                  <Text variant="bodySmall">{formatFt(k.osszeg)}</Text>
                </View>
                <ProgressBar
                  progress={kategoriaOsszeg > 0 ? k.osszeg / kategoriaOsszeg : 0}
                  style={styles.sav}
                />
              </View>
            </Pressable>
          ))}
        </Card.Content>
      </Card>

      <Card>
        <Card.Title
          title="AI pénzügyi elemzés"
          left={(p) => <Ionicons name="sparkles" size={p.size} color={theme.colors.primary} />}
        />
        <Card.Content>
          <Text variant="bodyMedium">
            {o.ai_elemzes || 'Az AI elemzés ehhez a hónaphoz még nem érhető el.'}
          </Text>
        </Card.Content>
      </Card>

      <Card>
        <Card.Title title="Költségkeretek" />
        <Card.Content style={styles.lista}>
          {o.keretek.map((k) => (
            <Pressable
              key={k.kategoria}
              onPress={() => szuresKategoriara(kategoriak.find((c) => c.nev === k.kategoria)?.id)}
            >
              <View style={styles.keret}>
                <View style={styles.keretFejlec}>
                  <Text variant="bodyLarge">{k.kategoria}</Text>
                  <Text variant="bodySmall">
                    {formatFt(k.elkoltve)} / {formatFt(k.havi_keret)} ({k.szazalek}%)
                  </Text>
                </View>
                <ProgressBar
                  progress={Math.min(k.szazalek / 100, 1)}
                  color={keretSzin(k.szazalek)}
                  style={styles.sav}
                />
              </View>
            </Pressable>
          ))}
        </Card.Content>
      </Card>

      <Card>
        <Card.Title
          title="Fix előfizetések"
          subtitle={`Várható hátralévő: ${formatFt(o.varhato_hatralevo_elofizetesek)}`}
        />
        <Card.Content style={styles.lista}>
          {(o.elofizetesek ?? []).map((e) => (
            <View key={e.id} style={styles.elofizetes}>
              <Ionicons
                name={e.kifizetve ? 'checkmark-circle' : 'time-outline'}
                size={22}
                color={e.kifizetve ? '#2e7d32' : theme.colors.outline}
              />
              <View style={styles.elofizetesNev}>
                <Text variant="bodyLarge">{e.megnevezes}</Text>
                <Text variant="bodySmall">
                  {e.kifizetve ? 'Kifizetve' : `Esedékes: ${e.esedekesseg_napja}.`}
                </Text>
              </View>
              <Text variant="bodyMedium">{formatFt(e.varhato_osszeg)}</Text>
            </View>
          ))}
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

function OsszegKartya({ cim, ertek, szin }: { cim: string; ertek: number; szin: string }) {
  return (
    <Card style={styles.osszegKartya}>
      <Card.Content>
        <Text variant="labelMedium">{cim}</Text>
        <Text variant="titleMedium" style={{ color: szin }}>
          {formatFt(ertek)}
        </Text>
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  sor: { flexDirection: 'row', gap: 12 },
  osszegKartya: { flex: 1 },
  lista: { gap: 12 },
  keret: { gap: 4 },
  keretFejlec: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  sav: { height: 8, borderRadius: 4 },
  elofizetes: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  elofizetesNev: { flex: 1 },
});
