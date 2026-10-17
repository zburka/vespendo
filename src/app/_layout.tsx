import { Stack } from 'expo-router';
import { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { KulcsPrompt } from '../components/KulcsPrompt';
import { ELO_API, setAppKulcs, vanAppKulcs } from '../services/api';
import { kulcsOlvas } from '../services/kulcs';
import { useStore } from '../store/useStore';

export default function RootLayout() {
  useEffect(() => {
    (async () => {
      if (!ELO_API) return;
      try {
        const tarolt = await kulcsOlvas();
        if (tarolt) setAppKulcs(tarolt);
      } catch {
        // a tároló nem érhető el: az app bekéri a kulcsot
      }
      if (!vanAppKulcs()) {
        useStore.getState().setKulcsSzukseges(true);
        return;
      }
      useStore.getState().betoltes();
    })();
  }, []);

  return (
    <SafeAreaProvider>
      <PaperProvider>
        <StatusBar style="auto" />
        <KulcsPrompt />
        <Stack>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen
            name="tranzakcio/[id]"
            options={{ title: 'Tétel', headerBackTitle: 'Vissza' }}
          />
          <Stack.Screen
            name="nyugta"
            options={{ title: 'Nyugta rögzítése', presentation: 'modal' }}
          />
          <Stack.Screen name="import" options={{ title: 'Banki import', presentation: 'modal' }} />
          <Stack.Screen name="uj-tetel" options={{ title: 'Új tétel', presentation: 'modal' }} />
        </Stack>
      </PaperProvider>
    </SafeAreaProvider>
  );
}
