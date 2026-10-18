import { useState } from 'react';
import { Button, Dialog, Portal, Text, TextInput } from 'react-native-paper';

import { useKeyboardHeight } from '../hooks/useKeyboardHeight';
import { useStore } from '../store/useStore';
import { Alert } from '../utils/uzenet';

/**
 * Ha a fiók még nincs személyhez kötve (háztartáshoz csatlakozás után), megkérdezi, melyik személy vagy te,
 * vagy létrehoz újat. A személy a fiókhoz tartozik, így minden eszközön ugyanaz marad.
 */
export function SzerepPrompt() {
  const szukseges = useStore((s) => s.szerepSzukseges);
  const szemelyek = useStore((s) => s.szemelyek);
  const en = useStore((s) => s.en);
  const setSzerep = useStore((s) => s.setSzerep);
  const mentSzemely = useStore((s) => s.mentSzemely);
  const profilFrissit = useStore((s) => s.profilFrissit);
  const [uj, setUj] = useState('');
  const [folyamatban, setFolyamatban] = useState(false);
  const billentyuzet = useKeyboardHeight();

  // olyan személyek, akiket még nem használ más tag
  const foglalt = new Set((en?.tagok ?? []).map((t) => t.szemely_kulcs).filter(Boolean));
  const valaszthato = szemelyek.filter((p) => p.aktiv && p.kulcs !== 'kozos' && !foglalt.has(p.kulcs));

  const futtat = async (f: () => Promise<void>) => {
    setFolyamatban(true);
    try {
      await f();
    } catch (e) {
      Alert.alert('Hiba', e instanceof Error ? e.message : 'A művelet nem sikerült.');
    }
    setFolyamatban(false);
  };

  const ujSzemely = () =>
    futtat(async () => {
      const kulcs = await mentSzemely(undefined, uj.trim(), true);
      if (!kulcs) throw new Error('A személy létrehozása nem sikerült.');
      await setSzerep(kulcs);
      setUj('');
    });

  return (
    <Portal>
      <Dialog visible={szukseges && !!en} dismissable={false} style={{ marginBottom: billentyuzet }}>
        <Dialog.Title>Ki vagy te a háztartásban?</Dialog.Title>
        <Dialog.Content style={{ gap: 12 }}>
          <Text variant="bodyMedium">
            Ezt a banki importnál, a nyugtáknál és az új tételeknél használjuk alapértelmezett tulajdonosként.
            Később a Beállítások fülön módosíthatod.
          </Text>
          {valaszthato.map((p) => (
            <Button
              key={p.kulcs}
              mode="outlined"
              disabled={folyamatban}
              onPress={() => futtat(() => setSzerep(p.kulcs))}
            >
              {p.nev}
            </Button>
          ))}
          <TextInput mode="outlined" label="Vagy új személy neve" value={uj} onChangeText={setUj} />
        </Dialog.Content>
        <Dialog.Actions>
          <Button onPress={() => profilFrissit().catch(() => {})} disabled={folyamatban}>
            Frissítés
          </Button>
          <Button onPress={ujSzemely} loading={folyamatban} disabled={folyamatban || !uj.trim()}>
            Új személy
          </Button>
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );
}
