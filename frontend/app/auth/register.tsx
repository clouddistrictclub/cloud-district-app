import { View, Text, StyleSheet, TextInput, TouchableOpacity, Alert, Platform } from 'react-native';
import { useState, useEffect } from 'react';
import { useRouter, Link, useLocalSearchParams } from 'expo-router';
import { useAuthStore } from '../../store/authStore';
import { SafeAreaView } from 'react-native-safe-area-context';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import { theme } from '../../theme';

export default function Register() {
  const router = useRouter();
  const { ref } = useLocalSearchParams<{ ref?: string }>();
  const register = useAuthStore(state => state.register);
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [month, setMonth] = useState('');
  const [day, setDay] = useState('');
  const [year, setYear] = useState('');
  const [referralCode, setReferralCode] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (ref && !isAuthenticated) {
      setReferralCode(ref.toUpperCase());
    }
  }, [ref, isAuthenticated]);

  const handleRegister = async () => {
    if (!email || !password || !firstName || !lastName || !month || !day || !year) {
      const msg = 'Please fill in all required fields';
      Platform.OS === 'web' ? alert(msg) : Alert.alert('Error', msg);
      return;
    }

    const dateOfBirth = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;

    setLoading(true);
    try {
      await register(email, password, firstName, lastName, dateOfBirth, referralCode.trim() || undefined);
      router.replace('/(tabs)/home');
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'An error occurred';
      Platform.OS === 'web' ? alert(msg) : Alert.alert('Registration Failed', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAwareScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.content}>
          <Text style={styles.title}>Create Account</Text>
          <Text style={styles.subtitle}>Join Cloud District Club</Text>

          <View style={styles.form}>
            <Text style={styles.label}>First Name</Text>
            <TextInput
              style={styles.input}
              placeholder="John"
              placeholderTextColor="#666"
              value={firstName}
              onChangeText={setFirstName}
              data-testid="register-first-name"
            />

            <Text style={styles.label}>Last Name</Text>
            <TextInput
              style={styles.input}
              placeholder="Doe"
              placeholderTextColor="#666"
              value={lastName}
              onChangeText={setLastName}
              data-testid="register-last-name"
            />

            <Text style={styles.label}>Email</Text>
            <TextInput
              style={styles.input}
              placeholder="your@email.com"
              placeholderTextColor="#666"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              data-testid="register-email"
            />

            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              placeholder="Create a password"
              placeholderTextColor="#666"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              data-testid="register-password"
            />

            <Text style={styles.label}>Date of Birth (Must be 21+)</Text>
            <View style={styles.dateContainer}>
              <TextInput
                style={styles.dateInput}
                placeholder="MM"
                placeholderTextColor="#666"
                value={month}
                onChangeText={setMonth}
                keyboardType="numeric"
                maxLength={2}
                data-testid="register-dob-month"
              />
              <Text style={styles.dateSeparator}>/</Text>
              <TextInput
                style={styles.dateInput}
                placeholder="DD"
                placeholderTextColor="#666"
                value={day}
                onChangeText={setDay}
                keyboardType="numeric"
                maxLength={2}
                data-testid="register-dob-day"
              />
              <Text style={styles.dateSeparator}>/</Text>
              <TextInput
                style={styles.dateInputYear}
                placeholder="YYYY"
                placeholderTextColor="#666"
                value={year}
                onChangeText={setYear}
                keyboardType="numeric"
                maxLength={4}
                data-testid="register-dob-year"
              />
            </View>

            <Text style={styles.label}>Referral Code <Text style={styles.optional}>(optional)</Text></Text>
            <TextInput
              style={styles.input}
              placeholder="Enter a friend's referral code"
              placeholderTextColor="#666"
              value={referralCode}
              onChangeText={(text) => setReferralCode(text.toUpperCase())}
              autoCapitalize="characters"
              maxLength={8}
              data-testid="register-referral-code"
            />

            <TouchableOpacity 
              style={[styles.button, loading && styles.buttonDisabled]} 
              onPress={handleRegister}
              disabled={loading}
              data-testid="register-submit-btn"
            >
              <Text style={styles.buttonText}>{loading ? 'Creating Account...' : 'Sign Up'}</Text>
            </TouchableOpacity>

            <View style={styles.footer}>
              <Text style={styles.footerText}>Already have an account? </Text>
              <Link href="/auth/login" asChild>
                <TouchableOpacity>
                  <Text style={styles.link}>Login</Text>
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
    backgroundColor: theme.colors.background,
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: theme.colors.textMuted,
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
  optional: {
    color: theme.colors.textMuted,
    fontWeight: '400',
  },
  input: {
    backgroundColor: theme.colors.inputBackground,
    borderWidth: 1,
    borderColor: theme.colors.inputBorder,
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    color: '#fff',
    fontSize: 16,
  },
  dateContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dateInput: {
    flex: 1,
    backgroundColor: theme.colors.inputBackground,
    borderWidth: 1,
    borderColor: theme.colors.inputBorder,
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
  },
  dateInputYear: {
    flex: 1.5,
    backgroundColor: theme.colors.inputBackground,
    borderWidth: 1,
    borderColor: theme.colors.inputBorder,
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
  },
  dateSeparator: {
    color: '#666',
    fontSize: 20,
    marginHorizontal: 8,
  },
  button: {
    backgroundColor: theme.colors.primary,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
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
    color: theme.colors.textMuted,
    fontSize: 14,
  },
  link: {
    color: theme.colors.primary,
    fontSize: 14,
    fontWeight: '600',
  },
});
