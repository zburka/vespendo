import { useState } from 'react';
import { Button, Card, Dialog, List, Portal, TextInput } from 'react-native-paper';

import { useKeyboardHeight } from '../hooks/useKeyboardHeight';
import { jelszoCsere } from '../services/auth';
import { useStore } from '../store/useStore';
import { Alert } from '../utils/uzenet';

/** A bejelentkezett fiók: név, e-mail, jelszócsere, kilépés. */
export function FiokKartya() {
  const en = useStore((s) => s.en);
  const kilepes = useStore((s) => s.kilepes);
  const szemelyek = useStore((s) => s.szemelyek);
  const [nyitva, setNyitva] = useState(false);
  const [regi, setRegi] = useState('');
  const [uj, setUj] = useState('');
  const [folyamatban, setFolyamatban] = useState(false);
  const billentyuzet = useKeyboardHeight();

  if (!en) return null;
  const szemely = szemelyek.find((p) => p.kulcs === en.haztartas.szemely_kulcs);

  const csere = async () => {
    setFolyamatban(true);
    try {
      await jelszoCsere(regi, uj);
      setNyitva(false);
      setRegi('');
      setUj('');
      // a jelszócsere minden eszközt kijelentkeztet, ezért újra be kell lépni
      Alert.alert('Jelszó megváltozott', 'Biztonsági okból minden eszközön újra be kell lépni.');
      await kilepes();
    } catch (e) {
      Alert.alert('Jelszócsere', e instanceof Error ? e.message : 'A jelszócsere nem sikerült.');
    }
    setFolyamatban(false);
  };

  return (
    <Card>
      <Card.Title title="Fiókom" />
      <Card.Content>
        <List.Item title={en.felhasznalo.nev} description={en.felhasznalo.email} />
        <List.Item
          title="Személyem a háztartásban"
          description={szemely ? szemely.nev : 'nincs kiválasztva'}
        />
      </Card.Content>
      <Card.Actions>
        <Button onPress={() => setNyitva(true)}>Jelszócsere</Button>
        <Button icon="logout" onPress={() => kilepes()}>
          Kilépés
        </Button>
      </Card.Actions>
      <Portal>
        <Dialog visible={nyitva} dismissable={false} style={{ marginBottom: billentyuzet }}>
          <Dialog.Title>Jelszócsere</Dialog.Title>
          <Dialog.Content style={{ gap: 12 }}>
            <TextInput mode="outlined" label="Jelenlegi jelszó" value={regi} onChangeText={setRegi} secureTextEntry autoCapitalize="none" />
            <TextInput mode="outlined" label="Új jelszó (min. 10 karakter)" value={uj} onChangeText={setUj} secureTextEntry autoCapitalize="none" />
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setNyitva(false)} disabled={folyamatban}>
              Mégse
            </Button>
            <Button onPress={csere} loading={folyamatban} disabled={folyamatban || !regi || !uj}>
              Módosítás
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </Card>
  );
}
