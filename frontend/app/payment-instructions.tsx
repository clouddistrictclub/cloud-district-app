import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Share } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

export default function PaymentInstructions() {
  const router = useRouter();
  const { orderId, method, amount } = useLocalSearchParams();

  const paymentInfo: any = {
    zelle: {
      title: 'Pay with Zelle',
      username: '6084179336',
      instructions: [
        'Open your banking app',
        'Select Zelle',
        'Send to: 6084179336',
        `Amount: $${amount}`,
        `Memo: Order #${orderId?.slice(-6)}`,
      ],
      deepLink: null,
    },
    venmo: {
      title: 'Pay with Venmo',
      username: '@CloudDistrictClub',
      instructions: [
        'Tap "Open Venmo" button below',
        'Confirm the pre-filled amount',
        'Add order number to note',
        'Complete payment',
      ],
      deepLink: `venmo://paycharge?txn=pay&recipients=CloudDistrictClub&amount=${amount}&note=Order%20${orderId?.slice(-6)}`,
    },
    cashapp: {
      title: 'Pay with Cash App',
      username: '$CloudDistrictClub',
      instructions: [
        'Tap "Open Cash App" button below',
        'Confirm the pre-filled amount',
        'Add order number to note',
        'Complete payment',
      ],
      deepLink: `https://cash.app/$CloudDistrictClub/${amount}`,
    },
    chime: {
      title: 'Pay with Chime',
      username: '$CloudDistrictClub',
      instructions: [
        'Open Chime app',
        'Select Pay Anyone',
        'Send to: $CloudDistrictClub',
        `Amount: $${amount}`,
        `Note: Order #${orderId?.slice(-6)}`,
      ],
      deepLink: null,
    },
  };

  const info = paymentInfo[method as string];

  const handleShare = async () => {
    try {
      await Share.share({
        message: `${info.title}\nUsername: ${info.username}\nAmount: $${amount}\nOrder: #${orderId}`,
      });
    } catch (error) {
      console.error('Share failed:', error);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Ionicons name="checkmark-circle" size={64} color="#10b981" />
        <Text style={styles.title}>Order Placed!</Text>
        <Text style={styles.subtitle}>Order #{orderId}</Text>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.warningBox}>
          <Ionicons name="time" size={24} color="#fbbf24" />
          <View style={{ flex: 1 }}>
            <Text style={styles.warningTitle}>Payment Required</Text>
            <Text style={styles.warningText}>
              Your order will be prepared once payment is confirmed by our team.
            </Text>
          </View>
        </View>

        <View style={styles.paymentCard}>
          <Text style={styles.cardTitle}>{info.title}</Text>
          
          <View style={styles.amountBox}>
            <Text style={styles.amountLabel}>Amount to Send</Text>
            <Text style={styles.amountValue}>${amount}</Text>
          </View>

          <View style={styles.usernameBox}>
            <Text style={styles.usernameLabel}>Send to</Text>
            <Text style={styles.usernameValue}>{info.username}</Text>
            <TouchableOpacity onPress={handleShare}>
              <Ionicons name="share-outline" size={20} color="#6366f1" />
            </TouchableOpacity>
          </View>

          <View style={styles.instructionsBox}>
            <Text style={styles.instructionsTitle}>Instructions</Text>
            {info.instructions.map((instruction: string, index: number) => (
              <View key={index} style={styles.instructionRow}>
                <View style={styles.stepNumber}>
                  <Text style={styles.stepText}>{index + 1}</Text>
                </View>
                <Text style={styles.instructionText}>{instruction}</Text>
              </View>
            ))}
          </View>

          <View style={styles.noteBox}>
            <Ionicons name="alert-circle" size={20} color="#fbbf24" />
            <Text style={styles.noteText}>
              <Text style={{ fontWeight: 'bold' }}>Important:</Text> Include your order number in the payment note
            </Text>
          </View>
        </View>

        <View style={styles.nextStepsCard}>
          <Text style={styles.nextStepsTitle}>What Happens Next?</Text>
          <View style={styles.stepBox}>
            <Ionicons name="send" size={20} color="#6366f1" />
            <Text style={styles.stepBoxText}>Send payment using instructions above</Text>
          </View>
          <View style={styles.stepBox}>
            <Ionicons name="checkmark" size={20} color="#6366f1" />
            <Text style={styles.stepBoxText}>We confirm your payment</Text>
          </View>
          <View style={styles.stepBox}>
            <Ionicons name="bag" size={20} color="#6366f1" />
            <Text style={styles.stepBoxText}>Your order is prepared</Text>
          </View>
          <View style={styles.stepBox}>
            <Ionicons name="notifications" size={20} color="#6366f1" />
            <Text style={styles.stepBoxText}>You'll be notified when ready for pickup</Text>
          </View>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity 
          style={styles.doneButton}
          onPress={() => router.replace('/(tabs)/orders')}
        >
          <Text style={styles.doneButtonText}>View My Orders</Text>
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
  header: {
    alignItems: 'center',
    padding: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 16,
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  content: {
    flex: 1,
    padding: 16,
  },
  warningBox: {
    flexDirection: 'row',
    backgroundColor: '#fbbf24',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    gap: 12,
  },
  warningTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#000',
    marginBottom: 4,
  },
  warningText: {
    fontSize: 14,
    color: '#000',
    lineHeight: 20,
  },
  paymentCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
  },
  amountBox: {
    backgroundColor: '#6366f1',
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  amountLabel: {
    fontSize: 14,
    color: '#e0e7ff',
    marginBottom: 4,
  },
  amountValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#fff',
  },
  usernameBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0c0c0c',
    padding: 16,
    borderRadius: 8,
    marginBottom: 20,
  },
  usernameLabel: {
    fontSize: 12,
    color: '#666',
    marginRight: 8,
  },
  usernameValue: {
    flex: 1,
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
  },
  instructionsBox: {
    marginBottom: 16,
  },
  instructionsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  instructionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 12,
  },
  stepNumber: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#6366f1',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#fff',
  },
  instructionText: {
    flex: 1,
    fontSize: 14,
    color: '#ccc',
  },
  noteBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#2a2a1a',
    padding: 12,
    borderRadius: 8,
    gap: 8,
  },
  noteText: {
    flex: 1,
    fontSize: 13,
    color: '#fbbf24',
    lineHeight: 18,
  },
  nextStepsCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 20,
  },
  nextStepsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  stepBox: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 12,
  },
  stepBoxText: {
    flex: 1,
    fontSize: 14,
    color: '#ccc',
  },
  footer: {
    padding: 16,
    backgroundColor: '#1a1a1a',
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  doneButton: {
    backgroundColor: '#6366f1',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  doneButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});