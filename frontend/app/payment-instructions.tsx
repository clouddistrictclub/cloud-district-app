import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, Linking, Platform } from 'react-native';
import { useState } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';

export default function PaymentInstructions() {
  const router = useRouter();
  const { orderId, method, amount } = useLocalSearchParams();
  const [copied, setCopied] = useState<string | null>(null);

  const shortOrderId = typeof orderId === 'string' ? orderId.slice(-6).toUpperCase() : '';
  const amountStr = typeof amount === 'string' ? amount : '0.00';

  const copyToClipboard = async (text: string, label: string) => {
    await Clipboard.setStringAsync(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleDeepLink = async (url: string, appName: string) => {
    try {
      const canOpen = await Linking.canOpenURL(url);
      if (canOpen) {
        await Linking.openURL(url);
      } else {
        Alert.alert(
          `${appName} Not Found`,
          `Please install ${appName} or copy the payment details and complete manually.`,
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      Alert.alert(
        'Unable to Open App',
        `Please copy the payment details and open ${appName} manually.`,
        [{ text: 'OK' }]
      );
    }
  };

  const handleContactSupport = () => {
    Alert.alert(
      'Need Help?',
      'Contact us for payment assistance',
      [
        {
          text: 'Call/Text',
          onPress: () => Linking.openURL('sms:6084179336')
        },
        {
          text: 'Cancel',
          style: 'cancel'
        }
      ]
    );
  };

  const paymentInfo: any = {
    zelle: {
      title: 'Pay with Zelle',
      username: '6084179336',
      icon: 'flash',
      color: '#6d1ed4',
      instructions: [
        'Open your banking app',
        'Select Zelle',
        'Send to: 6084179336',
        `Add memo: Order #${shortOrderId}`
      ],
      deepLink: null, // Zelle is bank-dependent, no universal deep link
      canDeepLink: false,
    },
    venmo: {
      title: 'Pay with Venmo',
      username: '@CloudDistrictClub',
      icon: 'logo-venmo',
      color: '#008CFF',
      instructions: [
        'Tap "Open Venmo" below',
        'Confirm pre-filled amount',
        'Verify order number in note',
        'Complete payment'
      ],
      deepLink: `venmo://paycharge?txn=pay&recipients=CloudDistrictClub&amount=${amountStr}&note=Order%20%23${shortOrderId}`,
      canDeepLink: true,
    },
    cashapp: {
      title: 'Pay with Cash App',
      username: '$CloudDistrictClub',
      icon: 'cash',
      color: '#00D64F',
      instructions: [
        'Tap "Open Cash App" below',
        'Amount will be pre-filled',
        'Add this to note: Order #' + shortOrderId,
        'Complete payment'
      ],
      deepLink: `https://cash.app/$CloudDistrictClub/${amountStr}`,
      canDeepLink: true,
    },
    chime: {
      title: 'Pay with Chime',
      username: '$CloudDistrictClub',
      icon: 'card',
      color: '#00C853',
      instructions: [
        'Open Chime app',
        'Select "Pay Anyone"',
        'Send to: $CloudDistrictClub',
        'Copy amount and order # below'
      ],
      deepLink: null, // Chime doesn't support deep linking
      canDeepLink: false,
    },
  };

  const info = paymentInfo[method as string];

  if (!info) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.errorText}>Invalid payment method</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={[styles.iconCircle, { backgroundColor: info.color + '20' }]}>
            <Ionicons name={info.icon as any} size={48} color={info.color} />
          </View>
          <Text style={styles.successTitle}>Order Placed!</Text>
          <View style={styles.orderBadge}>
            <Text style={styles.orderBadgeText}>Order #{shortOrderId}</Text>
          </View>
        </View>

        <View style={styles.warningBox}>
          <Ionicons name="alert-circle" size={24} color="#fbbf24" />
          <View style={{ flex: 1 }}>
            <Text style={styles.warningTitle}>External Payment Required</Text>
            <Text style={styles.warningText}>
              Your order will be prepared once payment is confirmed by our team.
            </Text>
          </View>
        </View>

        <View style={styles.paymentCard}>
          <Text style={styles.cardTitle}>{info.title}</Text>
          
          <View style={styles.amountContainer}>
            <Text style={styles.amountLabel}>Total Amount Due</Text>
            <Text style={styles.amountValue}>${amountStr}</Text>
            <TouchableOpacity 
              style={styles.copyButton}
              onPress={() => copyToClipboard(amountStr, 'amount')}
            >
              <Ionicons 
                name={copied === 'amount' ? 'checkmark-circle' : 'copy'} 
                size={20} 
                color={copied === 'amount' ? '#10b981' : '#6366f1'} 
              />
              <Text style={[styles.copyButtonText, copied === 'amount' && styles.copiedText]}>
                {copied === 'amount' ? 'Copied!' : 'Copy Amount'}
              </Text>
            </TouchableOpacity>
          </View>

          <View style={styles.recipientContainer}>
            <View style={{ flex: 1 }}>
              <Text style={styles.recipientLabel}>Send To</Text>
              <Text style={styles.recipientValue}>{info.username}</Text>
            </View>
            <TouchableOpacity 
              style={styles.copyButton}
              onPress={() => copyToClipboard(info.username, 'username')}
            >
              <Ionicons 
                name={copied === 'username' ? 'checkmark-circle' : 'copy'} 
                size={20} 
                color={copied === 'username' ? '#10b981' : '#6366f1'} 
              />
              <Text style={[styles.copyButtonText, copied === 'username' && styles.copiedText]}>
                {copied === 'username' ? 'Copied!' : 'Copy'}
              </Text>
            </TouchableOpacity>
          </View>

          <View style={styles.orderNumberContainer}>
            <View style={{ flex: 1 }}>
              <Text style={styles.orderNumberLabel}>Add to Payment Note</Text>
              <Text style={styles.orderNumberValue}>Order #{shortOrderId}</Text>
            </View>
            <TouchableOpacity 
              style={styles.copyButton}
              onPress={() => copyToClipboard(`Order #${shortOrderId}`, 'order')}
            >
              <Ionicons 
                name={copied === 'order' ? 'checkmark-circle' : 'copy'} 
                size={20} 
                color={copied === 'order' ? '#10b981' : '#6366f1'} 
              />
              <Text style={[styles.copyButtonText, copied === 'order' && styles.copiedText]}>
                {copied === 'order' ? 'Copied!' : 'Copy Order #'}
              </Text>
            </TouchableOpacity>
          </View>

          {info.canDeepLink && (
            <TouchableOpacity 
              style={[styles.openAppButton, { backgroundColor: info.color }]}
              onPress={() => handleDeepLink(info.deepLink, info.title.replace('Pay with ', ''))}
            >
              <Ionicons name="open" size={20} color="#fff" />
              <Text style={styles.openAppButtonText}>
                Open {info.title.replace('Pay with ', '')}
              </Text>
            </TouchableOpacity>
          )}

          <View style={styles.instructionsContainer}>
            <Text style={styles.instructionsTitle}>Payment Steps</Text>
            {info.instructions.map((instruction: string, index: number) => (
              <View key={index} style={styles.instructionRow}>
                <View style={styles.stepCircle}>
                  <Text style={styles.stepNumber}>{index + 1}</Text>
                </View>
                <Text style={styles.instructionText}>{instruction}</Text>
              </View>
            ))}
          </View>

          <View style={styles.importantNote}>
            <Ionicons name="warning" size={20} color="#fbbf24" />
            <Text style={styles.importantNoteText}>
              <Text style={{ fontWeight: 'bold' }}>Important: </Text>
              Include Order #{shortOrderId} in your payment note
            </Text>
          </View>
        </View>

        <View style={styles.nextStepsCard}>
          <Text style={styles.nextStepsTitle}>What Happens Next?</Text>
          <View style={styles.timelineContainer}>
            <View style={styles.timelineStep}>
              <View style={[styles.timelineDot, styles.timelineDotActive]} />
              <View style={styles.timelineContent}>
                <Text style={styles.timelineTitle}>1. Send Payment</Text>
                <Text style={styles.timelineDescription}>
                  Complete payment using the details above
                </Text>
              </View>
            </View>
            <View style={styles.timelineLine} />
            <View style={styles.timelineStep}>
              <View style={styles.timelineDot} />
              <View style={styles.timelineContent}>
                <Text style={styles.timelineTitle}>2. We Confirm</Text>
                <Text style={styles.timelineDescription}>
                  Our team verifies your payment
                </Text>
              </View>
            </View>
            <View style={styles.timelineLine} />
            <View style={styles.timelineStep}>
              <View style={styles.timelineDot} />
              <View style={styles.timelineContent}>
                <Text style={styles.timelineTitle}>3. Order Prepared</Text>
                <Text style={styles.timelineDescription}>
                  Your order is prepared for pickup
                </Text>
              </View>
            </View>
            <View style={styles.timelineLine} />
            <View style={styles.timelineStep}>
              <View style={styles.timelineDot} />
              <View style={styles.timelineContent}>
                <Text style={styles.timelineTitle}>4. Ready Notification</Text>
                <Text style={styles.timelineDescription}>
                  You'll be notified when ready
                </Text>
              </View>
            </View>
          </View>
        </View>

        <TouchableOpacity style={styles.helpButton} onPress={handleContactSupport}>
          <Ionicons name="help-circle" size={24} color="#6366f1" />
          <Text style={styles.helpButtonText}>Need Help with Payment?</Text>
          <Ionicons name="chevron-forward" size={20} color="#666" />
        </TouchableOpacity>
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
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 100,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  successTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  orderBadge: {
    backgroundColor: '#6366f1',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  orderBadgeText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  warningBox: {
    flexDirection: 'row',
    backgroundColor: '#2a2a1a',
    borderLeftWidth: 4,
    borderLeftColor: '#fbbf24',
    padding: 16,
    borderRadius: 8,
    marginBottom: 24,
    gap: 12,
  },
  warningTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fbbf24',
    marginBottom: 4,
  },
  warningText: {
    fontSize: 14,
    color: '#ccc',
    lineHeight: 20,
  },
  paymentCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 24,
  },
  amountContainer: {
    backgroundColor: '#6366f1',
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  amountLabel: {
    fontSize: 14,
    color: '#e0e7ff',
    marginBottom: 8,
  },
  amountValue: {
    fontSize: 42,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  recipientContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0c0c0c',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  recipientLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  recipientValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  orderNumberContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0c0c0c',
    padding: 16,
    borderRadius: 12,
    marginBottom: 20,
  },
  orderNumberLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  orderNumberValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#6366f1',
  },
  copyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#333',
  },
  copyButtonText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '600',
  },
  copiedText: {
    color: '#10b981',
  },
  openAppButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 18,
    borderRadius: 12,
    marginBottom: 20,
  },
  openAppButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
  },
  instructionsContainer: {
    marginBottom: 16,
  },
  instructionsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  instructionRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 16,
    gap: 12,
  },
  stepCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#6366f1',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepNumber: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#fff',
  },
  instructionText: {
    flex: 1,
    fontSize: 14,
    color: '#ccc',
    lineHeight: 20,
    paddingTop: 4,
  },
  importantNote: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#2a2a1a',
    padding: 12,
    borderRadius: 8,
    gap: 8,
  },
  importantNoteText: {
    flex: 1,
    fontSize: 13,
    color: '#fbbf24',
    lineHeight: 18,
  },
  nextStepsCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  nextStepsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
  },
  timelineContainer: {
    paddingLeft: 8,
  },
  timelineStep: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 16,
  },
  timelineDot: {
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: '#333',
    marginTop: 4,
  },
  timelineDotActive: {
    backgroundColor: '#6366f1',
  },
  timelineLine: {
    width: 2,
    height: 32,
    backgroundColor: '#333',
    marginLeft: 7,
    marginVertical: 4,
  },
  timelineContent: {
    flex: 1,
    paddingBottom: 8,
  },
  timelineTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  timelineDescription: {
    fontSize: 14,
    color: '#999',
    lineHeight: 20,
  },
  helpButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    padding: 16,
    borderRadius: 12,
    gap: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  helpButtonText: {
    flex: 1,
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    backgroundColor: '#1a1a1a',
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  doneButton: {
    backgroundColor: '#6366f1',
    padding: 18,
    borderRadius: 12,
    alignItems: 'center',
  },
  doneButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  errorText: {
    fontSize: 18,
    color: '#dc2626',
    textAlign: 'center',
    marginTop: 100,
  },
});
