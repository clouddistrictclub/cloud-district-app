import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../../store/authStore';
import { useCartStore } from '../../store/cartStore';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme';

export default function Account() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const clearCart = useCartStore(state => state.clearCart);

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Logout', 
          style: 'destructive',
          onPress: async () => {
            await logout();
            clearCart();
            router.replace('/auth/login');
          }
        }
      ]
    );
  };

  const menuItems = [
    {
      icon: 'star',
      label: 'Cloudz Rewards',
      onPress: () => router.push('/cloudz'),
      color: '#fbbf24',
    },
    ...(user?.isAdmin ? [
      { 
        icon: 'shield', 
        label: 'Admin Dashboard', 
        onPress: () => router.push('/admin/orders'),
        color: theme.colors.primary,
      }
    ] : []),
  ];

  const userPoints = user?.loyaltyPoints || 0;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Account</Text>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {user?.firstName.charAt(0)}{user?.lastName.charAt(0)}
            </Text>
          </View>
          <Text style={styles.profileName}>{user?.firstName} {user?.lastName}</Text>
          <Text style={styles.profileEmail}>{user?.email}</Text>
        </View>

        <TouchableOpacity
          style={styles.loyaltyCard}
          onPress={() => router.push('/cloudz')}
          activeOpacity={0.8}
          data-testid="loyalty-card-link"
        >
          <View style={styles.loyaltyHeader}>
            <Ionicons name="star" size={32} color="#fbbf24" />
            <Text style={styles.loyaltyTitle}>Cloudz Points</Text>
            <Ionicons name="chevron-forward" size={20} color="#e0e7ff" style={{ marginLeft: 'auto' }} />
          </View>
          <Text style={styles.loyaltyPoints} data-testid="account-points-display">{userPoints.toLocaleString()}</Text>
          <Text style={styles.loyaltySubtext}>Tap to view reward tiers</Text>
        </TouchableOpacity>

        <View style={styles.section}>
          {menuItems.map((item, index) => (
            <TouchableOpacity
              key={index}
              style={styles.menuItem}
              onPress={item.onPress}
              data-testid={`menu-item-${item.label.toLowerCase().replace(/\s/g, '-')}`}
            >
              <View style={styles.menuItemLeft}>
                <Ionicons name={item.icon as any} size={24} color={item.color || '#fff'} />
                <Text style={[styles.menuItemText, item.color && { color: item.color }]}>
                  {item.label}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#666" />
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.section}>
          <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>Member Since</Text>
            <Text style={styles.infoValue}>
              {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
            </Text>
          </View>
          
          <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>Age Verified</Text>
            <View style={styles.verifiedBadge}>
              <Ionicons name="checkmark-circle" size={16} color={theme.colors.success} />
              <Text style={styles.verifiedText}>21+</Text>
            </View>
          </View>
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout} data-testid="logout-btn">
          <Ionicons name="log-out" size={20} color={theme.colors.primary} />
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>

        <View style={styles.footer}>
          <Text style={styles.footerText}>Cloud District Club</Text>
          <Text style={styles.footerSubtext}>Local Pickup Only - 21+ Only</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
  },
  header: {
    padding: 16,
    paddingTop: 8,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  profileCard: {
    backgroundColor: '#151515',
    borderRadius: 18,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#2E6BFF',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  profileName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  profileEmail: {
    fontSize: 14,
    color: '#A0A0A0',
  },
  loyaltyCard: {
    backgroundColor: 'linear-gradient(135deg, #2E6BFF 0%, #8b5cf6 100%)',
    backgroundColor: '#2E6BFF',
    borderRadius: 18,
    padding: 24,
    marginBottom: 16,
  },
  loyaltyHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  loyaltyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  loyaltyPoints: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  loyaltySubtext: {
    fontSize: 14,
    color: '#e0e7ff',
  },
  section: {
    marginBottom: 16,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#151515',
    padding: 16,
    borderRadius: 18,
    marginBottom: 8,
  },
  menuItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  menuItemText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '500',
  },
  infoCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#151515',
    padding: 16,
    borderRadius: 18,
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 14,
    color: '#A0A0A0',
  },
  infoValue: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
  },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  verifiedText: {
    fontSize: 14,
    color: '#10b981',
    fontWeight: '600',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#151515',
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#2E6BFF',
  },
  logoutText: {
    fontSize: 16,
    color: '#2E6BFF',
    fontWeight: '600',
  },
  footer: {
    alignItems: 'center',
    marginTop: 32,
    marginBottom: 16,
  },
  footerText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  footerSubtext: {
    fontSize: 12,
    color: '#444',
    marginTop: 4,
  },
});