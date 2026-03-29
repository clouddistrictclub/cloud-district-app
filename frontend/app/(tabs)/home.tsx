import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image, RefreshControl, useWindowDimensions, Platform, Modal, Animated, Pressable } from 'react-native';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, Link } from 'expo-router';
import { useAuthStore } from '../../store/authStore';
import { useDrawerStore } from '../../store/drawerStore';
import { Ionicons } from '@expo/vector-icons';
import ProductCard from '../../components/ProductCard';
import HeroBanner from '../../components/HeroBanner';
import AppHeader from '../../components/AppHeader';
import axios from 'axios';
import { API_URL } from '../../constants/api';

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

// Desktop hero asset (only used for wide screens)
const desktopHeroAsset = require('../../assets/images/heroes/CloudDistrict_Hero_1440x600.png');

export default function Home() {
  const router = useRouter();
  const user = useAuthStore(state => state.user);
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

  const { isOpen: drawerOpen, close: closeDrawerStore } = useDrawerStore();
  const slideAnim = useRef(new Animated.Value(-280)).current;

  useEffect(() => {
    if (drawerOpen) {
      Animated.timing(slideAnim, { toValue: 0, duration: 250, useNativeDriver: false }).start();
    }
  }, [drawerOpen]);

  const closeDrawer = () => {
    Animated.timing(slideAnim, { toValue: -280, duration: 200, useNativeDriver: false }).start(() => closeDrawerStore());
  };
  const navigateFromDrawer = (path: string) => {
    closeDrawer();
    setTimeout(() => router.push(path as any), 220);
  };

  // Drawer is now rendered globally via GlobalDrawer in _layout.tsx
  // The drawerOpen state and animation are kept for home-page legacy nav compatibility

  return (
    <View style={styles.container}>
      <AppHeader />
      {/* Drawer is rendered globally via GlobalDrawer in _layout.tsx */}

      <ScrollView 
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
      >
        {/* Hero Banner */}
        <View style={isMobile ? styles.heroBannerMobile : styles.heroBannerDesktop}>
          {isMobile ? (
            <HeroBanner testID="home-hero-mobile" />
          ) : (
            <View style={{ width: '100%', overflow: 'hidden' }}>
              <Image
                source={desktopHeroAsset}
                style={{ width: '100%', height: undefined, aspectRatio: 1440 / 600 }}
                resizeMode="cover"
                testID="home-hero-desktop"
              />
            </View>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Shop by Brand</Text>
          <View style={styles.categoryGrid}>
            {brands.map((brand) => {
              const brandImg = brand.image
                ? (brand.image.startsWith('/') ? `${API_URL}${brand.image}` : brand.image)
                : null;
              return (
                <TouchableOpacity 
                  key={brand.id} 
                  style={styles.categoryCard}
                  onPress={() => router.push(`/shop?brand=${brand.id}`)}
                >
                  {brandImg ? (
                    Platform.OS === 'web' ? (
                      <img src={brandImg} style={{ width: 48, height: 48, objectFit: 'contain', borderRadius: 8 }} alt={brand.name} />
                    ) : (
                      <Image source={{ uri: brandImg }} style={{ width: 48, height: 48, borderRadius: 8 }} resizeMode="contain" />
                    )
                  ) : (
                    <Ionicons name="flash" size={32} color="#6366f1" />
                  )}
                  <Text style={styles.categoryName}>{brand.name}</Text>
                </TouchableOpacity>
              );
            })}
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
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