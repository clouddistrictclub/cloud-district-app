import { View, Text, StyleSheet, TouchableOpacity, Image, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../store/authStore';
import { useCartStore } from '../store/cartStore';

export default function AppHeader() {
  const router = useRouter();
  const user = useAuthStore(state => state.user);
  const itemCount = useCartStore(state => state.items.reduce((sum, i) => sum + i.quantity, 0));

  return (
    <View style={styles.header} data-testid="app-header">
      <TouchableOpacity onPress={() => router.push('/cloudz')} data-testid="header-icon-btn" activeOpacity={0.7}>
        <Image
          source={require('../assets/images/icon.png')}
          style={styles.headerIcon}
          resizeMode="contain"
        />
      </TouchableOpacity>
      <View style={styles.headerRight}>
        <TouchableOpacity onPress={() => router.push('/cloudz')} style={styles.loyaltyBadge} data-testid="header-cloudz-badge">
          <Ionicons name="star" size={16} color="#fbbf24" />
          <Text style={styles.loyaltyPoints}>{(user?.loyaltyPoints || 0).toLocaleString()}</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push('/cart')} style={styles.cartButton} data-testid="header-cart-btn">
          <Ionicons name="cart" size={24} color="#fff" />
          {itemCount > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{itemCount}</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 8,
    paddingTop: Platform.OS === 'web' ? 'max(12px, env(safe-area-inset-top))' as any : 8,
    backgroundColor: '#0C0C0C',
  },
  headerIcon: {
    height: 36,
    width: 36,
    borderRadius: 8,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  loyaltyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#151515',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 4,
  },
  loyaltyPoints: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  cartButton: {
    position: 'relative',
  },
  badge: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#2E6BFF',
    borderRadius: 10,
    width: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
});
