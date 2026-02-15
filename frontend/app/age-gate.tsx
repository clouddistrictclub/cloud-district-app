import { View, Text, StyleSheet, TouchableOpacity, Alert, Platform, Modal, TextInput } from 'react-native';
import { useState, useRef } from 'react';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme';

let DateTimePicker: any = null;
if (Platform.OS !== 'web') {
  DateTimePicker = require('@react-native-community/datetimepicker').default;
}

export default function AgeGate() {
  const router = useRouter();
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  const [showPicker, setShowPicker] = useState(false);
  const [tempDate, setTempDate] = useState<Date>(new Date(2002, 0, 1));
  const [webDateValue, setWebDateValue] = useState('');

  const maxDate = new Date();
  maxDate.setFullYear(maxDate.getFullYear() - 21);

  const minDate = new Date();
  minDate.setFullYear(minDate.getFullYear() - 100);

  const openDatePicker = () => {
    if (Platform.OS === 'web') {
      // On web, the input is always visible — clicking the button area focuses the hidden input
      return;
    }
    setTempDate(selectedDate || maxDate);
    setShowPicker(true);
  };

  const handleWebDateChange = (dateString: string) => {
    setWebDateValue(dateString);
    if (dateString) {
      const parts = dateString.split('-');
      const date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
      if (!isNaN(date.getTime())) {
        setSelectedDate(date);
      }
    } else {
      setSelectedDate(undefined);
    }
  };

  const handleDateChange = (event: any, date?: Date) => {
    if (Platform.OS === 'android') {
      setShowPicker(false);
      if (event.type === 'set' && date) {
        setSelectedDate(date);
      }
    } else {
      if (date) {
        setTempDate(date);
      }
    }
  };

  const handleIOSConfirm = () => {
    setSelectedDate(tempDate);
    setShowPicker(false);
  };

  const handleCancel = () => {
    setShowPicker(false);
  };

  const handleContinue = async () => {
    if (!selectedDate) {
      if (Platform.OS === 'web') {
        alert('Please select your date of birth');
      } else {
        Alert.alert('Date Required', 'Please select your date of birth');
      }
      return;
    }

    const today = new Date();
    const age = (today.getTime() - selectedDate.getTime()) / (1000 * 60 * 60 * 24 * 365.25);

    if (age < 21) {
      if (Platform.OS === 'web') {
        alert('You must be 21 or older to access this app. This product is restricted to adults only.');
      } else {
        Alert.alert(
          'Access Denied',
          'You must be 21 or older to access this app. This product is restricted to adults only.',
          [{ text: 'OK', style: 'default' }]
        );
      }
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

  const maxDateStr = `${maxDate.getFullYear()}-${String(maxDate.getMonth() + 1).padStart(2, '0')}-${String(maxDate.getDate()).padStart(2, '0')}`;
  const minDateStr = `${minDate.getFullYear()}-${String(minDate.getMonth() + 1).padStart(2, '0')}-${String(minDate.getDate()).padStart(2, '0')}`;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.logoContainer}>
          <View style={styles.logoCircle}>
            <Ionicons name="cloud" size={48} color={theme.colors.primary} />
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

          {Platform.OS === 'web' ? (
            <View style={styles.datePickerButton} data-testid="dob-web-container">
              <Ionicons name="calendar" size={24} color={theme.colors.primary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.datePickerLabel}>Date of Birth</Text>
                <input
                  type="date"
                  value={webDateValue}
                  max={maxDateStr}
                  min={minDateStr}
                  onChange={(e: any) => handleWebDateChange(e.target.value)}
                  data-testid="dob-web-input"
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: selectedDate ? '#fff' : '#666',
                    fontSize: 16,
                    fontWeight: '600',
                    outline: 'none',
                    width: '100%',
                    padding: 0,
                    fontFamily: 'inherit',
                    colorScheme: 'dark',
                  }}
                />
              </View>
            </View>
          ) : (
            <TouchableOpacity 
              style={styles.datePickerButton}
              onPress={openDatePicker}
              activeOpacity={0.7}
              data-testid="dob-native-button"
            >
              <Ionicons name="calendar" size={24} color={theme.colors.primary} />
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
          )}
        </View>

        <TouchableOpacity 
          style={[styles.button, !selectedDate && styles.buttonDisabled]} 
          onPress={handleContinue}
          disabled={!selectedDate}
          activeOpacity={0.8}
          data-testid="age-verify-btn"
        >
          <Text style={styles.buttonText}>Verify Age & Continue</Text>
          <Ionicons name="arrow-forward" size={20} color="#fff" />
        </TouchableOpacity>

        <Text style={styles.footerText}>
          By continuing, you confirm that you are 21 years of age or older
        </Text>
      </View>

      {/* iOS Modal Date Picker */}
      {Platform.OS === 'ios' && showPicker && DateTimePicker && (
        <Modal
          transparent={true}
          animationType="slide"
          visible={showPicker}
          onRequestClose={handleCancel}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <TouchableOpacity onPress={handleCancel}>
                  <Text style={styles.modalButton}>Cancel</Text>
                </TouchableOpacity>
                <Text style={styles.modalTitle}>Select Date of Birth</Text>
                <TouchableOpacity onPress={handleIOSConfirm}>
                  <Text style={[styles.modalButton, styles.modalButtonDone]}>Done</Text>
                </TouchableOpacity>
              </View>
              <DateTimePicker
                value={tempDate}
                mode="date"
                display="spinner"
                onChange={handleDateChange}
                maximumDate={new Date()}
                minimumDate={minDate}
                textColor="#fff"
                themeVariant="dark"
                style={styles.iosPicker}
              />
            </View>
          </View>
        </Modal>
      )}

      {/* Android Native Date Picker */}
      {Platform.OS === 'android' && showPicker && DateTimePicker && (
        <DateTimePicker
          value={tempDate}
          mode="date"
          display="default"
          onChange={handleDateChange}
          maximumDate={new Date()}
          minimumDate={minDate}
        />
      )}
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
    backgroundColor: theme.colors.card,
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
    color: theme.colors.textMuted,
    textAlign: 'center',
  },
  warningBox: {
    flexDirection: 'row',
    backgroundColor: theme.colors.primary,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
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
    color: theme.colors.textMuted,
    marginBottom: 20,
  },
  datePickerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    borderWidth: 2,
    borderColor: '#333',
    borderRadius: theme.borderRadius.lg,
    padding: 18,
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
  button: {
    flexDirection: 'row',
    backgroundColor: theme.colors.primary,
    padding: 18,
    borderRadius: theme.borderRadius.lg,
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
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalContent: {
    backgroundColor: theme.colors.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingBottom: 40,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  modalButton: {
    fontSize: 16,
    color: theme.colors.primary,
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  modalButtonDone: {
    fontWeight: '600',
  },
  iosPicker: {
    height: 200,
  },
});
