import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useToast } from '../../components/Toast';
import { useAuthStore } from '../../store/authStore';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Review {
  id: string;
  productId: string;
  productName: string;
  userId: string;
  userName: string;
  rating: number;
  comment?: string;
  createdAt: string;
  isHidden: boolean;
}

export default function AdminReviews() {
  const router = useRouter();
  const toast = useToast();
  const token = useAuthStore(state => state.token);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editReview, setEditReview] = useState<Review | null>(null);
  const [editComment, setEditComment] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (token) loadReviews(); }, [token]);

  const loadReviews = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/admin/reviews`);
      setReviews(res.data);
    } catch {
      toast.show('Failed to load reviews', 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const toggleHide = async (review: Review) => {
    try {
      await axios.patch(`${API_URL}/api/admin/reviews/${review.id}`, { isHidden: !review.isHidden });
      setReviews(prev => prev.map(r => r.id === review.id ? { ...r, isHidden: !r.isHidden } : r));
      toast.show(review.isHidden ? 'Review unhidden' : 'Review hidden');
    } catch {
      toast.show('Failed to update review', 'error');
    }
  };

  const deleteReview = async (id: string) => {
    try {
      await axios.delete(`${API_URL}/api/admin/reviews/${id}`);
      setReviews(prev => prev.filter(r => r.id !== id));
      toast.show('Review deleted');
    } catch {
      toast.show('Failed to delete review', 'error');
    }
  };

  const openEdit = (review: Review) => {
    setEditReview(review);
    setEditComment(review.comment || '');
  };

  const saveEdit = async () => {
    if (!editReview) return;
    setSaving(true);
    try {
      await axios.patch(`${API_URL}/api/admin/reviews/${editReview.id}`, { comment: editComment });
      setReviews(prev => prev.map(r => r.id === editReview.id ? { ...r, comment: editComment } : r));
      setEditReview(null);
      toast.show('Review updated');
    } catch {
      toast.show('Failed to update review', 'error');
    } finally {
      setSaving(false);
    }
  };

  const renderStars = (rating: number) => (
    <View style={styles.starsRow}>
      {[1, 2, 3, 4, 5].map(s => (
        <Ionicons key={s} name={s <= rating ? 'star' : 'star-outline'} size={13} color="#fbbf24" />
      ))}
    </View>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['top']}>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.title}>Review Moderation</Text>
          <TouchableOpacity onPress={() => { setRefreshing(true); loadReviews(); }}>
            <Ionicons name="refresh" size={24} color="#fff" />
          </TouchableOpacity>
        </View>

        <ScrollView
          style={styles.content}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadReviews(); }} tintColor="#6366f1" />}
        >
          {loading ? (
            <Text style={styles.emptyText}>Loading reviews...</Text>
          ) : reviews.length === 0 ? (
            <Text style={styles.emptyText}>No reviews yet</Text>
          ) : (
            reviews.map(review => (
              <View key={review.id} style={[styles.reviewCard, review.isHidden && styles.reviewCardHidden]}>
                <View style={styles.reviewHeader}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.productName}>{review.productName}</Text>
                    <Text style={styles.userName}>{review.userName}</Text>
                  </View>
                  <View style={{ alignItems: 'flex-end', gap: 4 }}>
                    {renderStars(review.rating)}
                    {review.isHidden && (
                      <View style={styles.hiddenBadge}>
                        <Text style={styles.hiddenBadgeText}>Hidden</Text>
                      </View>
                    )}
                  </View>
                </View>

                {review.comment ? (
                  <Text style={styles.comment}>{review.comment}</Text>
                ) : (
                  <Text style={styles.noComment}>No comment</Text>
                )}

                <Text style={styles.reviewDate}>
                  {new Date(review.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </Text>

                <View style={styles.actionRow}>
                  <TouchableOpacity
                    style={[styles.actionBtn, { borderColor: review.isHidden ? '#10b981' : '#fbbf24' }]}
                    onPress={() => toggleHide(review)}
                    data-testid={`review-toggle-${review.id}`}
                  >
                    <Ionicons name={review.isHidden ? 'eye-outline' : 'eye-off-outline'} size={14} color={review.isHidden ? '#10b981' : '#fbbf24'} />
                    <Text style={[styles.actionBtnText, { color: review.isHidden ? '#10b981' : '#fbbf24' }]}>
                      {review.isHidden ? 'Unhide' : 'Hide'}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.actionBtn, { borderColor: '#6366f1' }]}
                    onPress={() => openEdit(review)}
                    data-testid={`review-edit-${review.id}`}
                  >
                    <Ionicons name="create-outline" size={14} color="#6366f1" />
                    <Text style={[styles.actionBtnText, { color: '#6366f1' }]}>Edit</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.actionBtn, { borderColor: '#ef4444' }]}
                    onPress={() => deleteReview(review.id)}
                    data-testid={`review-delete-${review.id}`}
                  >
                    <Ionicons name="trash-outline" size={14} color="#ef4444" />
                    <Text style={[styles.actionBtnText, { color: '#ef4444' }]}>Delete</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </ScrollView>

        <Modal visible={!!editReview} transparent animationType="fade" onRequestClose={() => setEditReview(null)}>
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <Text style={styles.modalTitle}>Edit Review</Text>
              <Text style={styles.modalSubtitle}>{editReview?.productName} — {editReview?.userName}</Text>
              <TextInput
                style={styles.editInput}
                value={editComment}
                onChangeText={setEditComment}
                placeholder="Review text..."
                placeholderTextColor="#555"
                multiline
                numberOfLines={4}
              />
              <View style={styles.modalActions}>
                <TouchableOpacity style={styles.modalCancelBtn} onPress={() => setEditReview(null)}>
                  <Text style={styles.modalCancelText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.modalSaveBtn, saving && { opacity: 0.5 }]}
                  onPress={saveEdit}
                  disabled={saving}
                >
                  <Text style={styles.modalSaveText}>{saving ? 'Saving...' : 'Save'}</Text>
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
  container: { flex: 1, backgroundColor: '#0c0c0c' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16 },
  title: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  content: { flex: 1, padding: 16 },
  emptyText: { fontSize: 16, color: '#999', textAlign: 'center', marginTop: 32 },
  reviewCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
  },
  reviewCardHidden: {
    opacity: 0.55,
    borderWidth: 1,
    borderColor: '#333',
  },
  reviewHeader: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 8 },
  productName: { fontSize: 14, fontWeight: '700', color: '#fff' },
  userName: { fontSize: 12, color: '#666', marginTop: 2 },
  starsRow: { flexDirection: 'row', gap: 2 },
  hiddenBadge: { backgroundColor: '#ef444420', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 },
  hiddenBadgeText: { fontSize: 10, color: '#ef4444', fontWeight: '700' },
  comment: { fontSize: 13, color: '#ccc', lineHeight: 19, marginBottom: 6 },
  noComment: { fontSize: 12, color: '#555', marginBottom: 6, fontStyle: 'italic' },
  reviewDate: { fontSize: 11, color: '#444', marginBottom: 10 },
  actionRow: { flexDirection: 'row', gap: 6 },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 7, borderRadius: 8, borderWidth: 1, flex: 1, justifyContent: 'center' },
  actionBtnText: { fontSize: 12, fontWeight: '600' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#1a1a1a', borderRadius: 16, padding: 20, width: '100%', maxWidth: 400 },
  modalTitle: { fontSize: 18, fontWeight: 'bold', color: '#fff', marginBottom: 4 },
  modalSubtitle: { fontSize: 13, color: '#666', marginBottom: 14 },
  editInput: { backgroundColor: '#0c0c0c', borderRadius: 10, padding: 12, color: '#fff', fontSize: 14, borderWidth: 1, borderColor: '#333', minHeight: 90, textAlignVertical: 'top', marginBottom: 14 },
  modalActions: { flexDirection: 'row', gap: 10 },
  modalCancelBtn: { flex: 1, padding: 13, borderRadius: 10, backgroundColor: '#0c0c0c', alignItems: 'center' },
  modalCancelText: { color: '#999', fontSize: 14, fontWeight: '600' },
  modalSaveBtn: { flex: 1, padding: 13, borderRadius: 10, backgroundColor: '#6366f1', alignItems: 'center' },
  modalSaveText: { color: '#fff', fontSize: 14, fontWeight: '700' },
});
