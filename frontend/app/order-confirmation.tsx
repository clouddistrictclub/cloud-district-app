import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking, Platform } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme';

const STORE_NAME = 'Cloud District Club';
const STORE_ADDRESS = '123 Main St, Suite 100, Los Angeles, CA 90001';
const STORE_COORDS = { lat: 34.0522, lng: -118.2437 };

export default function OrderConfirmation() {
  const router = useRouter();
  const { orderId, status, paymentMethod, total, pickupTime } = useLocalSearchParams();

  const shortOrderId = typeof orderId === 'string' ? orderId.slice(-6).toUpperCase() : '';
  const orderStatus = typeof status === 'string' ? status : 'Pending';
  const method = typeof paymentMethod === 'string' ? paymentMethod : '';
  const amountStr = typeof total === 'string' ? total : '0.00';
  const pickup = typeof pickupTime === 'string' ? pickupTime : '';
  const isCash = method === 'Cash on Pickup';

  const openInMaps = () => {
    const { lat, lng } = STORE_COORDS;
    const label = encodeURIComponent(STORE_NAME);
    const url = Platform.select({
      ios: `maps:0,0?q=${label}@${lat},${lng}`,
      android: `geo:${lat},${lng}?q=${lat},${lng}(${label})`,
      default: `https://www.google.com/maps/search/?api=1&query=${lat},${lng}&query_place_id=${label}`,
    });
    if (url) Linking.openURL(url);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        {/* Success Header */}
        <View style={styles.header}>
          <View style={styles.checkCircle} data-testid="order-confirmation-check">
            <Ionicons name="checkmark" size={48} color="#fff" />
          </View>
          <Text style={styles.successTitle} data-testid="order-confirmation-title">Order Confirmed!</Text>
          <View style={styles.orderBadge}>
            <Text style={styles.orderBadgeText} data-testid="order-confirmation-id">Order #{shortOrderId}</Text>
          </View>
        </View>

        {/* Order Details Card */}
        <View style={styles.detailsCard}>
          <Text style={styles.cardTitle}>Order Details</Text>

          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Status</Text>
            <View style={[styles.statusBadge, isCash && styles.statusBadgeCash]}>
              <Text style={[styles.statusText, isCash && styles.statusTextCash]} data-testid="order-confirmation-status">
                {orderStatus}
              </Text>
            </View>
          </View>

          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Payment</Text>
            <Text style={styles.detailValue} data-testid="order-confirmation-payment">{method}</Text>
          </View>

          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Total</Text>
            <Text style={styles.detailValueBold} data-testid="order-confirmation-total">${amountStr}</Text>
          </View>

          {pickup ? (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Pickup</Text>
              <Text style={styles.detailValue} data-testid="order-confirmation-pickup">{pickup}</Text>
            </View>
          ) : null}
        </View>

        {/* Pickup Instructions */}
        <View style={styles.pickupCard}>
          <View style={styles.pickupHeader}>
            <Ionicons name="storefront" size={24} color={theme.colors.primary} />
            <Text style={styles.pickupTitle}>Pickup Instructions</Text>
          </View>

          <View style={styles.instructionStep}>
            <View style={styles.stepDot} />
            <Text style={styles.instructionText}>
              {isCash
                ? 'Have your cash ready at pickup — exact change appreciated.'
                : 'Complete your payment using the method selected.'}
            </Text>
          </View>
          <View style={styles.instructionStep}>
            <View style={styles.stepDot} />
            <Text style={styles.instructionText}>
              Head to the store during your selected pickup window.
            </Text>
          </View>
          <View style={styles.instructionStep}>
            <View style={styles.stepDot} />
            <Text style={styles.instructionText}>
              Show your order number <Text style={styles.boldAccent}>#{shortOrderId}</Text> at the counter.
            </Text>
          </View>
          <View style={styles.instructionStep}>
            <View style={styles.stepDot} />
            <Text style={styles.instructionText}>
              A valid 21+ ID is required for all pickups.
            </Text>
          </View>
        </View>

        {/* Store Location Card */}
        <View style={styles.locationCard}>
          <View style={styles.locationHeader}>
            <Ionicons name="location" size={24} color={theme.colors.danger} />
            <View style={{ flex: 1 }}>
              <Text style={styles.storeName} data-testid="store-name">{STORE_NAME}</Text>
              <Text style={styles.storeAddress} data-testid="store-address">{STORE_ADDRESS}</Text>
            </View>
          </View>

          <TouchableOpacity style={styles.mapsButton} onPress={openInMaps} data-testid="open-in-maps-btn">
            <Ionicons name="navigate" size={20} color="#fff" />
            <Text style={styles.mapsButtonText}>Open in Maps</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Footer */}
      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.viewOrdersButton}
          onPress={() => router.replace('/(tabs)/orders')}
          data-testid="view-my-orders-btn"
        >
          <Text style={styles.viewOrdersText}>View My Orders</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
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
    marginBottom: 28,
    marginTop: 8,
  },
  checkCircle: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: theme.colors.success,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  successTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  orderBadge: {
    backgroundColor: theme.colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
  },
  orderBadgeText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  detailsCard: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 20,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  detailLabel: {
    fontSize: 14,
    color: theme.colors.textMuted,
  },
  detailValue: {
    fontSize: 14,
    color: '#fff',
    maxWidth: '60%',
    textAlign: 'right',
  },
  detailValueBold: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  statusBadge: {
    backgroundColor: theme.colors.primary + '20',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusBadgeCash: {
    backgroundColor: theme.colors.warning + '20',
  },
  statusText: {
    fontSize: 13,
    fontWeight: '600',
    color: theme.colors.primary,
  },
  statusTextCash: {
    color: theme.colors.warning,
  },
  pickupCard: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 20,
    marginBottom: 16,
  },
  pickupHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 20,
  },
  pickupTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  instructionStep: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 14,
  },
  stepDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.primary,
    marginTop: 6,
  },
  instructionText: {
    flex: 1,
    fontSize: 14,
    color: '#ccc',
    lineHeight: 21,
  },
  boldAccent: {
    fontWeight: 'bold',
    color: theme.colors.primary,
  },
  locationCard: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 20,
    marginBottom: 16,
  },
  locationHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 16,
  },
  storeName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  storeAddress: {
    fontSize: 14,
    color: theme.colors.textMuted,
    lineHeight: 20,
  },
  mapsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: theme.colors.primary,
    padding: 14,
    borderRadius: theme.borderRadius.lg,
  },
  mapsButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    backgroundColor: theme.colors.card,
    borderTopWidth: 1,
    borderTopColor: '#222',
  },
  viewOrdersButton: {
    backgroundColor: theme.colors.primary,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
    alignItems: 'center',
  },
  viewOrdersText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
