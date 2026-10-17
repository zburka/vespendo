import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert } from 'react-native';
import { FAB, Portal } from 'react-native-paper';

export function MuveletGomb() {
  const router = useRouter();
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

  return (
    <Portal>
      <FAB.Group
        open={nyitva}
        visible
        icon={nyitva ? 'close' : 'plus'}
        onStateChange={({ open }) => setNyitva(open)}
        actions={[
          { icon: 'camera', label: 'Nyugta fotózása', onPress: () => nyugtaKivalasztas('kamera') },
          {
            icon: 'image',
            label: 'Nyugta a galériából',
            onPress: () => nyugtaKivalasztas('galeria'),
          },
        ]}
      />
    </Portal>
  );
}
