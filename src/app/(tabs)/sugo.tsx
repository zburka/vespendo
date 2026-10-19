import { useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { Button, Card, List, Text, TextInput } from 'react-native-paper';

import { ELO_API } from '../../services/api';
import { otletKuldes } from '../../services/auth';
import { Alert } from '../../utils/uzenet';

interface Resz {
  cim: string;
  ikon: string;
  pontok: string[];
}

const RESZEK: Resz[] = [
  {
    cim: 'Áttekintés',
    ikon: 'view-dashboard',
    pontok: [
      'A Dashboard megmutatja a hónap bevételét, kiadását és egyenlegét, személyenként is: közös, vagy a háztartás tagjainak saját költése.',
      'A „Kiadások kategóriánként” listában koppints egy kategóriára, és megnézheted a hozzá tartozó tételeket. Ahol van költségkeret, a sávon a piros vonal a keret határa; ha a sáv túlnyúlik rajta, túllépted.',
      'Az AI-összefoglaló lezárt hónapról visszatekintést, a folyamatban lévő hónapról helyzetképet és tanácsot ad a hátralévő napokra.',
      'A hónapot a fejlécben lapozhatod; a Tranzakciók fülön személyre és kategóriára is szűrhetsz.',
    ],
  },
  {
    cim: 'Tételek felvitele',
    ikon: 'plus-circle',
    pontok: [
      'Banki összekötés: a tételeid naponta automatikusan letöltődnek az OTP-ből. A Beállítások → Banki összekötés résznél indítod el; a bankban kell egyszer jóváhagynod, és kb. 6 havonta meg kell újítani.',
      'Banki kivonat feltöltése: a „+” gombbal PDF, Excel vagy CSV kivonatot tallózhatsz. A duplikációkat a rendszer felismeri, így nyugodtan töltheted fel újra.',
      'Nyugta fényképezése: a „+” → Nyugta résznél lefotózod a blokkot. Az AI soronként elolvassa, és kategóriákra bontja (pl. élelmiszer, ruházat, háztartás), az összeg a blokk végösszege lesz. Ha a bankból megjön a kártyás tétel, a rendszer párosítja a nyugtával; bármelyik érkezhet előbb.',
      'Kézi tétel: készpénzes vagy egyéb kiadásokhoz a „+” → Új tétel.',
      'A banki tételeket a bank néha több napot késve könyveli, ezért a friss vásárlás nem biztos, hogy rögtön megjelenik.',
    ],
  },
  {
    cim: 'Kategóriák',
    ikon: 'tag-multiple',
    pontok: [
      'A tételeket a rendszer kereskedő szerint automatikusan kategóriákba sorolja, az ismeretlen kereskedőket az AI.',
      'Ha egy tétel rossz kategóriába került, nyisd meg, és állítsd át: a rendszer megtanulja, és legközelebb magától jól sorolja.',
      'A Beállítások → Kategóriák résznél saját kategóriát vehetsz fel, átnevezheted, ikont választhatsz hozzá, vagy törölheted (ekkor a tételeket egy másik kategóriába teszi át).',
      'A belső átvezetések (pl. megtakarításra utalás) nem számítanak se kiadásnak, se bevételnek.',
    ],
  },
  {
    cim: 'Tervezés: keretek, célok, előfizetések',
    ikon: 'flag',
    pontok: [
      'Költségkeretet kategóriánként állíthatsz be havi összeggel; a Dashboard mutatja, mennyit költöttél belőle.',
      'A Célok fülön megtakarítási célokat követhetsz.',
      'Az Előfizetések az esedékességükkel együtt követhetők; a rendszer a tranzakcióid alapján javaslatot is tesz, mi lehet előfizetés.',
    ],
  },
  {
    cim: 'Háztartás és fiókok',
    ikon: 'account-group',
    pontok: [
      'Egy háztartáshoz több felhasználó is tartozhat (pl. házaspár). Új tag a meghívókóddal csatlakozik, amelyet az admin a Beállításoknál lát és küldhet el.',
      'Minden háztartás adata teljesen elkülönül a többiétől, más nem látja.',
      'A tételeknek tulajdonosa van (közös vagy személyenként); a Beállításokban a „Személyek” között felvehetsz újat, pl. gyereket.',
      'iPhone-on a banki kivonat a Megosztás menüből egy lépésben is feltölthető. Ehhez a Beállítások → API tokenek résznél hozz létre tokent a Parancsok alkalmazáshoz.',
    ],
  },
  {
    cim: 'Telepítés a telefonra',
    ikon: 'cellphone',
    pontok: [
      'iPhone: nyisd meg az oldalt a Safariban, koppints a Megosztás ikonra, majd „Főképernyőhöz adás”. Ettől kezdve az alkalmazás ikonja a főképernyőn van.',
      'Frissítés: az alkalmazás a következő megnyitáskor automatikusan az új verziót tölti be.',
      'A Beállítások fülön tudsz kilépni, jelszót cserélni, és ott látod a háztartás tagjait is.',
    ],
  },
];

/** Súgó: mire jó az alkalmazás és hogyan használható (a felhasználóknak szóló leírás). */
export default function SugoScreen() {
  const [otlet, setOtlet] = useState('');
  const [kuldes, setKuldes] = useState(false);

  const kuld = async () => {
    setKuldes(true);
    try {
      await otletKuldes(otlet.trim());
      setOtlet('');
      Alert.alert('Köszönjük!', 'Az ötletedet megkaptuk.');
    } catch (e) {
      Alert.alert('Ötlet', e instanceof Error ? e.message : 'A küldés nem sikerült.');
    }
    setKuldes(false);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card>
        <Card.Title title="Mire jó a VeSpendo?" />
        <Card.Content style={styles.szoveg}>
          <Text variant="bodyMedium">
            A VeSpendo egy családi költségkövető. Összegyűjti a banki tételeket és a nyugtákat, automatikusan kategóriákba sorolja őket,
            és áttekinthetően mutatja, hova megy a pénz. Segít a havi keretek betartásában, a megtakarítási célok követésében, és az AI
            rövid összefoglalót ír a hónapról.
          </Text>
        </Card.Content>
      </Card>

      <Card>
        {RESZEK.map((r) => (
          <List.Accordion key={r.cim} title={r.cim} left={(p) => <List.Icon {...p} icon={r.ikon} />}>
            <Card.Content style={styles.szoveg}>
              {r.pontok.map((p) => (
                <Text key={p} variant="bodyMedium">
                  •  {p}
                </Text>
              ))}
            </Card.Content>
          </List.Accordion>
        ))}
      </Card>

      {ELO_API && (
        <Card>
          <Card.Title title="Ötleted van?" subtitle="Írd le, mit hiányolsz, vagy mit lehetne jobban csinálni" />
          <Card.Content style={styles.szoveg}>
            <TextInput
              mode="outlined"
              label="Az ötleted"
              value={otlet}
              onChangeText={setOtlet}
              multiline
              numberOfLines={5}
              maxLength={2000}
            />
            <Text variant="bodySmall">Az ötletet a fejlesztő e-mailben megkapja, a neveddel és az e-mail címeddel együtt, hogy válaszolhasson.</Text>
          </Card.Content>
          <Card.Actions>
            <Button icon="send" onPress={kuld} loading={kuldes} disabled={kuldes || otlet.trim().length < 5}>
              Küldés
            </Button>
          </Card.Actions>
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  szoveg: { gap: 8, paddingBottom: 12 },
});
