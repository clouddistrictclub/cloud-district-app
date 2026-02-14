import { View, Text, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function UsersManagement() {
  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.text}>Users Management - Coming in Phase 3</Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0c0c0c', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#999', fontSize: 16 },
});