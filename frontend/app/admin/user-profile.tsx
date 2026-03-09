import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useState, useEffect } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { getLedgerLabel, getLedgerDescription } from '../../constants/ledger';
import { useToast } from '../../components/Toast';
import { useAuthStore } from '../../store/authStore';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const statusColors: Record<string, string> = {
  'Pending Payment': '#fbbf24',
  'Paid': '#3b82f6',
  'Ready for Pickup': '#10b981',
  'Completed': '#6b7280',
  'Cancelled': '#ef4444',
};

export default function AdminUserProfile() {
  const router = useRouter();
  const { userId } = useLocalSearchParams();
  const token = useAuthStore(state => state.token);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'orders' | 'reviews' | 'referral' | 'ledger' | 'notes' | 'credit'>('orders');
  const [ledger, setLedger] = useState<any[]>([]);
  const [ledgerLoaded, setLedgerLoaded] = useState(false);
  const [referrerInput, setReferrerInput] = useState('');
  const [assigningReferrer, setAssigningReferrer] = useState(false);
  const [adjustAmount, setAdjustAmount] = useState('');
  const [adjustDesc, setAdjustDesc] = useState('');
  const [adjusting, setAdjusting] = useState(false);
  const [creditAmount, setCreditAmount] = useState('');
  const [creditDesc, setCreditDesc] = useState('');
  const [adjustingCredit, setAdjustingCredit] = useState(false);
  const [adminNotes, setAdminNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [mergeTargetId, setMergeTargetId] = useState('');
  const [merging, setMerging] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [settingPassword, setSettingPassword] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (userId && token) loadProfile();
  }, [userId, token]);

  const loadProfile = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/admin/users/${userId}/profile`);
      setProfile(res.data);
      setAdminNotes(res.data?.user?.adminNotes || '');
    } catch (e) {
      console.error('Failed to load user profile', e);
    } finally {
      setLoading(false);
    }
  };

  const loadLedger = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/admin/users/${userId}/cloudz-ledger`);
      setLedger(res.data);
      setLedgerLoaded(true);
    } catch { toast.show('Failed to load ledger', 'error'); }
  };

  const assignReferrer = async () => {
    const val = referrerInput.trim() || null;
    setAssigningReferrer(true);
    try {
      const res = await axios.patch(`${API_URL}/api/admin/users/${userId}/referrer`, { referrerIdentifier: val });
      toast.show(res.data.warning || 'Referrer updated');
      setProfile((prev: any) => prev ? { ...prev, user: { ...prev.user, referredByUserId: val } } : prev);
      setReferrerInput('');
    } catch (e: any) {
      toast.show(e.response?.data?.detail || 'Failed to update referrer', 'error');
    } finally {
      setAssigningReferrer(false); }
  };

  const adjustCloudz = async () => {
    const amt = parseInt(adjustAmount);
    if (!adjustDesc.trim() || isNaN(amt)) { toast.show('Enter amount and description', 'error'); return; }
    setAdjusting(true);
    try {
      const res = await axios.post(`${API_URL}/api/admin/users/${userId}/cloudz-adjust`, { amount: amt, description: adjustDesc });
      toast.show(`Balance updated: ${res.data.newBalance} Cloudz`);
      setAdjustAmount(''); setAdjustDesc('');
      setProfile((prev: any) => prev ? { ...prev, user: { ...prev.user, loyaltyPoints: res.data.newBalance } } : prev);
      if (ledgerLoaded) loadLedger();
    } catch (e: any) {
      toast.show(e.response?.data?.detail || 'Failed to adjust', 'error');
    } finally { setAdjusting(false); }
  };

  const handleSetPassword = async () => {
    if (newPassword.length < 8) { toast.show('Password must be at least 8 characters', 'error'); return; }
    if (newPassword !== confirmPassword) { toast.show('Passwords do not match', 'error'); return; }
    setSettingPassword(true);
    try {
      await axios.post(`${API_URL}/api/admin/users/${userId}/set-password`, { newPassword });
      toast.show('Password updated successfully');
      setShowPasswordModal(false);
      setNewPassword(''); setConfirmPassword('');
    } catch (e: any) {
      toast.show(e.response?.data?.detail || 'Failed to set password', 'error');
    } finally { setSettingPassword(false); }
  };

  const handleToggleDisable = async () => {
    const isCurrentlyDisabled = profile?.user?.isDisabled || false;
    const action = isCurrentlyDisabled ? 'enable' : 'disable';
    Alert.alert(
      `${isCurrentlyDisabled ? 'Enable' : 'Disable'} Account`,
      `Are you sure you want to ${action} this account?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: isCurrentlyDisabled ? 'Enable' : 'Disable',
          style: isCurrentlyDisabled ? 'default' : 'destructive',
          onPress: async () => {
            try {
              await axios.patch(`${API_URL}/api/admin/users/${userId}`, { isDisabled: !isCurrentlyDisabled });
              setProfile((prev: any) => prev ? { ...prev, user: { ...prev.user, isDisabled: !isCurrentlyDisabled } } : prev);
              toast.show(`Account ${isCurrentlyDisabled ? 'enabled' : 'disabled'} successfully`);
            } catch (e: any) {
              toast.show(e.response?.data?.detail || 'Failed to update account status', 'error');
            }
          }
        }
      ]
    );
  };

  const handleCreditAdjust = async () => {
    const amt = parseFloat(creditAmount);
    if (!creditDesc.trim() || isNaN(amt)) { toast.show('Enter amount and description', 'error'); return; }
    setAdjustingCredit(true);
    try {
      const res = await axios.post(`${API_URL}/api/admin/users/${userId}/credit`, { amount: amt, description: creditDesc });
      toast.show(`Credit updated: $${res.data.newBalance?.toFixed(2)}`);
      setCreditAmount(''); setCreditDesc('');
      setProfile((prev: any) => prev ? { ...prev, user: { ...prev.user, creditBalance: res.data.newBalance } } : prev);
    } catch (e: any) {
      toast.show(e.response?.data?.detail || 'Failed to adjust credit', 'error');
    } finally { setAdjustingCredit(false); }
  };

  const handleSaveNotes = async () => {
    setSavingNotes(true);
    try {
      await axios.patch(`${API_URL}/api/admin/users/${userId}/notes`, { notes: adminNotes });
      toast.show('Notes saved');
    } catch (e: any) {
      toast.show(e.response?.data?.detail || 'Failed to save notes', 'error');
    } finally { setSavingNotes(false); }
  };

  const handleMerge = async () => {
    if (!mergeTargetId.trim()) { toast.show('Enter target user ID', 'error'); return; }
    setMerging(true);
    try {
      await axios.post(`${API_URL}/api/admin/users/merge`, { sourceUserId: userId, targetUserId: mergeTargetId.trim() });
      toast.show('Accounts merged successfully');
      setShowMergeModal(false); setMergeTargetId('');
      router.back();
    } catch (e: any) {
      toast.show(e.response?.data?.detail || 'Merge failed', 'error');
    } finally { setMerging(false); }
  };

  const handleForceLogout = async () => {
    Alert.alert(
      'Force Logout',
      'This will immediately invalidate all active sessions for this user.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Force Logout',
          style: 'destructive',
          onPress: async () => {
            try {
              await axios.post(`${API_URL}/api/admin/users/${userId}/force-logout`);
              toast.show('User sessions invalidated');
            } catch (e: any) {
              toast.show(e.response?.data?.detail || 'Failed to force logout', 'error');
            }
          }
        }
      ]
    );
  };

  const renderStars = (rating: number) => (
    <View style={{ flexDirection: 'row', gap: 2 }}>
      {[1, 2, 3, 4, 5].map(s => (
        <Ionicons key={s} name={s <= rating ? 'star' : 'star-outline'} size={12} color="#fbbf24" />
      ))}
    </View>
  );

  if (loading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['top']}>
        <View style={styles.centered}><Text style={styles.loadingText}>Loading...</Text></View>
      </SafeAreaView>
    );
  }

  if (!profile) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['top']}>
        <View style={styles.centered}><Text style={styles.loadingText}>User not found</Text></View>
      </SafeAreaView>
    );
  }

  const { user, orders, totalSpent, reviews } = profile;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['top']}>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.title}>Customer Profile</Text>
          <View style={{ width: 24 }} />
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {/* User Card */}
          <View style={styles.userCard}>
            <View style={styles.avatarCircle}>
              <Text style={styles.avatarText}>
                {(user.firstName?.[0] || '') + (user.lastName?.[0] || '') || '?'}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.userName}>{user.firstName} {user.lastName}</Text>
              <Text style={styles.userEmail}>{user.email}</Text>
              {user.phone ? <Text style={styles.userPhone}>{user.phone}</Text> : null}
              <Text style={styles.userId}>ID: {userId}</Text>
            </View>
          </View>

          {/* Stats Row */}
          <View style={styles.statsRow}>
            <View style={styles.statCard}>
              <Text style={styles.statValue}>{orders.length}</Text>
              <Text style={styles.statLabel}>Orders</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statValue}>${totalSpent.toFixed(2)}</Text>
              <Text style={styles.statLabel}>Total Spent</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statValue}>{(user.loyaltyPoints || 0).toLocaleString()}</Text>
              <Text style={styles.statLabel}>Cloudz</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statValue}>{reviews.length}</Text>
              <Text style={styles.statLabel}>Reviews</Text>
            </View>
          </View>

          {/* Admin Actions */}
          <View style={adminProfileStyles.actionsCard}>
            <Text style={adminProfileStyles.cardTitle}>Admin Actions</Text>
            <View style={adminProfileStyles.actionsRow}>
              <TouchableOpacity
                style={adminProfileStyles.actionPill}
                onPress={() => setShowPasswordModal(true)}
                data-testid="reset-password-btn"
              >
                <Ionicons name="key-outline" size={14} color="#fff" />
                <Text style={adminProfileStyles.actionPillText}>Reset Password</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[adminProfileStyles.actionPill, profile?.user?.isDisabled ? adminProfileStyles.enablePill : adminProfileStyles.disablePill]}
                onPress={handleToggleDisable}
                data-testid="toggle-disable-btn"
              >
                <Ionicons name={profile?.user?.isDisabled ? "checkmark-circle-outline" : "ban-outline"} size={14} color={profile?.user?.isDisabled ? '#10b981' : '#ef4444'} />
                <Text style={[adminProfileStyles.actionPillText, { color: profile?.user?.isDisabled ? '#10b981' : '#ef4444' }]}>
                  {profile?.user?.isDisabled ? 'Enable Account' : 'Disable Account'}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[adminProfileStyles.actionPill, adminProfileStyles.logoutPill]}
                onPress={handleForceLogout}
                data-testid="force-logout-btn"
              >
                <Ionicons name="log-out-outline" size={14} color="#fbbf24" />
                <Text style={[adminProfileStyles.actionPillText, { color: '#fbbf24' }]}>Force Logout</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[adminProfileStyles.actionPill, { borderColor: '#f9731633' }]}
                onPress={() => setShowMergeModal(true)}
                data-testid="merge-account-btn"
              >
                <Ionicons name="git-merge-outline" size={14} color="#f97316" />
                <Text style={[adminProfileStyles.actionPillText, { color: '#f97316' }]}>Merge Into</Text>
              </TouchableOpacity>
            </View>
            {profile?.user?.isDisabled && (
              <View style={adminProfileStyles.disabledBanner}>
                <Ionicons name="warning-outline" size={14} color="#ef4444" />
                <Text style={adminProfileStyles.disabledBannerText}>This account is disabled</Text>
              </View>
            )}
          </View>

          {/* Tabs */}
          <View style={styles.tabRow}>
            {(['orders', 'reviews', 'referral', 'ledger', 'notes', 'credit'] as const).map((t) => (
              <TouchableOpacity
                key={t}
                style={[styles.tab, tab === t && styles.tabActive]}
                onPress={() => { setTab(t); if (t === 'ledger' && !ledgerLoaded) loadLedger(); }}
              >
                <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
                  {t === 'orders' ? 'Orders' : t === 'reviews' ? 'Reviews' : t === 'referral' ? 'Referral' : t === 'ledger' ? 'Ledger' : t === 'notes' ? 'Notes' : 'Credit'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {tab === 'orders' ? (
            orders.length === 0 ? (
              <Text style={styles.emptyText}>No orders yet</Text>
            ) : (
              orders.map((order: any) => (
                <View key={order.id} style={styles.orderCard}>
                  <View style={styles.orderRow}>
                    <Text style={styles.orderId}>#{order.id.slice(-8)}</Text>
                    <View style={[styles.statusBadge, { backgroundColor: statusColors[order.status] || '#999' }]}>
                      <Text style={styles.statusText}>{order.status}</Text>
                    </View>
                  </View>
                  <View style={styles.orderRow}>
                    <Text style={styles.orderMeta}>
                      {new Date(order.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </Text>
                    <Text style={styles.orderTotal}>${order.total?.toFixed(2)}</Text>
                  </View>
                  <Text style={styles.orderItems}>
                    {order.items?.map((it: any) => `${it.quantity}x ${it.name}`).join(', ')}
                  </Text>
                </View>
              ))
            )
          ) : tab === 'reviews' ? (
            reviews.length === 0 ? (
              <Text style={styles.emptyText}>No reviews written</Text>
            ) : (
              reviews.map((rev: any) => (
                <View key={rev.id} style={styles.reviewCard}>
                  <View style={styles.orderRow}>
                    {renderStars(rev.rating)}
                    <Text style={styles.reviewDate}>
                      {new Date(rev.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </Text>
                  </View>
                  {rev.comment ? <Text style={styles.reviewComment}>{rev.comment}</Text> : null}
                </View>
              ))
            )
          ) : tab === 'referral' ? (
            <View>
              <View style={adminProfileStyles.infoCard}>
                <InfoRow label="Username" value={user.username ? `@${user.username}` : '—'} />
                <InfoRow label="Referral Code" value={user.referralCode || '—'} />
                <InfoRow label="Referred By" value={
                  user.referredByUser
                    ? (user.referredByUser.username ? `@${user.referredByUser.username}` : user.referredByUser.email || user.referredByUserId || 'None')
                    : (user.referredByUserId || 'None')
                } />
              </View>
              <View style={adminProfileStyles.infoCard}>
                <Text style={adminProfileStyles.cardTitle}>Assign / Change Referrer</Text>
                <TextInput
                  style={adminProfileStyles.inputField}
                  value={referrerInput}
                  onChangeText={setReferrerInput}
                  placeholder="Username, referral code, email or user ID"
                  placeholderTextColor="#555"
                  data-testid="referrer-input"
                />
                <TouchableOpacity
                  style={[adminProfileStyles.actionBtn, assigningReferrer && { opacity: 0.5 }]}
                  onPress={assignReferrer}
                  disabled={assigningReferrer}
                  data-testid="assign-referrer-btn"
                >
                  <Text style={adminProfileStyles.actionBtnText}>
                    {assigningReferrer ? 'Saving...' : referrerInput.trim() ? 'Assign Referrer' : 'Remove Referrer'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : tab === 'notes' ? (
            <View style={adminProfileStyles.infoCard}>
              <Text style={adminProfileStyles.cardTitle}>Account Notes</Text>
              <Text style={{ fontSize: 12, color: '#666', marginBottom: 10 }}>Private admin-only notes. Not visible to user.</Text>
              <TextInput
                style={[adminProfileStyles.inputField, { minHeight: 120, textAlignVertical: 'top' }]}
                value={adminNotes}
                onChangeText={setAdminNotes}
                placeholder="Add notes about this account..."
                placeholderTextColor="#555"
                multiline
                data-testid="admin-notes-input"
              />
              <TouchableOpacity
                style={[adminProfileStyles.actionBtn, savingNotes && { opacity: 0.5 }]}
                onPress={handleSaveNotes}
                disabled={savingNotes}
                data-testid="save-notes-btn"
              >
                <Text style={adminProfileStyles.actionBtnText}>{savingNotes ? 'Saving...' : 'Save Notes'}</Text>
              </TouchableOpacity>
            </View>
          ) : tab === 'credit' ? (
            <View style={adminProfileStyles.infoCard}>
              <Text style={adminProfileStyles.cardTitle}>Store Credit</Text>
              <Text style={adminProfileStyles.currentBalance}>Current Balance: ${(profile?.user?.creditBalance || 0).toFixed(2)}</Text>
              <TextInput
                style={adminProfileStyles.inputField}
                value={creditAmount}
                onChangeText={setCreditAmount}
                placeholder="Amount (e.g. 10.00 or -5.00)"
                placeholderTextColor="#555"
                keyboardType="numbers-and-punctuation"
                data-testid="credit-adjust-amount"
              />
              <TextInput
                style={adminProfileStyles.inputField}
                value={creditDesc}
                onChangeText={setCreditDesc}
                placeholder="Reason (e.g. Compensation for issue)"
                placeholderTextColor="#555"
                data-testid="credit-adjust-desc"
              />
              <TouchableOpacity
                style={[adminProfileStyles.actionBtn, adjustingCredit && { opacity: 0.5 }]}
                onPress={handleCreditAdjust}
                disabled={adjustingCredit}
                data-testid="credit-adjust-btn"
              >
                <Text style={adminProfileStyles.actionBtnText}>{adjustingCredit ? 'Saving...' : 'Apply Credit Adjustment'}</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View>
              <View style={adminProfileStyles.infoCard}>
                <Text style={adminProfileStyles.cardTitle}>Adjust Cloudz Balance</Text>
                <Text style={adminProfileStyles.currentBalance}>Current: {(user.loyaltyPoints || 0).toLocaleString()} Cloudz</Text>
                <TextInput
                  style={adminProfileStyles.inputField}
                  value={adjustAmount}
                  onChangeText={setAdjustAmount}
                  placeholder="Amount (e.g. 100 or -50)"
                  placeholderTextColor="#555"
                  keyboardType="numbers-and-punctuation"
                  data-testid="cloudz-adjust-amount"
                />
                <TextInput
                  style={adminProfileStyles.inputField}
                  value={adjustDesc}
                  onChangeText={setAdjustDesc}
                  placeholder="Description / reason"
                  placeholderTextColor="#555"
                  data-testid="cloudz-adjust-desc"
                />
                <TouchableOpacity
                  style={[adminProfileStyles.actionBtn, adjusting && { opacity: 0.5 }]}
                  onPress={adjustCloudz}
                  disabled={adjusting}
                  data-testid="cloudz-adjust-btn"
                >
                  <Text style={adminProfileStyles.actionBtnText}>{adjusting ? 'Saving...' : 'Apply Adjustment'}</Text>
                </TouchableOpacity>
              </View>
              {ledger.length === 0 ? (
                <Text style={styles.emptyText}>No ledger entries</Text>
              ) : (
                ledger.map((entry: any, i: number) => (
                  <View key={i} style={adminProfileStyles.ledgerRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={adminProfileStyles.ledgerDesc} numberOfLines={2}>{getLedgerDescription(entry)}</Text>
                      <Text style={adminProfileStyles.ledgerType}>{getLedgerLabel(entry.type)}</Text>
                      <Text style={adminProfileStyles.ledgerDate}>{new Date(entry.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</Text>
                    </View>
                    <Text style={[adminProfileStyles.ledgerAmount, entry.amount >= 0 ? adminProfileStyles.ledgerPos : adminProfileStyles.ledgerNeg]}>
                      {entry.amount >= 0 ? '+' : ''}{entry.amount}
                    </Text>
                  </View>
                ))
              )}
            </View>
          )}
          <View style={{ height: 40 }} />
        </ScrollView>
      </View>

      {/* Merge Account Modal */}
      <Modal visible={showMergeModal} animationType="slide" transparent>
        <View style={adminProfileStyles.modalOverlay}>
          <View style={adminProfileStyles.modalBox}>
            <View style={adminProfileStyles.modalTopRow}>
              <Text style={adminProfileStyles.modalTitle}>Merge Account</Text>
              <TouchableOpacity onPress={() => { setShowMergeModal(false); setMergeTargetId(''); }}>
                <Ionicons name="close" size={22} color="#666" />
              </TouchableOpacity>
            </View>
            <View style={{ backgroundColor: '#ef444415', borderRadius: 10, padding: 12, marginBottom: 16 }}>
              <Text style={{ fontSize: 12, color: '#ef4444', fontWeight: '600', lineHeight: 18 }}>
                Warning: This will move all orders, Cloudz, and credit from this account into the target account, then disable this account. This cannot be undone.
              </Text>
            </View>
            <Text style={adminProfileStyles.inputLabel}>Source Account</Text>
            <Text style={{ fontSize: 12, color: '#666', marginBottom: 12, padding: 10, backgroundColor: '#111', borderRadius: 8 }}>{String(userId)}</Text>

            <Text style={adminProfileStyles.inputLabel}>Target Account ID</Text>
            <TextInput
              style={adminProfileStyles.inputField}
              value={mergeTargetId}
              onChangeText={setMergeTargetId}
              placeholder="Paste target user ID"
              placeholderTextColor="#555"
              autoCapitalize="none"
              data-testid="merge-target-id-input"
            />
            <TouchableOpacity
              style={[adminProfileStyles.actionBtn, { backgroundColor: '#ef4444' }, merging && { opacity: 0.5 }]}
              onPress={handleMerge}
              disabled={merging}
              data-testid="confirm-merge-btn"
            >
              <Text style={adminProfileStyles.actionBtnText}>{merging ? 'Merging...' : 'Confirm Merge'}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Reset Password Modal */}
      <Modal visible={showPasswordModal} animationType="slide" transparent>
        <View style={adminProfileStyles.modalOverlay}>
          <View style={adminProfileStyles.modalBox}>
            <View style={adminProfileStyles.modalTopRow}>
              <Text style={adminProfileStyles.modalTitle}>Reset Password</Text>
              <TouchableOpacity onPress={() => { setShowPasswordModal(false); setNewPassword(''); setConfirmPassword(''); }}>
                <Ionicons name="close" size={22} color="#666" />
              </TouchableOpacity>
            </View>
            <Text style={adminProfileStyles.modalSubtitle}>Set a new password for this user.</Text>

            <Text style={adminProfileStyles.inputLabel}>New Password</Text>
            <TextInput
              style={adminProfileStyles.inputField}
              value={newPassword}
              onChangeText={setNewPassword}
              placeholder="Min. 8 characters"
              placeholderTextColor="#555"
              secureTextEntry
              autoCapitalize="none"
              data-testid="new-password-input"
            />

            <Text style={adminProfileStyles.inputLabel}>Confirm Password</Text>
            <TextInput
              style={adminProfileStyles.inputField}
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              placeholder="Repeat new password"
              placeholderTextColor="#555"
              secureTextEntry
              autoCapitalize="none"
              data-testid="confirm-password-input"
            />

            <TouchableOpacity
              style={[adminProfileStyles.actionBtn, settingPassword && { opacity: 0.5 }]}
              onPress={handleSetPassword}
              disabled={settingPassword}
              data-testid="submit-password-btn"
            >
              <Text style={adminProfileStyles.actionBtnText}>{settingPassword ? 'Saving...' : 'Update Password'}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0c0c0c' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: '#999', fontSize: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16 },
  title: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  content: { flex: 1, padding: 16 },
  userCard: { flexDirection: 'row', alignItems: 'center', gap: 14, backgroundColor: '#1a1a1a', borderRadius: 16, padding: 16, marginBottom: 14 },
  avatarCircle: { width: 54, height: 54, borderRadius: 27, backgroundColor: '#6366f1', alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 20, fontWeight: '800', color: '#fff' },
  userName: { fontSize: 16, fontWeight: '700', color: '#fff' },
  userEmail: { fontSize: 13, color: '#999', marginTop: 2 },
  userPhone: { fontSize: 12, color: '#666', marginTop: 1 },
  userId: { fontSize: 10, color: '#444', marginTop: 4 },
  statsRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  statCard: { flex: 1, backgroundColor: '#1a1a1a', borderRadius: 12, padding: 12, alignItems: 'center' },
  statValue: { fontSize: 16, fontWeight: '800', color: '#fff', marginBottom: 2 },
  statLabel: { fontSize: 10, color: '#666', textAlign: 'center' },
  tabRow: { flexDirection: 'row', backgroundColor: '#1a1a1a', borderRadius: 12, padding: 4, marginBottom: 14 },
  tab: { flex: 1, paddingVertical: 9, alignItems: 'center', borderRadius: 10 },
  tabActive: { backgroundColor: '#6366f1' },
  tabText: { fontSize: 13, fontWeight: '600', color: '#666' },
  tabTextActive: { color: '#fff' },
  emptyText: { fontSize: 14, color: '#555', textAlign: 'center', paddingVertical: 24 },
  orderCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 14, marginBottom: 8 },
  orderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  orderId: { fontSize: 14, fontWeight: '700', color: '#fff' },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10 },
  statusText: { fontSize: 10, fontWeight: '700', color: '#000' },
  orderMeta: { fontSize: 12, color: '#666' },
  orderTotal: { fontSize: 14, fontWeight: '700', color: '#10b981' },
  orderItems: { fontSize: 12, color: '#555', marginTop: 4 },
  reviewCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 14, marginBottom: 8 },
  reviewComment: { fontSize: 13, color: '#ccc', lineHeight: 19, marginTop: 6 },
  reviewDate: { fontSize: 11, color: '#444' },
});


function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#222' }}>
      <Text style={{ fontSize: 12, color: '#666' }}>{label}</Text>
      <Text style={{ fontSize: 12, color: '#fff', fontWeight: '600', maxWidth: '60%', textAlign: 'right' }} selectable>{value}</Text>
    </View>
  );
}

const adminProfileStyles = StyleSheet.create({
  infoCard: { backgroundColor: '#1a1a1a', borderRadius: 14, padding: 14, marginBottom: 12 },
  cardTitle: { fontSize: 13, fontWeight: '800', color: '#fff', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 },
  currentBalance: { fontSize: 12, color: '#10b981', marginBottom: 10, fontWeight: '700' },
  inputField: { backgroundColor: '#0c0c0c', borderRadius: 10, padding: 11, color: '#fff', fontSize: 13, borderWidth: 1, borderColor: '#333', marginBottom: 8 },
  actionBtn: { backgroundColor: '#6366f1', borderRadius: 10, paddingVertical: 11, alignItems: 'center' },
  actionBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  ledgerRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1a1a1a', borderRadius: 10, padding: 12, marginBottom: 6 },
  ledgerDesc: { fontSize: 13, color: '#ccc' },
  ledgerType: { fontSize: 10, color: '#888', marginTop: 2 },
  ledgerDate: { fontSize: 11, color: '#444', marginTop: 2 },
  ledgerAmount: { fontSize: 16, fontWeight: '800', minWidth: 50, textAlign: 'right' },
  ledgerPos: { color: '#10b981' },
  ledgerNeg: { color: '#ef4444' },
  actionsCard: { backgroundColor: '#1a1a1a', borderRadius: 14, padding: 14, marginBottom: 14 },
  actionsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  actionPill: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: '#2a2a2a', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, borderWidth: 1, borderColor: '#333' },
  disablePill: { borderColor: '#ef444433' },
  enablePill: { borderColor: '#10b98133' },
  logoutPill: { borderColor: '#fbbf2433' },
  actionPillText: { fontSize: 12, fontWeight: '700', color: '#fff' },
  disabledBanner: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#ef444415', borderRadius: 8, padding: 8, marginTop: 10 },
  disabledBannerText: { fontSize: 12, color: '#ef4444', fontWeight: '600' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.85)', justifyContent: 'flex-end' },
  modalBox: { backgroundColor: '#1a1a1a', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, paddingBottom: 40 },
  modalTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#fff' },
  modalSubtitle: { fontSize: 13, color: '#666', marginBottom: 20 },
  inputLabel: { fontSize: 12, fontWeight: '600', color: '#aaa', marginBottom: 6, marginTop: 4 },
});
