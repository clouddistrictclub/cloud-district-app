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
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
    marginBottom: 32,
  },
  warningBox: {
    backgroundColor: '#dc2626',
    padding: 16,
    borderRadius: 8,
    marginBottom: 32,
  },
  warningTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  warningText: {
    fontSize: 14,
    color: '#fff',
    lineHeight: 20,
  },
  label: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 8,
  },
  sublabel: {
    fontSize: 14,
    color: '#999',
    marginBottom: 24,
  },
  dateContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 32,
  },
  dateInput: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    padding: 16,
    color: '#fff',
    fontSize: 18,
    textAlign: 'center',
  },
  dateInputYear: {
    flex: 1.5,
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    padding: 16,
    color: '#fff',
    fontSize: 18,
    textAlign: 'center',
  },
  dateSeparator: {
    color: '#666',
    fontSize: 24,
    marginHorizontal: 8,
  },
  button: {
    backgroundColor: '#6366f1',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});