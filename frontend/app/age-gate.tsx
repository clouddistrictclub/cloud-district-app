import { View, Text, StyleSheet, TouchableOpacity, Alert, Platform } from 'react-native';
import { useState } from 'react';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { SafeAreaView } from 'react-native-safe-area-context';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';

export default function AgeGate() {
  const router = useRouter();
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  const [showPicker, setShowPicker] = useState(false);

  // Calculate the maximum date (21 years ago from today)
  const maxDate = new Date();
  maxDate.setFullYear(maxDate.getFullYear() - 21);

  // Calculate minimum reasonable date (100 years ago)
  const minDate = new Date();
  minDate.setFullYear(minDate.getFullYear() - 100);

  const handleDateChange = (event: any, date?: Date) => {
    if (Platform.OS === 'android') {
      setShowPicker(false);
    }
    if (date) {
      setSelectedDate(date);
    }
  };

  const handleContinue = async () => {
    if (!selectedDate) {
      Alert.alert('Date Required', 'Please select your date of birth');
      return;
    }

    const today = new Date();
    const age = (today.getTime() - selectedDate.getTime()) / (1000 * 60 * 60 * 24 * 365.25);

    if (age < 21) {
      Alert.alert(
        'Access Denied',
        'You must be 21 or older to access this app. This product is restricted to adults only.',
        [{ text: 'OK', style: 'default' }]
      );
      return;
    }

    await AsyncStorage.setItem('ageVerified', 'true');
    router.replace('/auth/login');
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.logoContainer}>
          <View style={styles.logoCircle}>
            <Ionicons name="cloud" size={48} color="#6366f1" />
          </View>
          <Text style={styles.title}>Cloud District Club</Text>
          <Text style={styles.subtitle}>Age Verification Required</Text>
        </View>
        
        <View style={styles.warningBox}>
          <Ionicons name="warning" size={24} color="#fff" />
          <View style={{ flex: 1 }}>
            <Text style={styles.warningTitle}>WARNING</Text>
            <Text style={styles.warningText}>
              This product contains nicotine. Nicotine is an addictive chemical.
            </Text>
          </View>
        </View>

        <View style={styles.verificationBox}>
          <Text style={styles.label}>Confirm Your Date of Birth</Text>
          <Text style={styles.sublabel}>You must be 21 or older to enter</Text>

          <TouchableOpacity 
            style={styles.datePickerButton}
            onPress={() => setShowPicker(true)}
          >
            <Ionicons name="calendar" size={24} color="#6366f1" />
            <View style={{ flex: 1 }}>
              <Text style={styles.datePickerLabel}>Date of Birth</Text>
              {selectedDate ? (
                <Text style={styles.datePickerValue}>{formatDate(selectedDate)}</Text>
              ) : (
                <Text style={styles.datePickerPlaceholder}>Tap to select your date of birth</Text>
              )}
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          {showPicker && (
            <View style={styles.pickerContainer}>
              <DateTimePicker
                value={selectedDate || maxDate}
                mode="date"
                display={Platform.OS === 'ios' ? 'spinner' : 'default'}
                onChange={handleDateChange}
                maximumDate={new Date()}
                minimumDate={minDate}
                textColor="#fff"
                themeVariant="dark"
              />
              {Platform.OS === 'ios' && (
                <TouchableOpacity 
                  style={styles.doneButton}
                  onPress={() => setShowPicker(false)}
                >
                  <Text style={styles.doneButtonText}>Done</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>

        <TouchableOpacity 
          style={[styles.button, !selectedDate && styles.buttonDisabled]} 
          onPress={handleContinue}
          disabled={!selectedDate}
        >
          <Text style={styles.buttonText}>Verify Age & Continue</Text>
          <Ionicons name="arrow-forward" size={20} color="#fff" />
        </TouchableOpacity>

        <Text style={styles.footerText}>
          By continuing, you confirm that you are 21 years of age or older
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logoCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#1a1a1a',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
  },
  warningBox: {
    flexDirection: 'row',
    backgroundColor: '#dc2626',
    padding: 16,
    borderRadius: 12,
    marginBottom: 32,
    gap: 12,
    alignItems: 'flex-start',
  },
  warningTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  warningText: {
    fontSize: 14,
    color: '#fff',
    lineHeight: 20,
  },
  verificationBox: {
    marginBottom: 24,
  },
  label: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  sublabel: {
    fontSize: 14,
    color: '#999',
    marginBottom: 20,
  },
  datePickerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderWidth: 2,
    borderColor: '#333',
    borderRadius: 12,
    padding: 16,
    gap: 12,
  },
  datePickerLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  datePickerValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  datePickerPlaceholder: {
    fontSize: 16,
    color: '#666',
  },
  pickerContainer: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    marginTop: 12,
    overflow: 'hidden',
  },
  doneButton: {
    backgroundColor: '#6366f1',
    padding: 16,
    alignItems: 'center',
  },
  doneButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  button: {
    flexDirection: 'row',
    backgroundColor: '#6366f1',
    padding: 18,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 16,
  },
  buttonDisabled: {
    backgroundColor: '#333',
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  footerText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    lineHeight: 18,
  },
});