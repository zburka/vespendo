import { Button, Dialog, Portal, Text } from 'react-native-paper';

import { useStore } from '../store/useStore';

/** Első indításkor megkérdezi, ki használja ezt a telefont (az importok és új tételek alapértelmezett tulajdonosa). */
export function SzerepPrompt() {
  const szukseges = useStore((s) => s.szerepSzukseges);
  const kulcsSzukseges = useStore((s) => s.kulcsSzukseges);
  const szemelyek = useStore((s) => s.szemelyek);
  const setSzerep = useStore((s) => s.setSzerep);

  const valaszthato = szemelyek.filter((p) => p.aktiv && p.kulcs !== 'kozos');

  return (
    <Portal>
      <Dialog visible={szukseges && !kulcsSzukseges && valaszthato.length > 0} dismissable={false}>
        <Dialog.Title>Ki vagy te?</Dialog.Title>
        <Dialog.Content>
          <Text variant="bodyMedium">
            Ezt a banki importnál, a nyugtáknál és az új tételeknél használjuk alapértelmezett
            tulajdonosként. Később a Beállítások fülön módosíthatod.
          </Text>
        </Dialog.Content>
        <Dialog.Actions>
          {valaszthato.map((p) => (
            <Button key={p.kulcs} onPress={() => setSzerep(p.kulcs)}>
              {p.nev}
            </Button>
          ))}
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );
}
