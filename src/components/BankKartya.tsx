import * as WebBrowser from 'expo-web-browser';
import { useCallback, useEffect, useState } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { Alert } from '../utils/uzenet';
import { Button, Card, Divider, Text, useTheme } from 'react-native-paper';

import {
  type BankKapcsolat,
  bankAllapot,
  bankOsszekotes,
  bankSzinkron,
  ELO_API,
} from '../services/api';
import { useStore } from '../store/useStore';

/** Banki összekötés (Enable Banking): személyenként a bank jóváhagyása, állapot, lejárat, kézi szinkron. */
export function BankKartya() {
  const theme = useTheme();
  const szemelyek = useStore((s) => s.szemelyek);
  const betoltes = useStore((s) => s.betoltes);
  const [kapcsolatok, setKapcsolatok] = useState<BankKapcsolat[]>([]);
  const [hiba, setHiba] = useState<string | null>(null);
  const [folyamatban, setFolyamatban] = useState<string | null>(null);

  const frissit = useCallback(async () => {
    try {
      setKapcsolatok(await bankAllapot());
      setHiba(null);
    } catch (e) {
      setHiba(e instanceof Error ? e.message : 'Az állapot nem érhető el');
    }
  }, []);

  useEffect(() => {
    let megszakitva = false;
    bankAllapot()
      .then((k) => !megszakitva && (setKapcsolatok(k), setHiba(null)))
      .catch(
        (e) => !megszakitva && setHiba(e instanceof Error ? e.message : 'Az állapot nem érhető el'),
      );
    return () => {
      megszakitva = true;
    };
  }, []);

  if (!ELO_API) return null;

  const osszekot = async (szemely: string) => {
    setFolyamatban(szemely);
    try {
      const url = await bankOsszekotes(szemely);
      // A bejelentkezés az OTP-appban hagyható jóvá; a böngészőből visszatérve az állapot frissül.
      if (Platform.OS === 'web') {
        window.location.assign(url);
        return;
      }
      await WebBrowser.openBrowserAsync(url);
      await frissit();
    } catch (e) {
      Alert.alert('Összekötés', e instanceof Error ? e.message : 'Az összekötés nem indítható.');
    }
    setFolyamatban(null);
  };

  const szinkron = async () => {
    setFolyamatban('szinkron');
    try {
      const eredmeny = await bankSzinkron();
      await Promise.all([betoltes(), frissit()]);
      const uj = eredmeny.reduce((s, e) => s + e.uj, 0);
      const hibak = eredmeny.filter((e) => !e.ok);
      Alert.alert(
        'Szinkron kész',
        eredmeny.length === 0
          ? 'Nincs aktív banki kapcsolat.'
          : `${uj} új tétel.` +
              (hibak.length ? `\n\nHiba: ${hibak.map((h) => h.hiba).join('; ')}` : ''),
      );
    } catch (e) {
      Alert.alert('Szinkron', e instanceof Error ? e.message : 'A szinkron nem sikerült.');
    }
    setFolyamatban(null);
  };

  const emberek = szemelyek.filter((p) => p.aktiv && p.kulcs !== 'kozos');

  return (
    <Card>
      <Card.Title
        title="Banki összekötés"
        subtitle="Automatikus tételletöltés az OTP-ből (az engedély időszakosan lejár)"
      />
      <Card.Content>
        {hiba && <Text style={{ color: theme.colors.error }}>{hiba}</Text>}
        {emberek.map((p, i) => {
          const sajat = kapcsolatok.filter((k) => k.szemely === p.kulcs);
          const lejarGyorsan = sajat.some((k) => k.lejart || (k.napok_hatra ?? 999) <= 14);
          return (
            <View key={p.kulcs}>
              {i > 0 && <Divider style={styles.elvalaszto} />}
              <Text variant="titleSmall">{p.nev}</Text>
              {sajat.length === 0 ? (
                <Text variant="bodySmall">Nincs összekötve.</Text>
              ) : (
                sajat.map((k) => (
                  <Text
                    key={k.id}
                    variant="bodySmall"
                    style={k.lejart ? { color: theme.colors.error } : undefined}
                  >
                    …{k.iban_vege} ·{' '}
                    {k.lejart
                      ? 'a hozzáférés lejárt, hagyd jóvá újra'
                      : `még ${k.napok_hatra ?? '?'} napig érvényes`}{' '}
                    · utolsó szinkron: {k.utolso_szinkron ?? 'még nem volt'}
                  </Text>
                ))
              )}
              <Button
                mode={lejarGyorsan || sajat.length === 0 ? 'contained-tonal' : 'text'}
                icon="bank"
                onPress={() => osszekot(p.kulcs)}
                loading={folyamatban === p.kulcs}
                disabled={folyamatban !== null}
                style={styles.gomb}
              >
                {sajat.length === 0 ? 'Összekötés' : 'Újra jóváhagyás'}
              </Button>
            </View>
          );
        })}
      </Card.Content>
      <Card.Actions>
        <Button
          icon="sync"
          onPress={szinkron}
          loading={folyamatban === 'szinkron'}
          disabled={folyamatban !== null || kapcsolatok.length === 0}
        >
          Szinkronizálás most
        </Button>
      </Card.Actions>
    </Card>
  );
}

const styles = StyleSheet.create({
  elvalaszto: { marginVertical: 12 },
  gomb: { alignSelf: 'flex-start', marginTop: 8 },
});
