import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal, Image, Alert, RefreshControl, Switch } from 'react-native';
import { useState, useEffect, useCallback } from 'react';
import { useRouter, useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  phone?: string;
  isAdmin: boolean;
  loyaltyPoints: number;
  profilePhoto?: string;
}

export default function UsersManagement() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    isAdmin: false,
    loyaltyPoints: 0,
    profilePhoto: '',
  });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/users`);
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to load users:', error);
      Alert.alert('Error', 'Failed to load users');
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
      quality: 0.3,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      setFormData({ ...formData, profilePhoto: `data:image/jpeg;base64,${result.assets[0].base64}` });
    }
  };

  const handleSaveUser = async () => {
    if (!editingUser) return;

    try {
      await axios.patch(`${API_URL}/api/admin/users/${editingUser.id}`, formData);
      Alert.alert('Success', 'User updated successfully');
      setShowModal(false);
      loadUsers();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to update user');
    }
  };

  const toggleAdmin = async (user: User) => {
    Alert.alert(
      user.isAdmin ? 'Remove Admin Access' : 'Grant Admin Access',
      `Are you sure you want to ${user.isAdmin ? 'remove admin access from' : 'grant admin access to'} ${user.firstName} ${user.lastName}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: user.isAdmin ? 'Remove' : 'Grant',
          style: user.isAdmin ? 'destructive' : 'default',
          onPress: async () => {
            try {
              await axios.patch(`${API_URL}/api/admin/users/${user.id}`, { isAdmin: !user.isAdmin });
              loadUsers();
              Alert.alert('Success', `Admin access ${user.isAdmin ? 'removed' : 'granted'}`);
            } catch (error) {
              Alert.alert('Error', 'Failed to update admin status');
            }
          }
        }
      ]
    );
  };

  const openEditModal = (user: User) => {
    setEditingUser(user);
    setFormData({
      firstName: user.firstName,
      lastName: user.lastName,
      email: user.email,
      phone: user.phone || '',
      isAdmin: user.isAdmin,
      loyaltyPoints: user.loyaltyPoints,
      profilePhoto: user.profilePhoto || '',
    });
    setShowModal(true);
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Users</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadUsers(); }} tintColor="#dc2626" />}
      >
        {loading ? (
          <Text style={styles.emptyText}>Loading...</Text>
        ) : users.length === 0 ? (
          <Text style={styles.emptyText}>No users found</Text>
        ) : (
          users.map((user) => (
            <View key={user.id} style={styles.userCard}>
              <View style={styles.userHeader}>
                {user.profilePhoto ? (
                  <Image source={{ uri: user.profilePhoto }} style={styles.userAvatar} />
                ) : (
                  <View style={styles.userAvatarPlaceholder}>
                    <Text style={styles.userInitials}>
                      {user.firstName.charAt(0)}{user.lastName.charAt(0)}
                    </Text>
                  </View>
                )}
                <View style={styles.userInfo}>
                  <View style={styles.userNameRow}>
                    <Text style={styles.userName}>{user.firstName} {user.lastName}</Text>
                    {user.isAdmin && (
                      <View style={styles.adminBadge}>
                        <Ionicons name="shield" size={12} color="#dc2626" />
                        <Text style={styles.adminBadgeText}>Admin</Text>
                      </View>
                    )}
                  </View>
                  <Text style={styles.userEmail}>{user.email}</Text>
                  {user.phone && <Text style={styles.userPhone}>{user.phone}</Text>}
                  <View style={styles.userMeta}>
                    <View style={styles.loyaltyBadge}>
                      <Ionicons name="star" size={12} color="#fbbf24" />
                      <Text style={styles.loyaltyText}>{user.loyaltyPoints} pts</Text>
                    </View>
                  </View>
                </View>
              </View>

              <View style={styles.userActions}>
                <TouchableOpacity style={styles.actionButton} onPress={() => openEditModal(user)}>
                  <Ionicons name="pencil" size={18} color="#6366f1" />
                  <Text style={styles.actionButtonText}>Edit</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                  style={[styles.actionButton, user.isAdmin && styles.adminActionButton]}
                  onPress={() => toggleAdmin(user)}
                >
                  <Ionicons name="shield" size={18} color={user.isAdmin ? "#dc2626" : "#10b981"} />
                  <Text style={[styles.actionButtonText, user.isAdmin && { color: '#dc2626' }]}>
                    {user.isAdmin ? 'Revoke Admin' : 'Make Admin'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          ))
        )}
      </ScrollView>

      {/* Edit User Modal */}
      <Modal visible={showModal} animationType="slide" presentationStyle="fullScreen">
        <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['bottom']}>
          <View style={{ flex: 1, paddingTop: 50 }}>
            <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
            <View style={styles.modalHeader}>
              <TouchableOpacity onPress={() => setShowModal(false)}>
                <Text style={{ color: '#ff3b30', fontSize: 16 }}>Cancel</Text>
              </TouchableOpacity>
              <Text style={styles.modalHeaderTitle}>Edit User</Text>
              <TouchableOpacity onPress={handleSaveUser}>
                <Text style={{ color: '#4CAF50', fontSize: 16 }}>Save</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.avatarUpload} onPress={pickImage}>
              {formData.profilePhoto ? (
                <Image source={{ uri: formData.profilePhoto }} style={styles.uploadedAvatar} />
              ) : (
                <View style={styles.avatarPlaceholder}>
                  <Ionicons name="person" size={48} color="#666" />
                  <Text style={styles.uploadText}>Tap to upload photo</Text>
                </View>
              )}
            </TouchableOpacity>

              <Text style={styles.inputLabel}>First Name</Text>
              <TextInput
                style={styles.input}
                value={formData.firstName}
                onChangeText={(text) => setFormData({ ...formData, firstName: text })}
                placeholder="First name"
                placeholderTextColor="#666"
              />

              <Text style={styles.inputLabel}>Last Name</Text>
              <TextInput
                style={styles.input}
                value={formData.lastName}
                onChangeText={(text) => setFormData({ ...formData, lastName: text })}
                placeholder="Last name"
                placeholderTextColor="#666"
              />

              <Text style={styles.inputLabel}>Email</Text>
              <TextInput
                style={styles.input}
                value={formData.email}
                onChangeText={(text) => setFormData({ ...formData, email: text })}
                placeholder="email@example.com"
                placeholderTextColor="#666"
                keyboardType="email-address"
                autoCapitalize="none"
              />

              <Text style={styles.inputLabel}>Phone</Text>
              <TextInput
                style={styles.input}
                value={formData.phone}
                onChangeText={(text) => setFormData({ ...formData, phone: text })}
                placeholder="Phone number"
                placeholderTextColor="#666"
                keyboardType="phone-pad"
              />

              <Text style={styles.inputLabel}>Cloudz Points</Text>
              <TextInput
                style={styles.input}
                value={String(formData.loyaltyPoints)}
                onChangeText={(text) => setFormData({ ...formData, loyaltyPoints: parseInt(text) || 0 })}
                keyboardType="numeric"
                placeholderTextColor="#666"
              />

              <View style={styles.switchRow}>
                <View>
                  <Text style={styles.inputLabel}>Admin Access</Text>
                  <Text style={styles.inputSubtext}>Grant full admin privileges</Text>
                </View>
                <Switch
                  value={formData.isAdmin}
                  onValueChange={(value) => setFormData({ ...formData, isAdmin: value })}
                  trackColor={{ false: '#333', true: '#dc2626' }}
                  thumbColor="#fff"
                />
              </View>
            </ScrollView>
          </View>
        </SafeAreaView>
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
  userCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  userHeader: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  userAvatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#2a2a2a',
  },
  userAvatarPlaceholder: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#6366f1',
    alignItems: 'center',
    justifyContent: 'center',
  },
  userInitials: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  userInfo: {
    flex: 1,
    marginLeft: 16,
  },
  userNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  userName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  adminBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#dc2626',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  adminBadgeText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#fff',
  },
  userEmail: {
    fontSize: 14,
    color: '#999',
    marginBottom: 4,
  },
  userPhone: {
    fontSize: 14,
    color: '#999',
    marginBottom: 8,
  },
  userMeta: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  loyaltyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#2a2a1a',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  loyaltyText: {
    fontSize: 12,
    color: '#fbbf24',
    fontWeight: '600',
  },
  userActions: {
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
  adminActionButton: {
    borderWidth: 1,
    borderColor: '#dc2626',
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
  avatarUpload: {
    width: 120,
    height: 120,
    borderRadius: 60,
    overflow: 'hidden',
    alignSelf: 'center',
    marginBottom: 24,
  },
  uploadedAvatar: {
    width: '100%',
    height: '100%',
  },
  avatarPlaceholder: {
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
    fontSize: 12,
    color: '#666',
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
    marginTop: 8,
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
    borderRadius: 8,
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
    borderRadius: 8,
    alignItems: 'center',
  },
  saveButtonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: '600',
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
});
