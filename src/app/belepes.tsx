import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Button, SegmentedButtons, Text, TextInput, useTheme } from 'react-native-paper';

import { useStore } from '../store/useStore';

type Mod = 'belepes' | 'csatlakozas' | 'uj';

/** Belépés, regisztráció meghívókóddal (meglévő háztartáshoz) vagy új háztartás létrehozása. */
export default function BelepesScreen() {
  const theme = useTheme();
  const munkamenet = useStore((s) => s.munkamenet);
  const munkamenetHiba = useStore((s) => s.munkamenetHiba);
  const inditas = useStore((s) => s.munkamenetInditas);
  const belepes = useStore((s) => s.belepes);
  const regisztracio = useStore((s) => s.regisztracio);

  const [mod, setMod] = useState<Mod>('belepes');
  const [email, setEmail] = useState('');
  const [jelszo, setJelszo] = useState('');
  const [nev, setNev] = useState('');
  const [kod, setKod] = useState('');
  const [haztartasNev, setHaztartasNev] = useState('');
  const [hiba, setHiba] = useState('');
  const [folyamatban, setFolyamatban] = useState(false);

  if (munkamenet === 'betolt') {
    return (
      <View style={styles.kozep}>
        <ActivityIndicator size="large" />
      </View>
    );
  }
  if (munkamenet === 'hiba') {
    return (
      <View style={styles.kozep}>
        <Text variant="titleMedium">A szerver nem érhető el</Text>
        <Text style={{ color: theme.colors.error }}>{munkamenetHiba}</Text>
        <Button mode="contained" onPress={inditas}>
          Újra
        </Button>
      </View>
    );
  }

  const kuld = async () => {
    setHiba('');
    setFolyamatban(true);
    try {
      if (mod === 'belepes') await belepes(email.trim(), jelszo);
      else
        await regisztracio({
          email: email.trim(),
          jelszo,
          nev: nev.trim(),
          ...(mod === 'csatlakozas'
            ? { meghivokod: kod.trim() }
            : { regisztracios_kod: kod.trim(), haztartas_nev: haztartasNev.trim() }),
        });
    } catch (e) {
      setHiba(e instanceof Error ? e.message : 'A művelet nem sikerült.');
    }
    setFolyamatban(false);
  };

  const kesz =
    email.trim() &&
    jelszo &&
    (mod === 'belepes' || (nev.trim() && kod.trim() && (mod === 'csatlakozas' || kod.trim())));

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text variant="headlineMedium" style={styles.cim}>
          VeSpendo
        </Text>
        <SegmentedButtons
          value={mod}
          onValueChange={(v) => {
            setMod(v as Mod);
            setHiba('');
          }}
          buttons={[
            { value: 'belepes', label: 'Belépés' },
            { value: 'csatlakozas', label: 'Csatlakozás' },
            { value: 'uj', label: 'Új háztartás' },
          ]}
        />
        {mod !== 'belepes' && (
          <TextInput mode="outlined" label="Neved" value={nev} onChangeText={setNev} autoComplete="name" />
        )}
        <TextInput
          mode="outlined"
          label="E-mail"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          autoComplete="email"
        />
        <TextInput
          mode="outlined"
          label="Jelszó"
          value={jelszo}
          onChangeText={setJelszo}
          secureTextEntry
          autoCapitalize="none"
          autoComplete={mod === 'belepes' ? 'current-password' : 'new-password'}
          onSubmitEditing={kesz ? kuld : undefined}
        />
        {mod !== 'belepes' && (
          <Text variant="bodySmall">Legalább 10 karakter, ne legyen könnyen kitalálható.</Text>
        )}
        {mod === 'csatlakozas' && (
          <TextInput
            mode="outlined"
            label="Meghívókód"
            value={kod}
            onChangeText={setKod}
            autoCapitalize="characters"
            autoCorrect={false}
          />
        )}
        {mod === 'uj' && (
          <>
            <TextInput
              mode="outlined"
              label="Háztartás neve"
              value={haztartasNev}
              onChangeText={setHaztartasNev}
            />
            <TextInput
              mode="outlined"
              label="Regisztrációs kód"
              value={kod}
              onChangeText={setKod}
              autoCapitalize="none"
              autoCorrect={false}
              secureTextEntry
            />
            <Text variant="bodySmall">
              Új háztartás létrehozásához a VeSpendo üzemeltetőjétől kapott regisztrációs kód kell. A háztartás
              adatai teljesen elkülönülnek másokétól.
            </Text>
          </>
        )}
        {!!hiba && <Text style={{ color: theme.colors.error }}>{hiba}</Text>}
        <Button mode="contained" onPress={kuld} loading={folyamatban} disabled={folyamatban || !kesz}>
          {mod === 'belepes' ? 'Belépés' : 'Regisztráció'}
        </Button>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, gap: 12, maxWidth: 480, width: '100%', alignSelf: 'center', flexGrow: 1, justifyContent: 'center' },
  kozep: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, padding: 24 },
  cim: { textAlign: 'center', fontWeight: '700', marginBottom: 8 },
});
