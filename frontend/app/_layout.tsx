import { Stack } from 'expo-router';
import { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { SafeAreaProvider } from 'react-native-safe-area-context';

export default function RootLayout() {
  const loadToken = useAuthStore(state => state.loadToken);

  useEffect(() => {
    loadToken();
  }, []);

  return (
    <SafeAreaProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="age-gate" />
        <Stack.Screen name="auth/login" />
        <Stack.Screen name="auth/register" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="product/[id]" />
        <Stack.Screen name="cart" />
        <Stack.Screen name="checkout" />
      </Stack>
    </SafeAreaProvider>
  );
}