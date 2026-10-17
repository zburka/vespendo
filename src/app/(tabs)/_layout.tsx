import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { useTheme } from 'react-native-paper';

import { MuveletGomb } from '../../components/MuveletGomb';

export default function TabLayout() {
  const theme = useTheme();

  return (
    <>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: theme.colors.primary,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: 'Dashboard',
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
      </Tabs>
      <MuveletGomb />
    </>
  );
}
