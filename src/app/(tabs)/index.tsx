import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Card, ProgressBar, Text, useTheme } from 'react-native-paper';

import { HonapValaszto } from '../../components/HonapValaszto';
import { useHaviOsszesito } from '../../hooks/useHaviOsszesito';
import { formatFt, keretSzin } from '../../utils/format';

export default function DashboardScreen() {
  const theme = useTheme();
  const { osszesito: o, hiba, betolt } = useHaviOsszesito();

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <HonapValaszto />
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
          title="AI pénzügyi elemzés"
          left={(p) => <Ionicons name="sparkles" size={p.size} color={theme.colors.primary} />}
        />
        <Card.Content>
          <Text variant="bodyMedium">{o.ai_elemzes}</Text>
        </Card.Content>
      </Card>

      <Card>
        <Card.Title title="Költségkeretek" />
        <Card.Content style={styles.lista}>
          {o.keretek.map((k) => (
            <View key={k.kategoria} style={styles.keret}>
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
