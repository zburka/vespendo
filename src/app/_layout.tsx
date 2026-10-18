import { Stack } from 'expo-router';
import { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { MD3LightTheme, PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { SzerepPrompt } from '../components/SzerepPrompt';
import { ELO_API } from '../services/api';
import { elutasitottOlvas } from '../services/kulcs';
import { useStore } from '../store/useStore';

export default function RootLayout() {
  const belepve = useStore((s) => s.munkamenet === 'belepve');

  useEffect(() => {
    elutasitottOlvas().then((l) => useStore.getState().setElutasitott(l));
    if (ELO_API) useStore.getState().munkamenetInditas();
  }, []);

  return (
    <SafeAreaProvider>
      {/* fix világos téma: a Paper alapból a rendszer színsémáját követné, ami weben (sötét mód) felemás felületet adott */}
      <PaperProvider theme={MD3LightTheme}>
        <StatusBar style="dark" />
        {belepve && <SzerepPrompt />}
        <Stack>
          <Stack.Protected guard={!belepve}>
            <Stack.Screen name="belepes" options={{ headerShown: false }} />
          </Stack.Protected>
          <Stack.Protected guard={belepve}>
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
          </Stack.Protected>
        </Stack>
      </PaperProvider>
    </SafeAreaProvider>
  );
}
