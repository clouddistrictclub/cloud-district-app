import { Stack } from 'expo-router';
import { useEffect } from 'react';
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
  const hydrateCart = useCartStore(state => state.hydrateCart);

  useEffect(() => {
    loadToken();
    // Hydrate cart from localStorage (web) or AsyncStorage (native) on client mount.
    hydrateCart();
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
