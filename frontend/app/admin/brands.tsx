import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal, Image, Alert, RefreshControl, Switch } from 'react-native';
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Brand {
  id: string;
  name: string;
  image?: string;
  isActive: boolean;
  displayOrder: number;
  productCount: number;
}

export default function BrandsManagement() {
  const router = useRouter();
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  
  const [formData, setFormData] = useState({
    name: '',
    image: '',
    isActive: true,
    displayOrder: 0,
  });

  useEffect(() => {
    loadBrands();
  }, []);

  const loadBrands = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/brands?active_only=false`);
      setBrands(response.data.sort((a: Brand, b: Brand) => a.displayOrder - b.displayOrder));
    } catch (error) {
      console.error('Failed to load brands:', error);
      Alert.alert('Error', 'Failed to load brands');
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
      quality: 0.5,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      setFormData({ ...formData, image: `data:image/jpeg;base64,${result.assets[0].base64}` });
    }
  };

  const handleSaveBrand = async () => {
    if (!formData.name) {
      Alert.alert('Error', 'Please enter a brand name');
      return;
    }

    try {
      if (editingBrand) {
        await axios.patch(`${API_URL}/api/brands/${editingBrand.id}`, formData);
        Alert.alert('Success', 'Brand updated successfully');
      } else {
        await axios.post(`${API_URL}/api/brands`, formData);
        Alert.alert('Success', 'Brand created successfully');
      }
      setShowModal(false);
      resetForm();
      loadBrands();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save brand');
    }
  };

  const handleDeleteBrand = (brand: Brand) => {
    if (brand.productCount > 0) {
      Alert.alert(
        'Cannot Delete Brand',
        `This brand has ${brand.productCount} product(s). Please reassign or delete products first.`,
        [{ text: 'OK' }]
      );
      return;
    }

    Alert.alert(
      'Delete Brand',
      `Are you sure you want to delete "${brand.name}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await axios.delete(`${API_URL}/api/brands/${brand.id}`);
              Alert.alert('Success', 'Brand deleted');
              loadBrands();
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to delete brand');
            }
          }
        }
      ]
    );
  };

  const toggleActive = async (brand: Brand) => {
    try {
      await axios.patch(`${API_URL}/api/brands/${brand.id}`, { isActive: !brand.isActive });
      loadBrands();
    } catch (error) {
      Alert.alert('Error', 'Failed to update brand status');
    }
  };

  const openEditModal = (brand: Brand) => {
    setEditingBrand(brand);
    setFormData({
      name: brand.name,
      image: brand.image || '',
      isActive: brand.isActive,
      displayOrder: brand.displayOrder,
    });
    setShowModal(true);
  };

  const resetForm = () => {
    setEditingBrand(null);
    setFormData({
      name: '',
      image: '',
      isActive: true,
      displayOrder: 0,
    });
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Brands</Text>
        <TouchableOpacity onPress={() => { resetForm(); setShowModal(true); }}>
          <Ionicons name="add-circle" size={28} color="#dc2626" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadBrands(); }} tintColor="#dc2626" />}
      >
        {loading ? (
          <Text style={styles.emptyText}>Loading...</Text>
        ) : brands.length === 0 ? (
          <Text style={styles.emptyText}>No brands yet. Tap + to add one.</Text>
        ) : (
          brands.map((brand) => (
            <View key={brand.id} style={styles.brandCard}>
              <View style={styles.brandHeader}>
                {brand.image ? (
                  <Image source={{ uri: brand.image }} style={styles.brandLogo} />
                ) : (
                  <View style={styles.brandLogoPlaceholder}>
                    <Ionicons name="flash" size={32} color="#666" />
                  </View>
                )}
                <View style={styles.brandInfo}>
                  <Text style={styles.brandName}>{brand.name}</Text>
                  <Text style={styles.brandProducts}>{brand.productCount} product(s)</Text>
                  <View style={styles.brandMeta}>
                    <View style={[styles.statusBadge, { backgroundColor: brand.isActive ? '#10b981' : '#666' }]}>
                      <Text style={styles.statusText}>{brand.isActive ? 'Active' : 'Hidden'}</Text>
                    </View>
                    <Text style={styles.displayOrder}>Order: {brand.displayOrder}</Text>
                  </View>
                </View>
              </View>

              <View style={styles.brandActions}>
                <TouchableOpacity style={styles.actionButton} onPress={() => toggleActive(brand)}>
                  <Ionicons name={brand.isActive ? "eye" : "eye-off"} size={18} color={brand.isActive ? "#10b981" : "#666"} />
                  <Text style={[styles.actionButtonText, !brand.isActive && { color: '#666' }]}>
                    {brand.isActive ? 'Visible' : 'Hidden'}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity style={styles.actionButton} onPress={() => openEditModal(brand)}>
                  <Ionicons name="pencil" size={18} color="#6366f1" />
                  <Text style={styles.actionButtonText}>Edit</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                  style={[styles.actionButton, brand.productCount > 0 && styles.actionButtonDisabled]}
                  onPress={() => handleDeleteBrand(brand)}
                  disabled={brand.productCount > 0}
                >
                  <Ionicons name="trash" size={18} color={brand.productCount > 0 ? "#333" : "#dc2626"} />
                  <Text style={[styles.actionButtonText, brand.productCount > 0 && { color: '#333' }]}>Delete</Text>
                </TouchableOpacity>
              </View>
            </View>
          ))
        )}
      </ScrollView>

      {/* Add/Edit Brand Modal */}
      <Modal visible={showModal} animationType="slide" onRequestClose={() => setShowModal(false)}>
        <SafeAreaView style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={() => setShowModal(false)}>
              <Text style={styles.modalCancel}>Cancel</Text>
            </TouchableOpacity>
            <Text style={styles.modalTitle}>{editingBrand ? 'Edit Brand' : 'Add Brand'}</Text>
            <TouchableOpacity onPress={handleSaveBrand}>
              <Text style={styles.modalSave}>Save</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalContent}>
            <TouchableOpacity style={styles.logoUpload} onPress={pickImage}>
              {formData.image ? (
                <Image source={{ uri: formData.image }} style={styles.uploadedLogo} />
              ) : (
                <View style={styles.uploadPlaceholder}>
                  <Ionicons name="flash" size={48} color="#666" />
                  <Text style={styles.uploadText}>Tap to upload logo</Text>
                  <Text style={styles.uploadSubtext}>(Optional)</Text>
                </View>
              )}
            </TouchableOpacity>

            <Text style={styles.inputLabel}>Brand Name *</Text>
            <TextInput
              style={styles.input}
              value={formData.name}
              onChangeText={(text) => setFormData({ ...formData, name: text })}
              placeholder="Enter brand name"
              placeholderTextColor="#666"
            />

            <Text style={styles.inputLabel}>Display Order</Text>
            <TextInput
              style={styles.input}
              value={String(formData.displayOrder)}
              onChangeText={(text) => setFormData({ ...formData, displayOrder: parseInt(text) || 0 })}
              keyboardType="numeric"
              placeholder="0 = first, higher = later"
              placeholderTextColor="#666"
            />

            <View style={styles.switchRow}>
              <View>
                <Text style={styles.inputLabel}>Visible on Storefront</Text>
                <Text style={styles.inputSubtext}>Show this brand to customers</Text>
              </View>
              <Switch
                value={formData.isActive}
                onValueChange={(value) => setFormData({ ...formData, isActive: value })}
                trackColor={{ false: '#333', true: '#10b981' }}
                thumbColor="#fff"
              />
            </View>
          </ScrollView>
        </View>
      </Modal>
    </View>
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
  brandCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  brandHeader: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  brandLogo: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#2a2a2a',
  },
  brandLogoPlaceholder: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#2a2a2a',
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandInfo: {
    flex: 1,
    marginLeft: 16,
  },
  brandName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  brandProducts: {
    fontSize: 14,
    color: '#999',
    marginBottom: 8,
  },
  brandMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#000',
  },
  displayOrder: {
    fontSize: 12,
    color: '#666',
  },
  brandActions: {
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
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#0c0c0c',
    borderRadius: 8,
  },
  actionButtonDisabled: {
    opacity: 0.4,
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
    color: '#dc2626',
  },
  modalTitle: {
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
  logoUpload: {
    width: 120,
    height: 120,
    borderRadius: 60,
    overflow: 'hidden',
    alignSelf: 'center',
    marginBottom: 24,
  },
  uploadedLogo: {
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
    color: '#999',
  },
  uploadSubtext: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 8,
  },
  inputSubtext: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  input: {
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    padding: 12,
    color: '#fff',
    fontSize: 16,
    marginBottom: 16,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    marginBottom: 8,
  },
});
