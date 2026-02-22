import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal, Image, Alert, RefreshControl, Switch, Platform, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useAuthStore } from '../../store/authStore';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Brand {
  id: string;
  name: string;
  isActive: boolean;
}

interface Product {
  id: string;
  name: string;
  brandId: string;
  brandName: string;
  category: string;
  image: string;
  images?: string[];
  puffCount: number;
  flavor: string;
  nicotinePercent: number;
  price: number;
  stock: number;
  lowStockThreshold: number;
  description?: string;
  isActive: boolean;
  isFeatured: boolean;
  loyaltyEarnRate?: number;
  displayOrder: number;
}

export default function ProductsManagement() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [stockAdjustProduct, setStockAdjustProduct] = useState<Product | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    brandId: '',
    category: 'best-sellers',
    image: '',
    puffCount: 5000,
    flavor: '',
    nicotinePercent: 5.0,
    price: 19.99,
    stock: 10,
    lowStockThreshold: 5,
    description: '',
    isActive: true,
    isFeatured: false,
    loyaltyEarnRate: 0,
    displayOrder: 0,
  });

  const [stockAdjustment, setStockAdjustment] = useState({ amount: 0, reason: '' });
  const [uploading, setUploading] = useState(false);
  const token = useAuthStore(state => state.token);

  useEffect(() => {
    loadData();
  }, []);

  // Refresh brands when screen gains focus
  useFocusEffect(
    useCallback(() => {
      fetchBrands();
    }, [])
  );

  const fetchBrands = async () => {
    try {
      const brandsRes = await axios.get(`${API_URL}/api/brands?active_only=false`);
      setBrands(brandsRes.data);
    } catch (error) {
      console.error('Failed to fetch brands:', error);
    }
  };

  const loadData = async () => {
    try {
      const [productsRes, brandsRes] = await Promise.all([
        axios.get(`${API_URL}/api/products?active_only=false`),
        axios.get(`${API_URL}/api/brands?active_only=false`)
      ]);
      setProducts(productsRes.data);
      setBrands(brandsRes.data);
    } catch (error: any) {
      console.error('Failed to load data:', error);
      console.error('Status:', error.response?.status);
      console.error('Details:', error.response?.data);
      Alert.alert(
        'Error Loading Data',
        `${error.response?.status || 'Network'} Error: ${error.response?.data?.detail || error.message}`
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.7,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setUploading(true);
      try {
        const formPayload = new FormData();
        const ext = (asset.uri.split('.').pop() || 'jpg').toLowerCase().split('?')[0];
        const mimeType = `image/${ext === 'jpg' ? 'jpeg' : ext}`;

        if (Platform.OS === 'web') {
          // On web: fetch the blob URI and convert to File
          const response = await fetch(asset.uri);
          const blob = await response.blob();
          const file = new File([blob], `product.${ext}`, { type: mimeType });
          formPayload.append('file', file);
        } else {
          // On native: use RN FormData syntax
          formPayload.append('file', {
            uri: asset.uri,
            name: `product.${ext}`,
            type: mimeType,
          } as any);
        }

        const res = await axios.post(`${API_URL}/api/upload/product-image`, formPayload, {
          headers: {
            Authorization: `Bearer ${token}`,
            // Content-Type intentionally omitted — browser auto-sets multipart boundary
          },
        });
        setFormData(prev => ({ ...prev, image: res.data.url }));
      } catch (error: any) {
        Alert.alert('Upload Failed', error.response?.data?.detail || 'Could not upload image');
      } finally {
        setUploading(false);
      }
    }
  };

  const handleSaveProduct = async () => {
    if (!formData.name || !formData.brandId || !formData.flavor || !formData.image) {
      Alert.alert('Error', 'Please fill all required fields and add an image');
      return;
    }

    try {
      const headers = { Authorization: `Bearer ${token}` };
      if (editingProduct) {
        await axios.patch(`${API_URL}/api/products/${editingProduct.id}`, formData, { headers });
        Alert.alert('Success', 'Product updated successfully');
      } else {
        await axios.post(`${API_URL}/api/products`, formData, { headers });
        Alert.alert('Success', 'Product created successfully');
      }
      setShowModal(false);
      resetForm();
      loadData();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save product');
    }
  };

  const handleDeleteProduct = (product: Product) => {
    Alert.alert(
      'Delete Product',
      `Are you sure you want to delete "${product.name}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await axios.delete(`${API_URL}/api/products/${product.id}`);
              Alert.alert('Success', 'Product deleted');
              loadData();
            } catch (error) {
              Alert.alert('Error', 'Failed to delete product');
            }
          }
        }
      ]
    );
  };

  const handleStockAdjustment = async () => {
    if (!stockAdjustProduct || stockAdjustment.amount === 0) return;

    try {
      await axios.patch(`${API_URL}/api/products/${stockAdjustProduct.id}/stock`, {
        adjustment: stockAdjustment.amount,
        reason: stockAdjustment.reason
      });
      Alert.alert('Success', 'Stock adjusted successfully');
      setStockAdjustProduct(null);
      setStockAdjustment({ amount: 0, reason: '' });
      loadData();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to adjust stock');
    }
  };

  const toggleActive = async (product: Product) => {
    try {
      await axios.patch(`${API_URL}/api/products/${product.id}`, { isActive: !product.isActive });
      loadData();
    } catch (error) {
      Alert.alert('Error', 'Failed to update product status');
    }
  };

  const toggleFeatured = async (product: Product) => {
    try {
      await axios.patch(`${API_URL}/api/products/${product.id}`, { isFeatured: !product.isFeatured });
      loadData();
    } catch (error) {
      Alert.alert('Error', 'Failed to update featured status');
    }
  };

  const openEditModal = (product: Product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      brandId: product.brandId,
      category: product.category,
      image: product.image,
      puffCount: product.puffCount,
      flavor: product.flavor,
      nicotinePercent: product.nicotinePercent,
      price: product.price,
      stock: product.stock,
      lowStockThreshold: product.lowStockThreshold,
      description: product.description || '',
      isActive: product.isActive,
      isFeatured: product.isFeatured,
      loyaltyEarnRate: product.loyaltyEarnRate || 0,
      displayOrder: product.displayOrder,
    });
    setShowModal(true);
  };

  const resetForm = () => {
    setEditingProduct(null);
    setFormData({
      name: '',
      brandId: '',
      category: 'best-sellers',
      image: '',
      puffCount: 5000,
      flavor: '',
      nicotinePercent: 5.0,
      price: 19.99,
      stock: 10,
      lowStockThreshold: 5,
      description: '',
      isActive: true,
      isFeatured: false,
      loyaltyEarnRate: 0,
      displayOrder: 0,
    });
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['top']}>
      <View style={styles.container}>
        <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Products</Text>
        <TouchableOpacity onPress={() => { resetForm(); setShowModal(true); }}>
          <Ionicons name="add-circle" size={28} color="#2E6BFF" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} tintColor="#2E6BFF" />}
      >
        {loading ? (
          <Text style={styles.emptyText}>Loading...</Text>
        ) : products.length === 0 ? (
          <Text style={styles.emptyText}>No products yet. Tap + to add one.</Text>
        ) : (
          products.map((product) => (
            <View key={product.id} style={styles.productCard}>
              <View style={styles.productHeader}>
                {product.image && (
                  <Image source={{ uri: product.image.startsWith('/') ? `${API_URL}${product.image}` : product.image }} style={styles.productImage} />
                )}
                <View style={styles.productInfo}>
                  <View style={styles.productTitleRow}>
                    <Text style={styles.productName} numberOfLines={1}>{product.name}</Text>
                    {product.isFeatured && (
                      <Ionicons name="star" size={16} color="#fbbf24" />
                    )}
                  </View>
                  <Text style={styles.productBrand}>{product.brandName}</Text>
                  <Text style={styles.productFlavor}>{product.flavor} • {product.puffCount} puffs</Text>
                  <View style={styles.productFooter}>
                    <Text style={styles.productPrice}>${product.price.toFixed(2)}</Text>
                    <View style={[
                      styles.stockBadge,
                      product.stock === 0 && styles.stockBadgeEmpty,
                      product.stock > 0 && product.stock <= product.lowStockThreshold && styles.stockBadgeLow
                    ]}>
                      <Text style={styles.stockText}>Stock: {product.stock}</Text>
                    </View>
                  </View>
                </View>
              </View>

              <View style={styles.productActions}>
                <TouchableOpacity style={styles.actionButton} onPress={() => toggleActive(product)}>
                  <Ionicons name={product.isActive ? "eye" : "eye-off"} size={18} color={product.isActive ? "#10b981" : "#666"} />
                  <Text style={[styles.actionButtonText, !product.isActive && { color: '#666' }]}>
                    {product.isActive ? 'Active' : 'Inactive'}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity style={styles.actionButton} onPress={() => toggleFeatured(product)}>
                  <Ionicons name={product.isFeatured ? "star" : "star-outline"} size={18} color={product.isFeatured ? "#fbbf24" : "#666"} />
                </TouchableOpacity>

                <TouchableOpacity style={styles.actionButton} onPress={() => setStockAdjustProduct(product)}>
                  <Ionicons name="create" size={18} color="#6366f1" />
                  <Text style={styles.actionButtonText}>Stock</Text>
                </TouchableOpacity>

                <TouchableOpacity style={styles.actionButton} onPress={() => openEditModal(product)}>
                  <Ionicons name="pencil" size={18} color="#6366f1" />
                </TouchableOpacity>

                <TouchableOpacity style={styles.actionButton} onPress={() => handleDeleteProduct(product)}>
                  <Ionicons name="trash" size={18} color="#2E6BFF" />
                </TouchableOpacity>
              </View>
            </View>
          ))
        )}
      </ScrollView>

      {/* Add/Edit Product Modal */}
      <Modal visible={showModal} animationType="slide" presentationStyle="fullScreen">
        <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['bottom']}>
          <View style={{ flex: 1, paddingTop: 50 }}>
            <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
            <View style={styles.modalHeader}>
              <TouchableOpacity onPress={() => setShowModal(false)}>
                <Text style={{ color: '#FF3B3B', fontSize: 16 }}>Cancel</Text>
              </TouchableOpacity>
              <Text style={styles.modalHeaderTitle}>{editingProduct ? 'Edit Product' : 'Add Product'}</Text>
              <TouchableOpacity onPress={handleSaveProduct}>
                <Text style={{ color: '#4CAF50', fontSize: 16 }}>Save</Text>
              </TouchableOpacity>
            </View>

              <TouchableOpacity style={styles.imageUpload} onPress={pickImage} disabled={uploading}>
                {uploading ? (
                  <View style={styles.uploadPlaceholder}>
                    <ActivityIndicator size="large" color="#2E6BFF" />
                    <Text style={styles.uploadText}>Uploading...</Text>
                  </View>
                ) : formData.image ? (
                  <Image source={{ uri: formData.image.startsWith('/') ? `${API_URL}${formData.image}` : formData.image }} style={styles.uploadedImage} />
                ) : (
                  <View style={styles.uploadPlaceholder}>
                    <Ionicons name="camera" size={40} color="#666" />
                    <Text style={styles.uploadText}>Tap to upload image</Text>
                  </View>
                )}
              </TouchableOpacity>

              <Text style={styles.inputLabel}>Product Name *</Text>
              <TextInput
                style={styles.input}
                value={formData.name}
                onChangeText={(text) => setFormData({ ...formData, name: text })}
                placeholder="Enter product name"
                placeholderTextColor="#666"
              />

              <Text style={styles.inputLabel}>Brand *</Text>
              <View style={styles.pickerContainer}>
                {brands.map((brand) => (
                  <TouchableOpacity
                    key={brand.id}
                    style={[styles.pickerOption, formData.brandId === brand.id && styles.pickerOptionSelected]}
                    onPress={() => setFormData({ ...formData, brandId: brand.id })}
                  >
                    <Text style={[styles.pickerOptionText, formData.brandId === brand.id && styles.pickerOptionTextSelected]}>
                      {brand.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.inputLabel}>Flavor *</Text>
              <TextInput
                style={styles.input}
                value={formData.flavor}
                onChangeText={(text) => setFormData({ ...formData, flavor: text })}
                placeholder="e.g., Watermelon Ice"
                placeholderTextColor="#666"
              />

              <View style={styles.row}>
                <View style={styles.halfInput}>
                  <Text style={styles.inputLabel}>Puff Count</Text>
                  <TextInput
                    style={styles.input}
                    value={String(formData.puffCount)}
                    onChangeText={(text) => setFormData({ ...formData, puffCount: parseInt(text) || 0 })}
                    keyboardType="numeric"
                    placeholderTextColor="#666"
                  />
                </View>
                <View style={styles.halfInput}>
                  <Text style={styles.inputLabel}>Nicotine %</Text>
                  <TextInput
                    style={styles.input}
                    value={String(formData.nicotinePercent)}
                    onChangeText={(text) => setFormData({ ...formData, nicotinePercent: parseFloat(text) || 0 })}
                    keyboardType="decimal-pad"
                    placeholderTextColor="#666"
                  />
                </View>
              </View>

              <View style={styles.row}>
                <View style={styles.halfInput}>
                  <Text style={styles.inputLabel}>Price ($)</Text>
                  <TextInput
                    style={styles.input}
                    value={String(formData.price)}
                    onChangeText={(text) => setFormData({ ...formData, price: parseFloat(text) || 0 })}
                    keyboardType="decimal-pad"
                    placeholderTextColor="#666"
                  />
                </View>
                <View style={styles.halfInput}>
                  <Text style={styles.inputLabel}>Stock</Text>
                  <TextInput
                    style={styles.input}
                    value={String(formData.stock)}
                    onChangeText={(text) => setFormData({ ...formData, stock: parseInt(text) || 0 })}
                    keyboardType="numeric"
                    placeholderTextColor="#666"
                  />
                </View>
              </View>

              <View style={styles.row}>
                <View style={styles.halfInput}>
                  <Text style={styles.inputLabel}>Low Stock Alert</Text>
                  <TextInput
                    style={styles.input}
                    value={String(formData.lowStockThreshold)}
                    onChangeText={(text) => setFormData({ ...formData, lowStockThreshold: parseInt(text) || 0 })}
                    keyboardType="numeric"
                    placeholderTextColor="#666"
                  />
                </View>
                <View style={styles.halfInput}>
                  <Text style={styles.inputLabel}>Display Order</Text>
                  <TextInput
                    style={styles.input}
                    value={String(formData.displayOrder)}
                    onChangeText={(text) => setFormData({ ...formData, displayOrder: parseInt(text) || 0 })}
                    keyboardType="numeric"
                    placeholderTextColor="#666"
                  />
                </View>
              </View>

              <View style={styles.switchRow}>
                <Text style={styles.inputLabel}>Active</Text>
                <Switch
                  value={formData.isActive}
                  onValueChange={(value) => setFormData({ ...formData, isActive: value })}
                  trackColor={{ false: '#333', true: '#10b981' }}
                  thumbColor="#fff"
                />
              </View>

              <View style={styles.switchRow}>
                <Text style={styles.inputLabel}>Featured</Text>
                <Switch
                  value={formData.isFeatured}
                  onValueChange={(value) => setFormData({ ...formData, isFeatured: value })}
                  trackColor={{ false: '#333', true: '#fbbf24' }}
                  thumbColor="#fff"
                />
              </View>

              <Text style={styles.inputLabel}>Description (Optional)</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={formData.description}
                onChangeText={(text) => setFormData({ ...formData, description: text })}
                placeholder="Product description..."
                placeholderTextColor="#666"
                multiline
                numberOfLines={4}
              />
            </ScrollView>
          </View>
        </SafeAreaView>
      </Modal>

      {/* Stock Adjustment Modal */}
      <Modal visible={!!stockAdjustProduct} animationType="slide" transparent onRequestClose={() => setStockAdjustProduct(null)}>
        <View style={styles.stockModalOverlay}>
          <View style={styles.stockModalContent}>
            <Text style={styles.stockModalTitle}>Adjust Stock</Text>
            <Text style={styles.stockModalProduct}>{stockAdjustProduct?.name}</Text>
            <Text style={styles.stockModalCurrent}>Current Stock: {stockAdjustProduct?.stock}</Text>

            <Text style={styles.inputLabel}>Adjustment Amount</Text>
            <TextInput
              style={styles.input}
              value={String(stockAdjustment.amount)}
              onChangeText={(text) => setStockAdjustment({ ...stockAdjustment, amount: parseInt(text) || 0 })}
              keyboardType="numeric"
              placeholder="Enter positive or negative number"
              placeholderTextColor="#666"
            />

            <Text style={styles.inputLabel}>Reason (Optional)</Text>
            <TextInput
              style={styles.input}
              value={stockAdjustment.reason}
              onChangeText={(text) => setStockAdjustment({ ...stockAdjustment, reason: text })}
              placeholder="e.g., Damaged items, restock"
              placeholderTextColor="#666"
            />

            <View style={styles.stockModalButtons}>
              <TouchableOpacity style={styles.stockModalCancel} onPress={() => setStockAdjustProduct(null)}>
                <Text style={styles.stockModalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.stockModalSave} onPress={handleStockAdjustment}>
                <Text style={styles.stockModalSaveText}>Adjust Stock</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
    marginTop: 32,
  },
  productCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 18,
    padding: 12,
    marginBottom: 12,
  },
  productHeader: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  productImage: {
    width: 80,
    height: 80,
    borderRadius: 18,
    backgroundColor: '#2a2a2a',
  },
  productInfo: {
    flex: 1,
    marginLeft: 12,
  },
  productTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  productName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    flex: 1,
  },
  productBrand: {
    fontSize: 12,
    color: '#6366f1',
    marginTop: 2,
  },
  productFlavor: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  productFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  productPrice: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  stockBadge: {
    backgroundColor: '#10b981',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 18,
  },
  stockBadgeLow: {
    backgroundColor: '#fbbf24',
  },
  stockBadgeEmpty: {
    backgroundColor: '#2E6BFF',
  },
  stockText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#000',
  },
  productActions: {
    flexDirection: 'row',
    gap: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 6,
    paddingHorizontal: 10,
    backgroundColor: '#0c0c0c',
    borderRadius: 18,
  },
  actionButtonText: {
    fontSize: 12,
    color: '#fff',
    fontWeight: '600',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: '#0c0c0c',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  modalCancel: {
    fontSize: 16,
    color: '#2E6BFF',
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    marginTop: 10,
    marginBottom: 24,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalHeaderTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  modalSave: {
    fontSize: 16,
    fontWeight: '600',
    color: '#10b981',
  },
  modalContent: {
    flex: 1,
    padding: 16,
  },
  imageUpload: {
    width: '100%',
    height: 200,
    borderRadius: 18,
    overflow: 'hidden',
    marginBottom: 20,
  },
  uploadedImage: {
    width: '100%',
    height: '100%',
  },
  uploadPlaceholder: {
    width: '100%',
    height: '100%',
    backgroundColor: '#1a1a1a',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#333',
    borderStyle: 'dashed',
  },
  uploadText: {
    marginTop: 8,
    fontSize: 14,
    color: '#666',
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 18,
    padding: 12,
    color: '#fff',
    fontSize: 16,
    marginBottom: 16,
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  halfInput: {
    flex: 1,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    marginBottom: 8,
  },
  pickerContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 16,
  },
  pickerOption: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#1a1a1a',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#333',
  },
  pickerOptionSelected: {
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  pickerOptionText: {
    fontSize: 14,
    color: '#999',
  },
  pickerOptionTextSelected: {
    color: '#fff',
    fontWeight: '600',
  },
  stockModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'center',
    padding: 20,
  },
  stockModalContent: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 20,
  },
  stockModalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  stockModalProduct: {
    fontSize: 16,
    color: '#6366f1',
    marginBottom: 4,
  },
  stockModalCurrent: {
    fontSize: 14,
    color: '#999',
    marginBottom: 20,
  },
  stockModalButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 20,
  },
  stockModalCancel: {
    flex: 1,
    padding: 14,
    backgroundColor: '#333',
    borderRadius: 18,
    alignItems: 'center',
  },
  stockModalCancelText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  stockModalSave: {
    flex: 1,
    padding: 14,
    backgroundColor: '#10b981',
    borderRadius: 18,
    alignItems: 'center',
  },
  stockModalSaveText: {
    color: '#000',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 24,
  },
  cancelButton: {
    flex: 1,
    padding: 16,
    backgroundColor: '#333',
    borderRadius: 18,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  saveButton: {
    flex: 1,
    padding: 16,
    backgroundColor: '#10b981',
    borderRadius: 18,
    alignItems: 'center',
  },
  saveButtonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: '600',
  },
});
