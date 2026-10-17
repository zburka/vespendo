import { useEffect, useMemo, useState } from 'react';

import { ELO_API, haviOsszesito } from '../services/api';
import { useStore } from '../store/useStore';
import type { HaviOsszesito } from '../types';
import { szamolHaviOsszesito } from '../utils/osszesito';

/**
 * Dashboard adatok: mock módban helyi számítás, élő módban a `havi-osszesito` végpont válasza
 * (az előfizetések részletes listája és hiba esetén minden adat a helyi számításból jön).
 */
export function useHaviOsszesito() {
  const honap = useStore((s) => s.honap);
  const tranzakciok = useStore((s) => s.tranzakciok);
  const kategoriak = useStore((s) => s.kategoriak);
  const keretek = useStore((s) => s.keretek);
  const elofizetesek = useStore((s) => s.elofizetesek);

  const helyi = useMemo(
    () => szamolHaviOsszesito({ honap, tranzakciok, kategoriak, keretek, elofizetesek }),
    [honap, tranzakciok, kategoriak, keretek, elofizetesek],
  );

  // adat === null: a lekérés hibás volt
  const [eredmeny, setEredmeny] = useState<{ honap: string; adat: HaviOsszesito | null } | null>(
    null,
  );

  useEffect(() => {
    if (!ELO_API) return;
    let megszakitva = false;
    haviOsszesito(honap)
      .then((adat) => !megszakitva && setEredmeny({ honap, adat }))
      .catch(() => !megszakitva && setEredmeny({ honap, adat: null }));
    return () => {
      megszakitva = true;
    };
  }, [honap, tranzakciok]);

  const aktualis = eredmeny?.honap === honap ? eredmeny : null;
  const hiba = aktualis !== null && aktualis.adat === null;
  const betolt = ELO_API && aktualis === null;
  const osszesito: HaviOsszesito = aktualis?.adat
    ? { ...aktualis.adat, elofizetesek: aktualis.adat.elofizetesek ?? helyi.elofizetesek }
    : helyi;

  return { osszesito, hiba, betolt };
}
