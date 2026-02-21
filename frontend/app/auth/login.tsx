import { View, Text, StyleSheet, TextInput, TouchableOpacity, Platform, Alert, Image } from 'react-native';
import { useState } from 'react';
import { useRouter, Link } from 'expo-router';
import { useAuthStore } from '../../store/authStore';
import { SafeAreaView } from 'react-native-safe-area-context';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import { LinearGradient } from 'expo-linear-gradient';

const heroAsset = require('../../assets/images/heroes/CloudDistrict_Mobile_Hero_v1_A_Final.png');

const LoginHero = () => {
  if (Platform.OS === 'web') {
    let uri: string;
    if (typeof heroAsset === 'string') uri = heroAsset;
    else if (typeof heroAsset === 'number') uri = Image.resolveAssetSource(heroAsset)?.uri ?? '';
    else uri = heroAsset?.uri ?? '';
    return (
      <View style={styles.heroWrap}>
        <img
          src={uri}
          style={{ width: '100%', height: '26vh', objectFit: 'cover', objectPosition: 'center center', display: 'block' }}
          data-testid="login-hero-img"
          alt="Cloud District"
        />
        <LinearGradient
          colors={['transparent', '#0c0c0c']}
          style={styles.heroGradient}
        />
      </View>
    );
  }
  return (
    <View style={styles.heroWrap}>
      <Image
        source={heroAsset}
        style={styles.heroNative}
        resizeMode="cover"
        testID="login-hero-img"
      />
      <LinearGradient
        colors={['transparent', '#0c0c0c']}
        style={styles.heroGradient}
      />
    </View>
  );
};

export default function Login() {
  const router = useRouter();
  const login = useAuthStore(state => state.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      router.replace('/(tabs)/home');
    } catch (error: any) {
      Alert.alert('Login Failed', error.response?.data?.detail || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <KeyboardAwareScrollView contentContainerStyle={styles.scrollContent}>
        <LoginHero />

        <View style={styles.formSection}>
          <Text style={styles.title} data-testid="login-title">Cloud District Club</Text>
          <Text style={styles.subtitle}>Welcome Back</Text>

          <View style={styles.form}>
            <Text style={styles.label}>Email</Text>
            <TextInput
              style={styles.input}
              placeholder="your@email.com"
              placeholderTextColor="#666"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              data-testid="login-email-input"
            />

            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              placeholder="********"
              placeholderTextColor="#666"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              data-testid="login-password-input"
            />

            <TouchableOpacity
              style={[styles.button, loading && styles.buttonDisabled]}
              onPress={handleLogin}
              disabled={loading}
              data-testid="login-btn"
            >
              <Text style={styles.buttonText}>{loading ? 'Logging in...' : 'Login'}</Text>
            </TouchableOpacity>

            <View style={styles.footer}>
              <Text style={styles.footerText}>Don't have an account? </Text>
              <Link href="/auth/register" asChild>
                <TouchableOpacity>
                  <Text style={styles.link}>Sign Up</Text>
                </TouchableOpacity>
              </Link>
            </View>
          </View>
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
  },
  scrollContent: {
    flexGrow: 1,
  },
  heroWrap: {
    width: '100%',
    overflow: 'hidden',
  },
  heroNative: {
    width: '100%',
    height: 220,
  },
  heroGradient: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: 60,
  },
  formSection: {
    paddingHorizontal: 24,
    marginTop: -8,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 15,
    color: '#A0A0A0',
    textAlign: 'center',
    marginBottom: 32,
  },
  form: {
    gap: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
    marginBottom: -8,
  },
  input: {
    backgroundColor: '#1A1A1A',
    borderWidth: 1,
    borderColor: '#333333',
    borderRadius: 18,
    padding: 16,
    color: '#fff',
    fontSize: 16,
  },
  button: {
    backgroundColor: '#2E6BFF',
    padding: 16,
    borderRadius: 18,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 16,
  },
  footerText: {
    color: '#A0A0A0',
    fontSize: 14,
  },
  link: {
    color: '#2E6BFF',
    fontSize: 14,
    fontWeight: '600',
  },
});
