import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, Image, ActivityIndicator, Platform, Share } from 'react-native';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'expo-router';
import { useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../../store/authStore';
import { useCartStore } from '../../store/cartStore';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme';
import axios from 'axios';
import * as Clipboard from 'expo-clipboard';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface TierInfo {
  id: string;
  name: string;
  pointsRequired: number;
  reward: number;
  unlocked: boolean;
}

interface RedemptionRecord {
  id: string;
  tierId: string;
  tierName: string;
  rewardAmount: number;
  pointsSpent: number;
  used: boolean;
  createdAt: string;
}

interface StreakInfo {
  streak: number;
  currentBonus: number;
  nextBonus: number;
  daysUntilExpiry: number;
}

const TIER_ACCENT: Record<string, string> = {
  tier_1: '#CD7F32',
  tier_2: '#C0C0C0',
  tier_3: '#FFD700',
  tier_4: '#A8B8D0',
  tier_5: '#B9F2FF',
};

export default function Account() {
  const router = useRouter();
  const { user, logout, token, refreshUser } = useAuthStore();
  const clearCart = useCartStore(state => state.clearCart);
  const [highestTier, setHighestTier] = useState<TierInfo | null>(null);
  const [history, setHistory] = useState<RedemptionRecord[]>([]);
  const [streakInfo, setStreakInfo] = useState<StreakInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const loadAccountData = useCallback(async () => {
    try {
      const [tiersRes, historyRes, streakRes] = await Promise.all([
        axios.get(`${API_URL}/api/loyalty/tiers`, authHeaders),
        axios.get(`${API_URL}/api/loyalty/history`, authHeaders),
        axios.get(`${API_URL}/api/loyalty/streak`, authHeaders),
      ]);
      // Find highest unlocked tier
      const unlocked = (tiersRes.data.tiers as TierInfo[]).filter(t => t.unlocked);
      setHighestTier(unlocked.length > 0 ? unlocked[unlocked.length - 1] : null);
      setHistory(historyRes.data.slice(0, 5)); // Show last 5
      setStreakInfo(streakRes.data);
    } catch (error) {
      console.error('Failed to load account data:', error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useFocusEffect(
    useCallback(() => {
      refreshUser();
      loadAccountData();
    }, [loadAccountData])
  );

  const referralLink = user?.referralCode
    ? `https://clouddistrict.club/register?ref=${user.referralCode}`
    : '';

  const handleCopyCode = async () => {
    if (user?.referralCode) {
      await Clipboard.setStringAsync(user.referralCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleShareLink = async () => {
    if (!referralLink) return;
    try {
      await Share.share({
        message: `Join Cloud District Club and get 1,000 Cloudz points on your first purchase! Use my link: ${referralLink}`,
        url: referralLink,
        title: 'Cloud District Club - Referral',
      });
    } catch (error) {
      // User cancelled or share failed silently
    }
  };

  const handleLogout = () => {
    const doLogout = async () => {
      await logout();
      clearCart();
      router.replace('/auth/login');
    };

    if (Platform.OS === 'web') {
      if (confirm('Are you sure you want to logout?')) {
        doLogout();
      }
    } else {
      Alert.alert('Logout', 'Are you sure you want to logout?', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Logout', style: 'destructive', onPress: doLogout },
      ]);
    }
  };

  const userPoints = user?.loyaltyPoints || 0;
  const tierColor = highestTier ? TIER_ACCENT[highestTier.id] || theme.colors.primary : theme.colors.textMuted;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Account</Text>
        <TouchableOpacity onPress={() => router.push('/profile')} data-testid="edit-profile-btn">
          <Ionicons name="create-outline" size={22} color={theme.colors.primary} />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Profile Card */}
        <TouchableOpacity
          style={styles.profileCard}
          onPress={() => router.push('/profile')}
          activeOpacity={0.8}
          data-testid="profile-card"
        >
          {user?.profilePhoto ? (
            <Image source={{ uri: user.profilePhoto }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatar, styles.avatarPlaceholder]}>
              <Text style={styles.avatarText}>
                {user?.firstName?.charAt(0)}{user?.lastName?.charAt(0)}
              </Text>
            </View>
          )}
          <View style={styles.profileInfo}>
            <Text style={styles.profileName}>{user?.firstName} {user?.lastName}</Text>
            <Text style={styles.profileEmail}>{user?.email}</Text>
            {user?.phone ? <Text style={styles.profilePhone}>{user.phone}</Text> : null}
          </View>
          <Ionicons name="chevron-forward" size={20} color="#666" />
        </TouchableOpacity>

        {/* Cloudz Balance + Tier Badge */}
        <TouchableOpacity
          style={styles.loyaltyCard}
          onPress={() => router.push('/cloudz')}
          activeOpacity={0.8}
          data-testid="loyalty-card-link"
        >
          <View style={styles.loyaltyRow}>
            <View style={{ flex: 1 }}>
              <View style={styles.loyaltyHeader}>
                <Ionicons name="star" size={28} color="#fbbf24" />
                <Text style={styles.loyaltyTitle}>Cloudz Points</Text>
              </View>
              <Text style={styles.loyaltyPoints} data-testid="account-points-display">
                {userPoints.toLocaleString()}
              </Text>
            </View>
            {highestTier && (
              <View style={[styles.tierBadge, { borderColor: tierColor }]} data-testid="tier-badge">
                <Ionicons name="diamond" size={18} color={tierColor} />
                <Text style={[styles.tierBadgeText, { color: tierColor }]}>{highestTier.name}</Text>
              </View>
            )}
          </View>
          <View style={styles.loyaltyFooter}>
            <Text style={styles.loyaltySubtext}>
              {highestTier ? `${highestTier.name} Member` : 'Earn points with every purchase'}
            </Text>
            <Ionicons name="chevron-forward" size={18} color="#e0e7ff" />
          </View>
        </TouchableOpacity>

        {/* Streak Bonus Card */}
        {streakInfo && (
          <View style={styles.streakCard} data-testid="streak-card">
            <View style={styles.streakHeader}>
              <Ionicons name="flame" size={24} color="#f97316" />
              <Text style={styles.streakTitle}>Weekly Streak</Text>
              {streakInfo.streak >= 2 && (
                <View style={styles.streakBadge}>
                  <Text style={styles.streakBadgeText}>+{streakInfo.currentBonus}</Text>
                </View>
              )}
            </View>
            <View style={styles.streakBody}>
              <Text style={styles.streakCount} data-testid="streak-count">
                {streakInfo.streak}
              </Text>
              <Text style={styles.streakUnit}>
                {streakInfo.streak === 1 ? 'week' : 'weeks'}
              </Text>
            </View>
            {streakInfo.streak >= 1 ? (
              <Text style={styles.streakFooter} data-testid="streak-footer">
                {streakInfo.streak >= 2
                  ? `Earning +${streakInfo.currentBonus} Cloudz this week`
                  : `Purchase next week for +${streakInfo.nextBonus} Cloudz bonus`}
                {streakInfo.daysUntilExpiry > 0
                  ? ` \u00B7 ${streakInfo.daysUntilExpiry}d left this week`
                  : ' \u00B7 Last day this week!'}
              </Text>
            ) : (
              <Text style={styles.streakFooter} data-testid="streak-footer">
                Make a purchase to start your streak!
              </Text>
            )}
          </View>
        )}

        {/* Menu Items */}
        <View style={styles.section}>
          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => router.push('/cloudz')}
            data-testid="menu-item-cloudz-rewards"
          >
            <View style={styles.menuItemLeft}>
              <Ionicons name="star" size={24} color="#fbbf24" />
              <Text style={[styles.menuItemText, { color: '#fbbf24' }]}>Cloudz Rewards</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => router.push('/cloudz-history')}
            data-testid="menu-item-cloudz-history"
          >
            <View style={styles.menuItemLeft}>
              <Ionicons name="receipt" size={24} color="#a78bfa" />
              <Text style={[styles.menuItemText, { color: '#a78bfa' }]}>Cloudz History</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => router.push('/leaderboard')}
            data-testid="menu-item-leaderboard"
          >
            <View style={styles.menuItemLeft}>
              <Ionicons name="trophy" size={24} color="#f59e0b" />
              <Text style={[styles.menuItemText, { color: '#f59e0b' }]}>Leaderboard</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          {user?.isAdmin && (
            <TouchableOpacity
              style={styles.menuItem}
              onPress={() => router.push('/admin/orders')}
              data-testid="menu-item-admin-dashboard"
            >
              <View style={styles.menuItemLeft}>
                <Ionicons name="shield" size={24} color={theme.colors.primary} />
                <Text style={[styles.menuItemText, { color: theme.colors.primary }]}>Admin Dashboard</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#666" />
            </TouchableOpacity>
          )}
        </View>

        {/* Refer & Earn */}
        {user?.referralCode && (
          <View style={styles.section}>
            <View style={styles.referralCard} data-testid="referral-section">
              <View style={styles.referralHeader}>
                <Ionicons name="people" size={28} color={theme.colors.primary} />
                <Text style={styles.referralTitle}>Refer & Earn</Text>
              </View>

              <Text style={styles.referralDesc}>
                You earn 2,000 Cloudz. Your friend earns 1,000 after their first purchase.
              </Text>

              <View style={styles.referralCodeRow}>
                <Text style={styles.referralCodeLabel}>Your Code</Text>
                <View style={styles.referralCodeBox}>
                  <Text style={styles.referralCodeText} data-testid="referral-code-display">{user.referralCode}</Text>
                  <TouchableOpacity
                    onPress={handleCopyCode}
                    style={styles.copyButton}
                    data-testid="copy-referral-code-btn"
                  >
                    <Ionicons name={copied ? 'checkmark' : 'copy'} size={18} color={copied ? theme.colors.success : '#fff'} />
                    <Text style={[styles.copyButtonText, copied && { color: theme.colors.success }]}>
                      {copied ? 'Copied!' : 'Copy'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* Share Link Preview + Button */}
              <View style={styles.shareLinkPreview} data-testid="share-link-preview">
                <Text style={styles.shareLinkUrl} numberOfLines={1}>{referralLink}</Text>
              </View>
              <TouchableOpacity
                style={styles.shareButton}
                onPress={handleShareLink}
                data-testid="share-referral-link-btn"
              >
                <Ionicons name="share-social" size={20} color="#fff" />
                <Text style={styles.shareButtonText}>Share Referral Link</Text>
              </TouchableOpacity>

              <View style={styles.referralStats}>
                <View style={styles.referralStat}>
                  <Text style={styles.referralStatValue} data-testid="referral-count">{user.referralCount || 0}</Text>
                  <Text style={styles.referralStatLabel}>Referrals</Text>
                </View>
                <View style={styles.referralStatDivider} />
                <View style={styles.referralStat}>
                  <Text style={styles.referralStatValue} data-testid="referral-earnings">{(user.referralRewardsEarned || 0).toLocaleString()}</Text>
                  <Text style={styles.referralStatLabel}>Cloudz Earned</Text>
                </View>
              </View>
            </View>
          </View>
        )}

        {/* Redemption History */}
        {history.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Recent Redemptions</Text>
            {history.map((item) => (
              <View key={item.id} style={styles.historyRow} data-testid={`redemption-${item.id}`}>
                <View style={[styles.historyDot, { backgroundColor: TIER_ACCENT[item.tierId] || '#666' }]} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.historyName}>{item.tierName}</Text>
                  <Text style={styles.historyDate}>
                    {new Date(item.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </Text>
                </View>
                <Text style={styles.historyPoints}>-{item.pointsSpent.toLocaleString()}</Text>
                <View style={[
                  styles.historyStatus,
                  { backgroundColor: item.used ? '#333' : theme.colors.success + '22' }
                ]}>
                  <Text style={[
                    styles.historyStatusText,
                    { color: item.used ? '#666' : theme.colors.success }
                  ]}>
                    {item.used ? 'Used' : 'Active'}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Info Cards */}
        <View style={styles.section}>
          <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>Age Verified</Text>
            <View style={styles.verifiedBadge}>
              <Ionicons name="checkmark-circle" size={16} color={theme.colors.success} />
              <Text style={styles.verifiedText}>21+</Text>
            </View>
          </View>
        </View>

        {/* Logout */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout} data-testid="logout-btn">
          <Ionicons name="log-out" size={20} color={theme.colors.primary} />
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>

        <View style={styles.footer}>
          <Text style={styles.footerText}>Cloud District Club</Text>
          <Text style={styles.footerSubtext}>Local Pickup Only - 21+ Only</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    paddingTop: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    marginBottom: 16,
    gap: 14,
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
  },
  avatarPlaceholder: {
    backgroundColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
  },
  profileInfo: {
    flex: 1,
  },
  profileName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  profileEmail: {
    fontSize: 13,
    color: theme.colors.textMuted,
    marginTop: 2,
  },
  profilePhone: {
    fontSize: 13,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  loyaltyCard: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.borderRadius.lg,
    padding: 20,
    marginBottom: 16,
  },
  loyaltyRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  loyaltyHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  loyaltyTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#e0e7ff',
  },
  loyaltyPoints: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#fff',
  },
  tierBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderWidth: 1.5,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: 'rgba(0,0,0,0.25)',
  },
  tierBadgeText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  loyaltyFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  loyaltySubtext: {
    fontSize: 13,
    color: '#e0e7ff',
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 10,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: theme.colors.card,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
    marginBottom: 8,
  },
  menuItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  menuItemText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '500',
  },
  historyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.md,
    padding: 12,
    marginBottom: 6,
    gap: 10,
  },
  historyDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  historyName: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
  },
  historyDate: {
    color: '#666',
    fontSize: 11,
    marginTop: 1,
  },
  historyPoints: {
    color: theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '600',
  },
  historyStatus: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  historyStatusText: {
    fontSize: 11,
    fontWeight: '600',
  },
  infoCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 14,
    color: theme.colors.textMuted,
  },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  verifiedText: {
    fontSize: 14,
    color: theme.colors.success,
    fontWeight: '600',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: theme.colors.card,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
    borderWidth: 1,
    borderColor: theme.colors.primary,
  },
  logoutText: {
    fontSize: 16,
    color: theme.colors.primary,
    fontWeight: '600',
  },
  footer: {
    alignItems: 'center',
    marginTop: 32,
    marginBottom: 16,
  },
  footerText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  footerSubtext: {
    fontSize: 12,
    color: '#444',
    marginTop: 4,
  },
  referralCard: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 20,
    borderWidth: 1,
    borderColor: '#222',
  },
  referralHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 10,
  },
  referralTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  referralDesc: {
    fontSize: 13,
    color: theme.colors.textMuted,
    lineHeight: 18,
    marginBottom: 16,
  },
  referralCodeRow: {
    marginBottom: 16,
  },
  referralCodeLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 6,
  },
  referralCodeBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(46,107,255,0.1)',
    borderWidth: 1,
    borderColor: theme.colors.primary + '44',
    borderRadius: 10,
    paddingLeft: 16,
    overflow: 'hidden',
  },
  referralCodeText: {
    flex: 1,
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
    letterSpacing: 3,
    paddingVertical: 12,
  },
  copyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: theme.colors.primary,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  copyButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#fff',
  },
  referralStats: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  referralStat: {
    flex: 1,
    alignItems: 'center',
  },
  referralStatDivider: {
    width: 1,
    height: 32,
    backgroundColor: '#333',
  },
  referralStatValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  referralStatLabel: {
    fontSize: 12,
    color: theme.colors.textMuted,
    marginTop: 2,
  },
  shareLinkPreview: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  },
  shareLinkUrl: {
    fontSize: 12,
    color: theme.colors.textMuted,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  shareButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: theme.colors.primary,
    borderRadius: 10,
    paddingVertical: 14,
    marginBottom: 16,
  },
  shareButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
});
