import { View, Text, StyleSheet, TouchableOpacity, TextInput, Alert } from 'react-native';
import { useState } from 'react';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function AgeGate() {
  const router = useRouter();
  const [month, setMonth] = useState('');
  const [day, setDay] = useState('');
  const [year, setYear] = useState('');

  const handleContinue = async () => {
    if (!month || !day || !year) {
      Alert.alert('Error', 'Please enter your complete date of birth');
      return;
    }

    const birthDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    const today = new Date();
    const age = (today.getTime() - birthDate.getTime()) / (1000 * 60 * 60 * 24 * 365.25);

    if (age < 21) {
      Alert.alert(
        'Age Requirement',
        'You must be 21 or older to access this app.',
        [{ text: 'OK' }]
      );
      return;
    }

    await AsyncStorage.setItem('ageVerified', 'true');
    router.replace('/auth/login');
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Cloud District Club</Text>
        <Text style={styles.subtitle}>Age Verification Required</Text>
        
        <View style={styles.warningBox}>
          <Text style={styles.warningTitle}>⚠️ WARNING</Text>
          <Text style={styles.warningText}>
            This product contains nicotine. Nicotine is an addictive chemical.
          </Text>
        </View>

        <Text style={styles.label}>Enter Your Date of Birth</Text>
        <Text style={styles.sublabel}>You must be 21 or older to continue</Text>

        <View style={styles.dateContainer}>
          <TextInput
            style={styles.dateInput}
            placeholder="MM"
            placeholderTextColor="#666"
            value={month}
            onChangeText={setMonth}
            keyboardType="numeric"
            maxLength={2}
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
          />
        </View>

        <TouchableOpacity style={styles.button} onPress={handleContinue}>
          <Text style={styles.buttonText}>Continue</Text>
        </TouchableOpacity>
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