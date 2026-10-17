import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { usePathname, useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, Platform } from 'react-native';
import { FAB, Portal } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export function MuveletGomb() {
  const router = useRouter();
  const pathname = usePathname();
  const insets = useSafeAreaInsets();
  // csak ott látszik, ahol új tételt rögzítesz; a fül sáv fölött ül, nem takarja a Beállításokat
  const lathato = pathname === '/' || pathname === '/tranzakciok';
  const tabSavMagassag = (Platform.OS === 'ios' ? 49 : 56) + insets.bottom;
  const [nyitva, setNyitva] = useState(false);

  const nyugtaKivalasztas = async (forras: 'kamera' | 'galeria') => {
    if (forras === 'kamera') {
      const { granted } = await ImagePicker.requestCameraPermissionsAsync();
      if (!granted) {
        Alert.alert('Kamera', 'A nyugta fotózásához engedélyezd a kamera használatát.');
        return;
      }
    }
    const opciok: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 1 };
    const eredmeny =
      forras === 'kamera'
        ? await ImagePicker.launchCameraAsync(opciok)
        : await ImagePicker.launchImageLibraryAsync(opciok);
    if (eredmeny.canceled) return;
    const kep = eredmeny.assets[0];
    router.push({
      pathname: '/nyugta',
      params: { uri: kep.uri, szelesseg: String(kep.width) },
    });
  };

  const bankiFajl = async () => {
    const eredmeny = await DocumentPicker.getDocumentAsync({
      type: [
        'text/csv',
        'text/comma-separated-values',
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '*/*',
      ],
      copyToCacheDirectory: true,
    });
    if (eredmeny.canceled) return;
    const fajl = eredmeny.assets[0];
    router.push({ pathname: '/import', params: { uri: fajl.uri, nev: fajl.name } });
  };

  return (
    <Portal>
      <FAB.Group
        open={nyitva}
        visible={lathato}
        style={{ paddingBottom: tabSavMagassag }}
        icon={nyitva ? 'close' : 'plus'}
        onStateChange={({ open }) => setNyitva(open)}
        actions={[
          { icon: 'camera', label: 'Nyugta fotózása', onPress: () => nyugtaKivalasztas('kamera') },
          {
            icon: 'image',
            label: 'Nyugta a galériából',
            onPress: () => nyugtaKivalasztas('galeria'),
          },
          { icon: 'file-table', label: 'Banki fájl tallózása', onPress: bankiFajl },
          { icon: 'pencil-plus', label: 'Kézi hozzáadás', onPress: () => router.push('/uj-tetel') },
        ]}
      />
    </Portal>
  );
}
