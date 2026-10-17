import { StyleSheet, View } from 'react-native';
import { Chip } from 'react-native-paper';

import { useStore } from '../store/useStore';

interface Props {
  ertek: string;
  onChange: (kulcs: string) => void;
  /** Szűrőként: 'Mind' elem is megjelenik (kulcsa: 'mind'). */
  mind?: boolean;
  /** A 'Közös' elem megjelenjen-e (feltöltőnél nem). */
  kozos?: boolean;
}

/** Személyválasztó chipekkel: a személyek a szerverről jönnek (átnevezhetők, bővíthetők). */
export function SzemelyValaszto({ ertek, onChange, mind = false, kozos = true }: Props) {
  const szemelyek = useStore((s) => s.szemelyek);
  const lista = szemelyek.filter(
    (s) => (s.aktiv || s.kulcs === ertek) && (kozos || s.kulcs !== 'kozos'),
  );

  return (
    <View style={styles.sor}>
      {mind && (
        <Chip selected={ertek === 'mind'} showSelectedOverlay onPress={() => onChange('mind')}>
          Mind
        </Chip>
      )}
      {lista.map((s) => (
        <Chip
          key={s.kulcs}
          selected={ertek === s.kulcs}
          showSelectedOverlay
          onPress={() => onChange(s.kulcs)}
        >
          {s.nev}
        </Chip>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  sor: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
});
