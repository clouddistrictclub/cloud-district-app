import { View, Text, StyleSheet, TouchableOpacity, Platform, BackHandler } from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme';
import HeroBanner from '../components/HeroBanner';

function persistAgeVerified() {
  if (Platform.OS === 'web') {
    try { window.localStorage.setItem('cloudDistrictAgeVerified', 'true'); } catch {}
    // Keep legacy key too so index.tsx routing still works
    try { window.localStorage.setItem('ageVerified', 'true'); } catch {}
  } else {
    AsyncStorage.setItem('cloudDistrictAgeVerified', 'true');
    AsyncStorage.setItem('ageVerified', 'true');
  }
}

export default function AgeGate() {
  const router = useRouter();

  const handleEnter = () => {
    persistAgeVerified();
    router.replace('/auth/login');
  };

  const handleExit = () => {
    if (Platform.OS !== 'web') {
      BackHandler.exitApp();
    } else {
      // Web: can't force-close — show a clear message by navigating to a dead-end
      if (typeof window !== 'undefined') {
        document.body.innerHTML =
          '<div style="background:#0c0c0c;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:sans-serif;">' +
          '<p style="color:#fff;font-size:20px;text-align:center;max-width:360px;line-height:1.5">You must be 21 or older to access Cloud District Club.<br><br>Please close this tab.</p>' +
          '</div>';
      }
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <HeroBanner testID="agegate-hero" />

      <View style={styles.content}>

        <View style={styles.titleBlock}>
          <Text style={styles.title}>Age Verification</Text>
          <Text style={styles.subtitle}>You must be 21+ to enter Cloud District</Text>
        </View>

        <View style={styles.warningBox}>
          <Ionicons name="warning" size={22} color="#fff" />
          <Text style={styles.warningText}>
            This product contains nicotine. Nicotine is an addictive chemical.
          </Text>
        </View>

        <TouchableOpacity
          style={styles.enterButton}
          onPress={handleEnter}
          activeOpacity={0.85}
          data-testid="age-enter-btn"
        >
          <Ionicons name="checkmark-circle-outline" size={22} color="#fff" />
          <Text style={styles.enterButtonText}>I am 21+  Enter</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.exitButton}
          onPress={handleExit}
          activeOpacity={0.7}
          data-testid="age-exit-btn"
        >
          <Text style={styles.exitButtonText}>Exit</Text>
        </TouchableOpacity>

        <Text style={styles.disclaimer}>
          By entering, you confirm you are 21 years of age or older and agree to our terms.
        </Text>

      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    flex: 1,
    paddingHorizontal: 28,
    paddingTop: 8,
    paddingBottom: 32,
  },
  titleBlock: {
    alignItems: 'center',
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 16,
    color: theme.colors.textMuted,
    textAlign: 'center',
    lineHeight: 22,
  },
  warningBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    marginBottom: 40,
  },
  warningText: {
    flex: 1,
    fontSize: 13,
    color: '#fff',
    lineHeight: 19,
  },
  enterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.borderRadius.lg,
    paddingVertical: 18,
    marginBottom: 14,
  },
  enterButtonText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: 0.3,
  },
  exitButton: {
    alignItems: 'center',
    paddingVertical: 14,
    marginBottom: 24,
  },
  exitButtonText: {
    fontSize: 15,
    color: theme.colors.textMuted,
    fontWeight: '500',
  },
  disclaimer: {
    fontSize: 12,
    color: '#555',
    textAlign: 'center',
    lineHeight: 17,
  },
});
