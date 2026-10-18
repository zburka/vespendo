import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { Text, useTheme } from 'react-native-paper';
import { View } from 'react-native';

import { MuveletGomb } from '../../components/MuveletGomb';
import { useStore } from '../../store/useStore';

export default function TabLayout() {
  const theme = useTheme();
  const demo = useStore((s) => !!s.en?.felhasznalo.demo);

  return (
    <>
      {demo && (
        <View style={{ backgroundColor: theme.colors.tertiaryContainer, paddingVertical: 4, paddingHorizontal: 12 }}>
          <Text variant="labelSmall" style={{ textAlign: 'center', color: theme.colors.onTertiaryContainer }}>
            Demó mód: kitalált adatok, a bemutató éjszakánként visszaáll
          </Text>
        </View>
      )}
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: theme.colors.primary,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: 'Dashboard',
            headerTitle: 'VeSpendo',
            headerTitleStyle: { fontWeight: '700' },
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="home" size={size} color={color as string} />
            ),
          }}
        />
        <Tabs.Screen
          name="tranzakciok"
          options={{
            title: 'Tranzakciók',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="list" size={size} color={color as string} />
            ),
          }}
        />
        <Tabs.Screen
          name="celok"
          options={{
            title: 'Célok',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="flag" size={size} color={color as string} />
            ),
          }}
        />
        <Tabs.Screen
          name="beallitasok"
          options={{
            title: 'Beállítások',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="settings" size={size} color={color as string} />
            ),
          }}
        />
      </Tabs>
      <MuveletGomb />
    </>
  );
}
