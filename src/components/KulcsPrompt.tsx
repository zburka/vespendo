import { useState } from 'react';
import { Button, Dialog, Portal, Text, TextInput, useTheme } from 'react-native-paper';

import { setAppKulcs } from '../services/api';
import { kulcsMent } from '../services/kulcs';
import { useStore } from '../store/useStore';

/** Első indításkor (vagy hibás kulcs esetén) bekéri az alkalmazás kulcsát, és biztonságosan eltárolja. */
export function KulcsPrompt() {
  const theme = useTheme();
  const szukseges = useStore((s) => s.kulcsSzukseges);
  const [kulcs, setKulcs] = useState('');
  const [probalt, setProbalt] = useState(false);
  const [mentes, setMentes] = useState(false);

  const ment = async () => {
    const tiszta = kulcs.trim();
    if (!tiszta) return;
    setMentes(true);
    try {
      await kulcsMent(tiszta);
    } catch {
      // ha a tároló nem érhető el, a kulcs csak az aktuális munkamenetre él
    }
    setAppKulcs(tiszta);
    setProbalt(true);
    setKulcs('');
    useStore.getState().setKulcsSzukseges(false);
    setMentes(false);
    await useStore.getState().betoltes(); // hibás kulcs esetén újra előugrik
  };

  return (
    <Portal>
      <Dialog visible={szukseges} dismissable={false}>
        <Dialog.Title>Alkalmazás kulcs</Dialog.Title>
        <Dialog.Content style={{ gap: 12 }}>
          <Text variant="bodyMedium">
            Add meg a VeSpendo szerver kulcsát. Ezt csak egyszer kell, utána a telefon biztonságosan
            megjegyzi.
          </Text>
          {probalt && (
            <Text variant="bodySmall" style={{ color: theme.colors.error }}>
              A szerver elutasította a kulcsot. Ellenőrizd, és próbáld újra.
            </Text>
          )}
          <TextInput
            mode="outlined"
            label="Kulcs"
            value={kulcs}
            onChangeText={setKulcs}
            autoCapitalize="none"
            autoCorrect={false}
            secureTextEntry
          />
        </Dialog.Content>
        <Dialog.Actions>
          <Button onPress={ment} loading={mentes} disabled={mentes || !kulcs.trim()}>
            Mentés
          </Button>
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );
}
