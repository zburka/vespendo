import { Button, Dialog, Portal, Text } from 'react-native-paper';

import { useStore } from '../store/useStore';

/** Első indításkor megkérdezi, ki használja ezt a telefont (az importok alapértelmezett feltöltője). */
export function SzerepPrompt() {
  const szukseges = useStore((s) => s.szerepSzukseges);
  const kulcsSzukseges = useStore((s) => s.kulcsSzukseges);
  const setSzerep = useStore((s) => s.setSzerep);

  return (
    <Portal>
      <Dialog visible={szukseges && !kulcsSzukseges} dismissable={false}>
        <Dialog.Title>Ki vagy te?</Dialog.Title>
        <Dialog.Content>
          <Text variant="bodyMedium">
            Ezt a beállítást a banki importnál és a nyugtáknál használjuk alapértelmezett
            feltöltőként. Később a Beállítások fülön módosíthatod.
          </Text>
        </Dialog.Content>
        <Dialog.Actions>
          <Button onPress={() => setSzerep('ferj')}>Férj</Button>
          <Button onPress={() => setSzerep('feleseg')}>Feleség</Button>
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );
}
