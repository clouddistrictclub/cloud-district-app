import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image, RefreshControl, useWindowDimensions, Platform, Modal, Animated, Pressable, Dimensions } from 'react-native';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, Link } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../../store/authStore';
import { useCartStore } from '../../store/cartStore';
import { Ionicons } from '@expo/vector-icons';
import ProductCard from '../../components/ProductCard';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Product {
  id: string;
  name: string;
  brand: string;
  category: string;
  image: string;
  puffCount: number;
  flavor: string;
  nicotinePercent: number;
  price: number;
  stock: number;
}

// Hero image assets
const mobileHeroAsset = require('../../assets/images/heroes/CloudDistrict_Mobile_Hero_v1_A_Final.png');
const desktopHeroAsset = require('../../assets/images/heroes/CloudDistrict_Hero_1440x600.png');

// Platform-specific hero image component for proper width:100%/height:auto on web
const HeroImage = ({ source, testID, isMobile }: { source: any; testID: string; isMobile: boolean }) => {
  if (Platform.OS === 'web') {
    let uri: string;
    if (typeof source === 'string') {
      uri = source;
    } else if (typeof source === 'number') {
      uri = Image.resolveAssetSource(source)?.uri ?? '';
    } else {
      uri = source?.uri ?? '';
    }
    if (isMobile) {
      return (
        <img
          src={uri}
          style={{ width: '100%', height: '26vh', objectFit: 'cover', objectPosition: 'center center', display: 'block' }}
          data-testid={testID}
          alt="Cloud District Hero"
        />
      );
    }
    return (
      <img
        src={uri}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        data-testid={testID}
        alt="Cloud District Hero"
      />
    );
  }
  return (
    <Image
      source={source}
      style={{ width: '100%' }}
      resizeMode="contain"
      testID={testID}
    />
  );
};

export default function Home() {
  const router = useRouter();
  const user = useAuthStore(state => state.user);
  const itemCount = useCartStore(state => state.items.reduce((sum, i) => sum + i.quantity, 0));
  const { width } = useWindowDimensions();
  const isMobile = width < 768;
  const [products, setProducts] = useState<Product[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadProducts = useCallback(async () => {
    try {
      const [productsRes, brandsRes] = await Promise.all([
        axios.get(`${API_URL}/api/products`),
        axios.get(`${API_URL}/api/brands?active_only=true`)
      ]);
      setProducts(productsRes.data.slice(0, 6));
      setBrands(brandsRes.data.slice(0, 4));
    } catch (error) {
      console.error('Failed to load products:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadProducts();
  };

  const [drawerOpen, setDrawerOpen] = useState(false);
  const slideAnim = useRef(new Animated.Value(-280)).current;

  const openDrawer = () => {
    setDrawerOpen(true);
    Animated.timing(slideAnim, { toValue: 0, duration: 250, useNativeDriver: false }).start();
  };
  const closeDrawer = () => {
    Animated.timing(slideAnim, { toValue: -280, duration: 200, useNativeDriver: false }).start(() => setDrawerOpen(false));
  };
  const navigateFromDrawer = (path: string) => {
    closeDrawer();
    setTimeout(() => router.push(path as any), 220);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={openDrawer} data-testid="header-menu-btn" activeOpacity={0.7}>
          <Image
            source={require('../../assets/images/icon.png')}
            style={styles.headerIcon}
            resizeMode="contain"
          />
        </TouchableOpacity>
        <View style={styles.headerRight}>
          <View style={styles.loyaltyBadge}>
            <Ionicons name="star" size={16} color="#fbbf24" />
            <Text style={styles.loyaltyPoints}>{user?.loyaltyPoints || 0}</Text>
          </View>
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

      {/* Side Drawer */}
      {drawerOpen && (
        <Modal transparent visible animationType="none" onRequestClose={closeDrawer}>
          <Pressable style={styles.drawerOverlay} onPress={closeDrawer}>
            <Animated.View style={[styles.drawerPanel, { left: slideAnim }]}>
              <Pressable onPress={(e) => e.stopPropagation()}>
                <View style={styles.drawerHeader}>
                  <Image source={require('../../assets/images/icon.png')} style={styles.drawerLogo} resizeMode="contain" />
                  <Text style={styles.drawerTitle}>Cloud District</Text>
                </View>
                <View style={styles.drawerDivider} />
                {[
                  { icon: 'person' as const, label: 'Profile', path: '/profile' },
                  { icon: 'star' as const, label: 'Cloudz Points', path: '/cloudz' },
                  { icon: 'receipt' as const, label: 'Orders', path: '/orders' },
                  { icon: 'chatbubble-ellipses' as const, label: 'Support', path: '/support' },
                  ...(user?.isAdmin ? [{ icon: 'shield' as const, label: 'Admin', path: '/admin/orders' }] : []),
                ].map((item) => (
                  <TouchableOpacity key={item.path} style={styles.drawerItem} onPress={() => navigateFromDrawer(item.path)}>
                    <Ionicons name={item.icon} size={20} color="#aaa" />
                    <Text style={styles.drawerItemText}>{item.label}</Text>
                  </TouchableOpacity>
                ))}
              </Pressable>
            </Animated.View>
          </Pressable>
        </Modal>
      )}

      <ScrollView 
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
      >
        {/* Hero Banner */}
        <View style={isMobile ? styles.heroBannerMobile : styles.heroBannerDesktop}>
          {isMobile ? (
            <HeroImage source={mobileHeroAsset} testID="home-hero-mobile" isMobile />
          ) : (
            <HeroImage source={desktopHeroAsset} testID="home-hero-desktop" isMobile={false} />
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Shop by Brand</Text>
          <View style={styles.categoryGrid}>
            {brands.map((brand) => (
              <TouchableOpacity 
                key={brand.id} 
                style={styles.categoryCard}
                onPress={() => router.push(`/shop?brand=${brand.id}`)}
              >
                <Ionicons name="flash" size={32} color="#6366f1" />
                <Text style={styles.categoryName}>{brand.name}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Featured Products</Text>
            <Link href="/shop" asChild>
              <TouchableOpacity>
                <Text style={styles.seeAll}>See All</Text>
              </TouchableOpacity>
            </Link>
          </View>
          <View style={styles.productGrid}>
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </View>
        </View>

        {user?.isAdmin && (
          <TouchableOpacity 
            style={styles.adminButton}
            onPress={() => router.push('/admin/orders')}
          >
            <Ionicons name="shield" size={20} color="#fff" />
            <Text style={styles.adminButtonText}>Admin Dashboard</Text>
          </TouchableOpacity>
        )}
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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 8,
    paddingTop: Platform.OS === 'web' ? 'max(12px, env(safe-area-inset-top))' as any : 8,
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
  content: {
    flex: 1,
  },
  heroBannerMobile: {
    overflow: 'hidden',
  },
  heroBannerDesktop: {
    marginHorizontal: 16,
    marginTop: 2,
    marginBottom: 4,
    borderRadius: 16,
    overflow: 'hidden',
  },
  section: {
    padding: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  seeAll: {
    fontSize: 14,
    color: '#2E6BFF',
    fontWeight: '600',
  },
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  categoryCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#151515',
    padding: 20,
    borderRadius: 18,
    alignItems: 'center',
    gap: 8,
  },
  categoryName: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  productGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  adminButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    margin: 16,
    padding: 16,
    backgroundColor: '#2E6BFF',
    borderRadius: 18,
  },
  adminButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
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