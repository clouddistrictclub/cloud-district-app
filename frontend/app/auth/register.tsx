import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator, Image, Platform } from 'react-native';
import { useState, useEffect, useRef } from 'react';
import { useRouter, Link, useLocalSearchParams } from 'expo-router';
import { useAuthStore } from '../../store/authStore';
import { SafeAreaView } from 'react-native-safe-area-context';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import { theme } from '../../theme';
import axios from 'axios';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { API_URL } from '../../constants/api';

type UsernameStatus = 'idle' | 'checking' | 'available' | 'taken';

function formatPhone(raw: string): string {
  const nums = raw.replace(/\D/g, '').slice(0, 10);
  if (nums.length <= 3) return nums;
  if (nums.length <= 6) return `(${nums.slice(0, 3)}) ${nums.slice(3)}`;
  return `(${nums.slice(0, 3)}) ${nums.slice(3, 6)}-${nums.slice(6)}`;
}

export default function Register() {
  const router = useRouter();
  const { ref } = useLocalSearchParams<{ ref?: string }>();
  const register = useAuthStore(state => state.register);
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [ageVerified, setAgeVerified] = useState(false);
  const [referralCode, setReferralCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [usernameStatus, setUsernameStatus] = useState<UsernameStatus>('idle');
  const [profilePhoto, setProfilePhoto] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (ref && !isAuthenticated) {
      setReferralCode(ref.toLowerCase());
    }
  }, [ref, isAuthenticated]);

  const pickAvatar = async () => {
    if (Platform.OS !== 'web') {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        setErrorMsg('Camera roll permission is required to upload a photo');
        return;
      }
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.6,
      base64: true,
    });
    if (!result.canceled && result.assets[0].base64) {
      setProfilePhoto(`data:image/jpeg;base64,${result.assets[0].base64}`);
    }
  };

  // Debounced username availability check
  useEffect(() => {
    const trimmed = username.trim();
    if (trimmed.length < 3) {
      setUsernameStatus('idle');
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setUsernameStatus('checking');
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await axios.get(`${API_URL}/api/auth/check-username`, {
          params: { username: trimmed },
        });
        setUsernameStatus(res.data.available ? 'available' : 'taken');
      } catch {
        setUsernameStatus('idle');
      }
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [username]);

  const showError = (msg: string) => setErrorMsg(msg);

  const handleRegister = async () => {
    setErrorMsg(null);

    if (!firstName || !lastName || !username || !email || !phone || !password || !confirmPassword) {
      showError('Please fill in all required fields');
      return;
    }

    const rawPhone = phone.replace(/\D/g, '');
    if (rawPhone.length < 10) {
      showError('Please enter a valid 10-digit phone number');
      return;
    }

    if (password !== confirmPassword) {
      showError('Passwords do not match');
      return;
    }

    if (!ageVerified) {
      showError('You must confirm you are 21 or older to register');
      return;
    }

    const normalizedUsername = username.toLowerCase().replace(/\s/g, '').trim();
    if (!/^[a-z0-9_]{3,20}$/.test(normalizedUsername)) {
      showError('Username must be 3–20 characters: letters, numbers, underscores only');
      return;
    }

    if (usernameStatus === 'taken') {
      showError('That username is already taken — please choose another');
      return;
    }

    setLoading(true);
    try {
      await register(
        email,
        password,
        firstName,
        lastName,
        '1990-01-01',
        normalizedUsername,
        referralCode.trim() || undefined,
        rawPhone,
        profilePhoto || undefined,
      );
      router.replace('/(tabs)/home');
    } catch (error: any) {
      showError(error?.response?.data?.detail || error?.message || 'Something went wrong');
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

            {/* AVATAR PICKER */}
            <TouchableOpacity
              style={styles.avatarContainer}
              onPress={pickAvatar}
              activeOpacity={0.75}
              data-testid="register-avatar-picker"
            >
              {profilePhoto ? (
                <Image source={{ uri: profilePhoto }} style={styles.avatarImage} />
              ) : (
                <View style={styles.avatarPlaceholder}>
                  <Ionicons name="person-outline" size={36} color="#555" />
                </View>
              )}
              <View style={styles.avatarBadge}>
                <Ionicons name="camera" size={12} color="#fff" />
              </View>
              <Text style={styles.avatarHint}>
                {profilePhoto ? 'Tap to change photo' : 'Tap to upload photo (optional)'}
              </Text>
            </TouchableOpacity>

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

            {/* USERNAME with availability indicator */}
            <View style={styles.labelRow}>
              <Text style={styles.label}>
                Username <Text style={styles.required}>*</Text>
              </Text>
              {usernameStatus === 'checking' && (
                <View style={styles.statusRow}>
                  <ActivityIndicator size="small" color="#888" />
                  <Text style={styles.statusChecking}> Checking…</Text>
                </View>
              )}
              {usernameStatus === 'available' && (
                <Text style={styles.statusAvailable} data-testid="username-available">✓ Available</Text>
              )}
              {usernameStatus === 'taken' && (
                <Text style={styles.statusTaken} data-testid="username-taken">✗ Already taken</Text>
              )}
            </View>
            <TextInput
              style={[styles.input, usernameStatus === 'taken' && styles.inputError, usernameStatus === 'available' && styles.inputSuccess]}
              placeholder="e.g. johndoe123"
              placeholderTextColor="#666"
              value={username}
              onChangeText={(t) => setUsername(t.toLowerCase().replace(/\s/g, ''))}
              autoCapitalize="none"
              autoCorrect={false}
              maxLength={20}
              data-testid="register-username"
            />
            <Text style={styles.helperText}>This becomes your permanent referral ID</Text>

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

            <Text style={styles.label}>Phone Number</Text>
            <TextInput
              style={styles.input}
              placeholder="(608) 555-1234"
              placeholderTextColor="#666"
              value={phone}
              onChangeText={(t) => setPhone(formatPhone(t))}
              keyboardType="phone-pad"
              maxLength={14}
              data-testid="register-phone"
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

            <Text style={styles.label}>Confirm Password</Text>
            <TextInput
              style={styles.input}
              placeholder="Confirm your password"
              placeholderTextColor="#666"
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              secureTextEntry
              data-testid="register-confirm-password"
            />

            <TouchableOpacity
              style={styles.checkboxRow}
              onPress={() => setAgeVerified(!ageVerified)}
              activeOpacity={0.7}
              data-testid="register-age-verify"
            >
              <View style={[styles.checkbox, ageVerified && styles.checkboxChecked]}>
                {ageVerified && <Text style={styles.checkmark}>✓</Text>}
              </View>
              <Text style={styles.checkboxLabel}>I confirm I am 21 years of age or older</Text>
            </TouchableOpacity>

            <Text style={styles.label}>
              Referral Username <Text style={styles.optional}>(optional)</Text>
            </Text>
            <TextInput
              style={styles.input}
              placeholder="Enter a friend's username"
              placeholderTextColor="#666"
              value={referralCode}
              onChangeText={(t) => setReferralCode(t.toLowerCase().replace(/\s/g, ''))}
              autoCapitalize="none"
              autoCorrect={false}
              maxLength={20}
              data-testid="register-referral-code"
            />

            {errorMsg ? (
              <View style={styles.errorBox} data-testid="register-error-msg">
                <Text style={styles.errorText}>{errorMsg}</Text>
              </View>
            ) : null}

            <TouchableOpacity
              style={[styles.button, loading && styles.buttonDisabled]}
              onPress={handleRegister}
              disabled={loading}
              data-testid="register-submit-btn"
            >
              <Text style={styles.buttonText}>{loading ? 'Creating Account…' : 'Sign Up'}</Text>
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
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: -8,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
    marginBottom: -8,
  },
  required: {
    color: '#ef4444',
    fontWeight: '600',
  },
  optional: {
    color: theme.colors.textMuted,
    fontWeight: '400',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusChecking: {
    fontSize: 12,
    color: '#888',
  },
  statusAvailable: {
    fontSize: 12,
    fontWeight: '600',
    color: '#22c55e',
  },
  statusTaken: {
    fontSize: 12,
    fontWeight: '600',
    color: '#ef4444',
  },
  helperText: {
    color: theme.colors.textMuted,
    fontSize: 12,
    marginTop: -4,
    lineHeight: 17,
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
  inputError: {
    borderColor: '#ef4444',
  },
  inputSuccess: {
    borderColor: '#22c55e',
  },
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 4,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: theme.colors.inputBorder,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  checkboxChecked: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary,
  },
  checkmark: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    lineHeight: 16,
  },
  checkboxLabel: {
    color: '#fff',
    fontSize: 14,
    flex: 1,
    lineHeight: 20,
  },
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.12)',
    borderWidth: 1,
    borderColor: '#ef4444',
    borderRadius: 10,
    padding: 12,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
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
  avatarContainer: {
    alignItems: 'center',
    marginBottom: 8,
    position: 'relative',
  },
  avatarPlaceholder: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: theme.colors.inputBackground,
    borderWidth: 2,
    borderColor: theme.colors.inputBorder,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarImage: {
    width: 88,
    height: 88,
    borderRadius: 44,
    borderWidth: 2,
    borderColor: theme.colors.primary,
  },
  avatarBadge: {
    position: 'absolute',
    bottom: 24,
    right: '50%',
    marginRight: -50,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarHint: {
    marginTop: 8,
    fontSize: 12,
    color: theme.colors.textMuted,
    textAlign: 'center',
  },
});
