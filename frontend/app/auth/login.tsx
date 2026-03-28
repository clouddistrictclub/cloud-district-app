import { View, Text, StyleSheet, TextInput, TouchableOpacity } from 'react-native';
import { useState } from 'react';
import { useRouter, Link } from 'expo-router';
import { useAuthStore } from '../../store/authStore';
import { SafeAreaView } from 'react-native-safe-area-context';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import HeroBanner from '../../components/HeroBanner';

export default function Login() {
  const router = useRouter();
  const login = useAuthStore(state => state.login);
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleLogin = async () => {
    setErrorMsg(null);
    if (!identifier || !password) {
      setErrorMsg('Please fill in all fields');
      return;
    }
    setLoading(true);
    try {
      await login(identifier, password);
      router.replace('/(tabs)/home');
    } catch (error: any) {
      setErrorMsg(error?.response?.data?.detail || 'Invalid email/username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <KeyboardAwareScrollView contentContainerStyle={styles.scrollContent}>
        <HeroBanner testID="login-hero-img" />

        <View style={styles.formSection}>
          <Text style={styles.title} data-testid="login-title">Cloud District Club</Text>
          <Text style={styles.subtitle}>Welcome Back</Text>

          <View style={styles.form}>
            <Text style={styles.label}>Email or Username</Text>
            <TextInput
              style={styles.input}
              placeholder="your@email.com or username"
              placeholderTextColor="#666"
              value={identifier}
              onChangeText={setIdentifier}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
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

            {errorMsg ? (
              <View style={styles.errorBox} data-testid="login-error-msg">
                <Text style={styles.errorText}>{errorMsg}</Text>
              </View>
            ) : null}

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
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.12)',
    borderWidth: 1,
    borderColor: '#ef4444',
    borderRadius: 12,
    padding: 12,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 14,
    textAlign: 'center',
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
