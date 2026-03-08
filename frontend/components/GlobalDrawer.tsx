import { View, Text, StyleSheet, TouchableOpacity, Image, Modal, Animated, Pressable } from 'react-native';
import { useRef, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../store/authStore';
import { useDrawerStore } from '../store/drawerStore';

export default function GlobalDrawer() {
  const router = useRouter();
  const user = useAuthStore(state => state.user);
  const { isOpen, close } = useDrawerStore();
  const slideAnim = useRef(new Animated.Value(-280)).current;

  useEffect(() => {
    if (isOpen) {
      Animated.timing(slideAnim, { toValue: 0, duration: 250, useNativeDriver: false }).start();
    }
  }, [isOpen]);

  const closeDrawer = () => {
    Animated.timing(slideAnim, { toValue: -280, duration: 200, useNativeDriver: false }).start(() => close());
  };

  const navigateFromDrawer = (path: string) => {
    closeDrawer();
    setTimeout(() => router.push(path as any), 220);
  };

  const drawerItems = [
    { icon: 'person' as const, label: 'Profile', path: '/profile' },
    { icon: 'star' as const, label: 'Cloudz Points', path: '/cloudz' },
    { icon: 'receipt' as const, label: 'Orders', path: '/orders' },
    { icon: 'chatbubble-ellipses' as const, label: 'Support', path: '/support' },
    ...(user?.isAdmin ? [{ icon: 'shield' as const, label: 'Admin', path: '/admin/orders' }] : []),
  ];

  if (!isOpen) return null;

  return (
    <Modal transparent visible animationType="none" onRequestClose={closeDrawer}>
      <Pressable style={styles.drawerOverlay} onPress={closeDrawer}>
        <Animated.View style={[styles.drawerPanel, { left: slideAnim }]}>
          <Pressable onPress={(e) => e.stopPropagation()}>
            <View style={styles.drawerHeader}>
              <Image source={require('../assets/images/icon.png')} style={styles.drawerLogo} resizeMode="contain" />
              <Text style={styles.drawerTitle}>Cloud District</Text>
            </View>
            <View style={styles.drawerDivider} />
            {drawerItems.map((item) => (
              <TouchableOpacity key={item.path} style={styles.drawerItem} onPress={() => navigateFromDrawer(item.path)}>
                <Ionicons name={item.icon} size={20} color="#aaa" />
                <Text style={styles.drawerItemText}>{item.label}</Text>
              </TouchableOpacity>
            ))}
          </Pressable>
        </Animated.View>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  drawerOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  drawerPanel: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 280,
    backgroundColor: '#111',
    paddingTop: 60,
    paddingHorizontal: 20,
  },
  drawerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  drawerLogo: {
    width: 44,
    height: 44,
    borderRadius: 10,
  },
  drawerTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  drawerDivider: {
    height: 1,
    backgroundColor: '#222',
    marginBottom: 12,
  },
  drawerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingVertical: 14,
  },
  drawerItemText: {
    color: '#ddd',
    fontSize: 15,
    fontWeight: '500',
  },
});
