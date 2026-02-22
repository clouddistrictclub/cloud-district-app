import { Stack } from 'expo-router';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { useAuthStore } from '../store/authStore';
import { useCartStore } from '../store/cartStore';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as Notifications from 'expo-notifications';

if (Platform.OS !== 'web') {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

export default function RootLayout() {
  const loadToken = useAuthStore(state => state.loadToken);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    loadToken();
    // Manually rehydrate cart from localStorage/AsyncStorage on client mount.
    // skipHydration: true in cartStore prevents SSR from caching empty fallback storage.
    const doRehydrate = async () => {
      console.log('[_layout] Starting rehydration...');
      try {
        await useCartStore.persist.rehydrate();
        console.log('[_layout] Rehydration complete');
        console.log('[_layout] Cart items after rehydrate:', useCartStore.getState().items);
        setHydrated(true);
      } catch (e) {
        console.error('[_layout] Rehydration error:', e);
        setHydrated(true);
      }
    };
    doRehydrate();
  }, []);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    const sub = Notifications.addNotificationReceivedListener((notification) => {
      console.log('Notification received:', notification);
    });
    return () => sub.remove();
  }, []);

  return (
    <SafeAreaProvider>
      <Stack
        screenOptions={{
          headerShown: false
        }}
      />
    </SafeAreaProvider>
  );
}