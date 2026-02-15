import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image, Alert } from 'react-native';
import { useState, useEffect } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
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

export default function ProductDetail() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const addItem = useCartStore(state => state.addItem);
  const [product, setProduct] = useState<Product | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProduct();
  }, [id]);

  const loadProduct = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/products/${id}`);
      setProduct(response.data);
    } catch (error) {
      console.error('Failed to load product:', error);
      Alert.alert('Error', 'Failed to load product');
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = () => {
    if (!product) return;
    
    if (product.stock === 0) {
      Alert.alert('Out of Stock', 'This product is currently unavailable');
      return;
    }

    addItem({
      productId: product.id,
      quantity,
      name: product.name,
      price: product.price,
      image: product.image,
    });

    Alert.alert(
      'Added to Cart',
      `${quantity}x ${product.name} added to cart`,
      [
        { text: 'Continue Shopping', style: 'cancel' },
        { text: 'View Cart', onPress: () => router.push('/cart') }
      ]
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.loadingText}>Loading...</Text>
      </SafeAreaView>
    );
  }

  if (!product) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.loadingText}>Product not found</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push('/cart')}>
          <Ionicons name="cart" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {product.image && (
          <Image source={{ uri: product.image }} style={styles.productImage} />
        )}

        <View style={styles.infoSection}>
          <View style={styles.brandBadge}>
            <Text style={styles.brandText}>{product.brand}</Text>
          </View>
          <Text style={styles.productName}>{product.name}</Text>
          <Text style={styles.productFlavor}>{product.flavor}</Text>

          <View style={styles.priceContainer}>
            <Text style={styles.price}>${product.price.toFixed(2)}</Text>
            {product.stock === 0 && (
              <View style={styles.outOfStockBadge}>
                <Text style={styles.outOfStockText}>Out of Stock</Text>
              </View>
            )}
          </View>

          <View style={styles.detailsCard}>
            <View style={styles.detailRow}>
              <Ionicons name="cloud" size={20} color="#2E6BFF" />
              <Text style={styles.detailLabel}>Puff Count</Text>
              <Text style={styles.detailValue}>{product.puffCount} puffs</Text>
            </View>
            <View style={styles.detailRow}>
              <Ionicons name="warning" size={20} color="#fbbf24" />
              <Text style={styles.detailLabel}>Nicotine</Text>
              <Text style={styles.detailValue}>{product.nicotinePercent}%</Text>
            </View>
            <View style={styles.detailRow}>
              <Ionicons name="cube" size={20} color="#10b981" />
              <Text style={styles.detailLabel}>Stock</Text>
              <Text style={styles.detailValue}>{product.stock > 0 ? `${product.stock} available` : 'Out of stock'}</Text>
            </View>
          </View>

          <View style={styles.warningBox}>
            <Ionicons name="warning" size={20} color="#fff" />
            <Text style={styles.warningText}>
              This product contains nicotine. Nicotine is an addictive chemical.
            </Text>
          </View>
        </View>
      </ScrollView>

      {product.stock > 0 && (
        <View style={styles.footer}>
          <View style={styles.quantityContainer}>
            <TouchableOpacity 
              style={styles.quantityButton}
              onPress={() => setQuantity(Math.max(1, quantity - 1))}
            >
              <Ionicons name="remove" size={20} color="#fff" />
            </TouchableOpacity>
            <Text style={styles.quantityText}>{quantity}</Text>
            <TouchableOpacity 
              style={styles.quantityButton}
              onPress={() => setQuantity(Math.min(product.stock, quantity + 1))}
            >
              <Ionicons name="add" size={20} color="#fff" />
            </TouchableOpacity>
          </View>
          <TouchableOpacity style={styles.addToCartButton} onPress={handleAddToCart}>
            <Text style={styles.addToCartText}>Add to Cart</Text>
            <Text style={styles.addToCartPrice}>${(product.price * quantity).toFixed(2)}</Text>
          </TouchableOpacity>
        </View>
      )}
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
  },
  backButton: {
    padding: 4,
  },
  loadingText: {
    fontSize: 16,
    color: '#A0A0A0',
    textAlign: 'center',
    marginTop: 100,
  },
  content: {
    flex: 1,
  },
  productImage: {
    width: '100%',
    height: 300,
    backgroundColor: '#151515',
  },
  infoSection: {
    padding: 16,
  },
  brandBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#2E6BFF',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 18,
    marginBottom: 12,
  },
  brandText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
  },
  productName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  productFlavor: {
    fontSize: 16,
    color: '#A0A0A0',
    marginBottom: 16,
  },
  priceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  price: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  outOfStockBadge: {
    backgroundColor: '#2E6BFF',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 18,
  },
  outOfStockText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
  },
  detailsCard: {
    backgroundColor: '#151515',
    borderRadius: 18,
    padding: 16,
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  detailLabel: {
    flex: 1,
    fontSize: 14,
    color: '#A0A0A0',
    marginLeft: 12,
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  warningBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2E6BFF',
    padding: 16,
    borderRadius: 18,
    gap: 12,
  },
  warningText: {
    flex: 1,
    fontSize: 14,
    color: '#fff',
    lineHeight: 20,
  },
  footer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#151515',
    borderTopWidth: 1,
    borderTopColor: '#333',
    gap: 12,
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0c0c0c',
    borderRadius: 18,
    padding: 8,
    gap: 16,
  },
  quantityButton: {
    width: 36,
    height: 36,
    backgroundColor: '#333',
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quantityText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    minWidth: 30,
    textAlign: 'center',
  },
  addToCartButton: {
    flex: 1,
    backgroundColor: '#2E6BFF',
    borderRadius: 18,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  addToCartText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  addToCartPrice: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
});
