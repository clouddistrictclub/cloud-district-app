import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { useEffect } from 'react';
import { useRouter } from 'expo-router';
import { useAuthStore } from '../store/authStore';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function Index() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    const checkAgeGate = async () => {
      if (isLoading) return;

      const ageVerified = await AsyncStorage.getItem('ageVerified');
      
      if (!ageVerified) {
        router.replace('/age-gate');
      } else if (!isAuthenticated) {
        router.replace('/auth/login');
      } else {
        router.replace('/(tabs)/home');
      }
    };

    checkAgeGate();
  }, [isAuthenticated, isLoading]);

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#6366f1" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
    alignItems: 'center',
    justifyContent: 'center',
  },
});