import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image, RefreshControl, useWindowDimensions, Platform } from 'react-native';
import { useState, useEffect } from 'react';
import { useRouter, Link } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../../store/authStore';
import { useCartStore } from '../../store/cartStore';
import { Ionicons } from '@expo/vector-icons';
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

export default function Home() {
  const router = useRouter();
  const user = useAuthStore(state => state.user);
  const itemCount = useCartStore(state => state.getItemCount());
  const { width } = useWindowDimensions();
  const isMobile = width < 768;
  const heroContainerWidth = width - 32; // account for 16px margins each side
  const mobileHeroHeight = heroContainerWidth * (1350 / 1080);
  const desktopHeroHeight = heroContainerWidth * (600 / 1440);
  const [products, setProducts] = useState<Product[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadProducts = async () => {
    try {
      const [productsRes, brandsRes] = await Promise.all([
        axios.get(`${API_URL}/api/products`),
        axios.get(`${API_URL}/api/brands?active_only=true`)
      ]);
      setProducts(productsRes.data.slice(0, 6)); // Featured products
      setBrands(brandsRes.data.slice(0, 4)); // Top 4 brands
    } catch (error) {
      console.error('Failed to load products:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadProducts();
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Image
          source={require('../../assets/images/logo-horizontal.png')}
          style={styles.headerLogo}
          resizeMode="contain"
          data-testid="home-skyline-logo"
        />
        <View style={styles.headerRight}>
          <View style={styles.loyaltyBadge}>
            <Ionicons name="star" size={16} color="#fbbf24" />
            <Text style={styles.loyaltyPoints}>{user?.loyaltyPoints || 0}</Text>
          </View>
          <TouchableOpacity onPress={() => router.push('/cart')} style={styles.cartButton}>
            <Ionicons name="cart" size={24} color="#fff" />
            {itemCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{itemCount}</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView 
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
      >
        {/* Hero Banner */}
        <View style={styles.heroBannerWrap}>
          {isMobile ? (
            <Image
              source={require('../../assets/images/heroes/CloudDistrict_Mobile_Hero_v1_A_Final.png')}
              style={{ width: heroContainerWidth, height: mobileHeroHeight }}
              resizeMode="contain"
              testID="home-hero-mobile"
            />
          ) : (
            <Image
              source={require('../../assets/images/heroes/CloudDistrict_Hero_1440x600.png')}
              style={{ width: heroContainerWidth, height: desktopHeroHeight }}
              resizeMode="contain"
              testID="home-hero-desktop"
            />
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
              <TouchableOpacity
                key={product.id}
                style={styles.productCard}
                onPress={() => router.push(`/product/${product.id}`)}
              >
                {product.image && (
                  <Image 
                    source={{ uri: product.image }} 
                    style={styles.productImage}
                  />
                )}
                <View style={styles.productInfo}>
                  <Text style={styles.productBrand}>{product.brand}</Text>
                  <Text style={styles.productName} numberOfLines={2}>{product.name}</Text>
                  <Text style={styles.productFlavor}>{product.flavor}</Text>
                  <View style={styles.productFooter}>
                    <Text style={styles.productPrice}>${product.price.toFixed(2)}</Text>
                    <Text style={styles.productPuffs}>{product.puffCount} puffs</Text>
                  </View>
                </View>
              </TouchableOpacity>
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
    padding: 16,
    paddingTop: 8,
  },
  headerLogo: {
    height: 36,
    width: 160,
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
  heroBannerWrap: {
    marginHorizontal: 16,
    marginTop: 4,
    marginBottom: 8,
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 8,
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
  productCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#151515',
    borderRadius: 18,
    overflow: 'hidden',
  },
  productImage: {
    width: '100%',
    height: 120,
    backgroundColor: '#222222',
  },
  productInfo: {
    padding: 12,
  },
  productBrand: {
    fontSize: 12,
    color: '#2E6BFF',
    fontWeight: '600',
    marginBottom: 4,
  },
  productName: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
    marginBottom: 4,
  },
  productFlavor: {
    fontSize: 12,
    color: '#A0A0A0',
    marginBottom: 8,
  },
  productFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  productPrice: {
    fontSize: 16,
    color: '#fff',
    fontWeight: 'bold',
  },
  productPuffs: {
    fontSize: 11,
    color: '#666',
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
});