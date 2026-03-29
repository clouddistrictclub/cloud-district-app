import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../store/authStore';
import { Ionicons } from '@expo/vector-icons';
import { formatLedgerType, getLedgerIcon, getLedgerColor } from '../constants/ledger';
import axios from 'axios';
import { theme } from '../theme';
import { API_URL } from '../constants/api';

interface Tier {
  id: string;
  name: string;
  pointsRequired: number;
  reward: number;
  icon: string;
  unlocked: boolean;
  pointsNeeded: number;
}

interface Reward {
  id: string;
  tierId: string;
  tierName: string;
  rewardAmount: number;
  pointsSpent: number;
  used: boolean;
  createdAt: string;
}

interface LedgerEntry {
  userId: string;
  type: string;
  amount: number;
  balanceAfter: number;
  reference: string;
  createdAt: string;
}

const EARN_ACTIONS = [
  { id: 'order', icon: 'cart', label: 'Place an Order', desc: '3 Cloudz per $1 spent', enabled: true },
  { id: 'signup', icon: 'person-add', label: 'Signup Bonus', desc: '500 Cloudz on registration', enabled: true },
  { id: 'referral', icon: 'people', label: 'Refer a Friend', desc: '1,000 Cloudz per referral', enabled: true },
  { id: 'twitter', icon: 'logo-twitter', label: 'Share on X', desc: 'Coming soon', enabled: false },
  { id: 'facebook', icon: 'logo-facebook', label: 'Share on Facebook', desc: 'Coming soon', enabled: false },
  { id: 'instagram', icon: 'logo-instagram', label: 'Follow on Instagram', desc: 'Coming soon', enabled: false },
];


export default function Cloudz() {
  const router = useRouter();
  const { user, refreshUser, token } = useAuthStore();
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState<string | null>(null);

  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const loadData = useCallback(async () => {
    try {
      const [tiersRes, rewardsRes, ledgerRes] = await Promise.all([
        axios.get(`${API_URL}/api/loyalty/tiers`, authHeaders),
        axios.get(`${API_URL}/api/loyalty/rewards`, authHeaders),
        axios.get(`${API_URL}/api/loyalty/ledger`, authHeaders),
      ]);
      setTiers(Array.isArray(tiersRes.data?.tiers) ? tiersRes.data.tiers : []);
      setRewards(Array.isArray(rewardsRes.data) ? rewardsRes.data : []);
      setLedger(Array.isArray(ledgerRes.data) ? ledgerRes.data : []);
    } catch (error) {
      console.error('Failed to load loyalty data:', error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRedeem = (tier: Tier) => {
    if (!tier.unlocked) return;

    const hasActive = rewards.some(r => r.tierId === tier.id);
    if (hasActive) {
      Alert.alert('Already Redeemed', 'You have an active reward for this tier. Use it at checkout first.');
      return;
    }

    Alert.alert(
      `Redeem ${tier.name}`,
      `Spend ${tier.pointsRequired.toLocaleString()} Cloudz for a $${tier.reward.toFixed(2)} reward?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Redeem',
          onPress: async () => {
            setRedeeming(tier.id);
            try {
              await axios.post(`${API_URL}/api/loyalty/redeem`, { tierId: tier.id }, authHeaders);
              await refreshUser();
              await loadData();
              Alert.alert('Redeemed!', `$${tier.reward.toFixed(2)} reward is ready to use at checkout.`);
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to redeem');
            } finally {
              setRedeeming(null);
            }
          },
        },
      ]
    );
  };

  const userPoints = user?.loyaltyPoints || 0;
  const nextTier = tiers.find(t => !t.unlocked);

  if (loading) {
    return (
      <SafeAreaView style={s.container} edges={['top']}>
        <View style={s.loadingWrap}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.container} edges={['top']}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn} data-testid="cloudz-back-btn">
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={s.headerTitle}>Cloudz Rewards</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView style={s.scroll} showsVerticalScrollIndicator={false}>

        {/* ═══ BALANCE PANEL ═══ */}
        <View style={s.balancePanel} data-testid="cloudz-balance-card">
          <View style={s.balanceGlow} />
          <View style={s.balanceIconRow}>
            <View style={s.balanceIconCircle}>
              <Ionicons name="star" size={22} color="#000" />
            </View>
          </View>
          <Text style={s.balanceLabel}>Your Cloudz Balance</Text>
          <Text style={s.balanceValue} data-testid="cloudz-points-balance">
            {userPoints.toLocaleString()}
          </Text>
          {nextTier ? (
            <View style={s.thresholdRow}>
              <View style={s.progressTrack}>
                <View style={[s.progressFill, { width: `${Math.min(100, (userPoints / nextTier.pointsRequired) * 100)}%` }]} />
              </View>
              <Text style={s.thresholdText}>
                {nextTier.pointsRequired.toLocaleString()} Cloudz  {'->'} ${nextTier.reward.toFixed(2)} reward
              </Text>
            </View>
          ) : (
            <Text style={s.thresholdText}>All reward tiers unlocked</Text>
          )}

          {/* Active rewards badges */}
          {rewards.length > 0 && (
            <View style={s.activeRewardStrip}>
              {rewards.map(r => (
                <View key={r.id} style={s.activeRewardChip} data-testid={`active-reward-${r.tierId}`}>
                  <Ionicons name="checkmark-circle" size={14} color={theme.colors.success} />
                  <Text style={s.activeRewardChipText}>${r.rewardAmount.toFixed(2)} ready</Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {/* ═══ SECTION 1: WAYS TO EARN ═══ */}
        <View style={s.section} data-testid="ways-to-earn-section">
          <Text style={s.sectionTitle}>Ways to Earn</Text>
          <Text style={s.sectionSub}>Stack up Cloudz with every action</Text>
          <View style={s.earnGrid}>
            {EARN_ACTIONS.map(action => (
              <View
                key={action.id}
                style={[s.earnCard, !action.enabled && s.earnCardDisabled]}
                data-testid={`earn-action-${action.id}`}
              >
                <View style={[s.earnIconCircle, !action.enabled && s.earnIconDisabled]}>
                  <Ionicons
                    name={action.icon as any}
                    size={20}
                    color={action.enabled ? '#fff' : '#555'}
                  />
                </View>
                <Text style={[s.earnLabel, !action.enabled && { color: '#444' }]}>{action.label}</Text>
                <Text style={[s.earnDesc, !action.enabled && { color: '#333' }]}>{action.desc}</Text>
                {!action.enabled && (
                  <View style={s.comingSoonBadge}>
                    <Ionicons name="lock-closed" size={10} color="#555" />
                    <Text style={s.comingSoonText}>Soon</Text>
                  </View>
                )}
              </View>
            ))}
          </View>
        </View>

        {/* ═══ SECTION 2: WAYS TO REDEEM ═══ */}
        <View style={s.section} data-testid="ways-to-redeem-section">
          <Text style={s.sectionTitle}>Ways to Redeem</Text>
          <Text style={s.sectionSub}>Turn your Cloudz into real savings</Text>

          {tiers.map(tier => {
            const hasActive = rewards.some(r => r.tierId === tier.id);
            const isRedeeming = redeeming === tier.id;
            const pct = tier.unlocked ? 100 : Math.min(100, (userPoints / tier.pointsRequired) * 100);

            return (
              <View
                key={tier.id}
                style={[s.redeemCard, tier.unlocked && s.redeemCardUnlocked]}
                data-testid={`tier-card-${tier.id}`}
              >
                <View style={s.redeemTop}>
                  <View style={s.redeemRewardBadge}>
                    <Text style={s.redeemRewardAmount}>${tier.reward.toFixed(2)}</Text>
                    <Text style={s.redeemRewardLabel}>reward</Text>
                  </View>
                  <View style={s.redeemInfo}>
                    <Text style={[s.redeemTierName, !tier.unlocked && { color: '#555' }]}>
                      {tier.name}
                    </Text>
                    <Text style={s.redeemPoints}>
                      {tier.pointsRequired.toLocaleString()} Cloudz
                    </Text>
                  </View>
                </View>

                {/* Mini progress */}
                {!tier.unlocked && (
                  <View style={s.redeemProgress}>
                    <View style={s.redeemProgressTrack}>
                      <View style={[s.redeemProgressFill, { width: `${pct}%` }]} />
                    </View>
                    <Text style={s.redeemProgressText}>
                      {tier.pointsNeeded.toLocaleString()} more needed
                    </Text>
                  </View>
                )}

                {tier.unlocked && !hasActive && (
                  <TouchableOpacity
                    style={s.redeemBtn}
                    onPress={() => handleRedeem(tier)}
                    disabled={isRedeeming}
                    data-testid={`redeem-btn-${tier.id}`}
                  >
                    {isRedeeming ? (
                      <ActivityIndicator size="small" color="#000" />
                    ) : (
                      <Text style={s.redeemBtnText}>Redeem</Text>
                    )}
                  </TouchableOpacity>
                )}

                {tier.unlocked && hasActive && (
                  <View style={s.redeemActiveBar}>
                    <Ionicons name="checkmark-circle" size={14} color={theme.colors.success} />
                    <Text style={s.redeemActiveText}>Active — use at checkout</Text>
                  </View>
                )}
              </View>
            );
          })}
        </View>

        {/* ═══ SECTION 3: YOUR ACTIVITY ═══ */}
        <View style={s.section} data-testid="activity-section">
          <View style={s.activityHeader}>
            <View>
              <Text style={s.sectionTitle}>Your Activity</Text>
              <Text style={s.sectionSub}>Points earned and redeemed</Text>
            </View>
            {ledger.length > 5 && (
              <TouchableOpacity onPress={() => router.push('/cloudz-history')} data-testid="view-all-activity-btn">
                <Text style={s.viewAllLink}>View All</Text>
              </TouchableOpacity>
            )}
          </View>

          {ledger.length === 0 ? (
            <View style={s.emptyActivity} data-testid="empty-activity">
              <Ionicons name="receipt-outline" size={36} color="#333" />
              <Text style={s.emptyText}>No activity yet</Text>
              <Text style={s.emptySubtext}>Place an order to start earning Cloudz</Text>
            </View>
          ) : (
            ledger.slice(0, 5).map((entry, idx) => {
              const icon = getLedgerIcon(entry.type);
              const label = formatLedgerType(entry.type);
              const color = getLedgerColor(entry.type, entry.amount);
              const isPositive = entry.amount > 0;
              const date = new Date(entry.createdAt);

              return (
                <View key={idx} style={s.activityRow} data-testid={`activity-entry-${idx}`}>
                  <View style={[s.activityIcon, { backgroundColor: `${color}18` }]}>
                    <Ionicons name={icon as any} size={16} color={color} />
                  </View>
                  <View style={s.activityContent}>
                    <Text style={s.activityLabel}>{label}</Text>
                    <Text style={s.activityRef} numberOfLines={1}>{entry.reference}</Text>
                    <Text style={s.activityDate}>
                      {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </Text>
                  </View>
                  <View style={s.activityRight}>
                    <Text style={[s.activityAmount, { color }]}>
                      {isPositive ? '+' : ''}{(entry.amount ?? 0).toLocaleString()}
                    </Text>
                    <Text style={s.activityBal}>bal {(entry.balanceAfter ?? 0).toLocaleString()}</Text>
                  </View>
                </View>
              );
            })
          )}
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  loadingWrap: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16 },
  backBtn: { width: 40 },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  scroll: { flex: 1, padding: 16 },

  // Balance Panel
  balancePanel: {
    backgroundColor: '#0f1628',
    borderRadius: theme.borderRadius.xl,
    padding: 28,
    alignItems: 'center',
    marginBottom: 28,
    borderWidth: 1,
    borderColor: 'rgba(46,107,255,0.2)',
    overflow: 'hidden',
  },
  balanceGlow: {
    position: 'absolute',
    top: -40,
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: 'rgba(46,107,255,0.08)',
  },
  balanceIconRow: { marginBottom: 8 },
  balanceIconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#fbbf24',
    alignItems: 'center',
    justifyContent: 'center',
  },
  balanceLabel: { fontSize: 13, color: '#8899bb', letterSpacing: 0.5 },
  balanceValue: { fontSize: 52, fontWeight: '800', color: '#fff', marginTop: 2, letterSpacing: -1 },
  thresholdRow: { width: '100%', marginTop: 16, alignItems: 'center' },
  progressTrack: {
    width: '100%',
    height: 5,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressFill: { height: '100%', backgroundColor: theme.colors.primary, borderRadius: 3 },
  thresholdText: { fontSize: 12, color: '#667799' },
  activeRewardStrip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 16,
    justifyContent: 'center',
  },
  activeRewardChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(27,196,125,0.1)',
    borderWidth: 1,
    borderColor: 'rgba(27,196,125,0.25)',
    borderRadius: 20,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  activeRewardChipText: { fontSize: 12, fontWeight: '600', color: theme.colors.success },

  // Section base
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: '#fff' },
  sectionSub: { fontSize: 13, color: '#667', marginTop: 2, marginBottom: 14 },

  // Ways to Earn
  earnGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  earnCard: {
    width: '31%',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.md,
    padding: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.cardBorder,
  },
  earnCardDisabled: { opacity: 0.45 },
  earnIconCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  earnIconDisabled: { backgroundColor: '#222' },
  earnLabel: { fontSize: 11, fontWeight: '600', color: '#ddd', textAlign: 'center' },
  earnDesc: { fontSize: 9, color: '#777', textAlign: 'center', marginTop: 3 },
  comingSoonBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    marginTop: 6,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderRadius: 8,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  comingSoonText: { fontSize: 9, color: '#555' },

  // Ways to Redeem
  redeemCard: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: theme.colors.cardBorder,
  },
  redeemCardUnlocked: { borderColor: 'rgba(46,107,255,0.3)' },
  redeemTop: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  redeemRewardBadge: {
    backgroundColor: theme.colors.primary,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 8,
    alignItems: 'center',
    minWidth: 70,
  },
  redeemRewardAmount: { fontSize: 18, fontWeight: '800', color: '#fff' },
  redeemRewardLabel: { fontSize: 10, color: 'rgba(255,255,255,0.6)', marginTop: 1 },
  redeemInfo: { flex: 1 },
  redeemTierName: { fontSize: 15, fontWeight: '600', color: '#fff' },
  redeemPoints: { fontSize: 12, color: '#778', marginTop: 2 },

  redeemProgress: { marginTop: 12 },
  redeemProgressTrack: {
    height: 4,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 6,
  },
  redeemProgressFill: { height: '100%', backgroundColor: theme.colors.primary, borderRadius: 2 },
  redeemProgressText: { fontSize: 11, color: '#556' },

  redeemBtn: {
    marginTop: 12,
    backgroundColor: theme.colors.primary,
    borderRadius: 10,
    paddingVertical: 11,
    alignItems: 'center',
  },
  redeemBtnText: { fontSize: 14, fontWeight: '700', color: '#fff' },

  redeemActiveBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
  },
  redeemActiveText: { fontSize: 12, color: theme.colors.success },

  // Activity
  activityHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  viewAllLink: { fontSize: 13, color: theme.colors.primary, fontWeight: '600' },

  emptyActivity: {
    alignItems: 'center',
    padding: 32,
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    gap: 6,
  },
  emptyText: { fontSize: 14, fontWeight: '600', color: '#555' },
  emptySubtext: { fontSize: 12, color: '#444' },

  activityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.md,
    padding: 12,
    marginBottom: 6,
    gap: 10,
  },
  activityIcon: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  activityContent: { flex: 1 },
  activityLabel: { fontSize: 13, fontWeight: '600', color: '#ddd' },
  activityRef: { fontSize: 11, color: '#667', marginTop: 1 },
  activityDate: { fontSize: 10, color: '#445', marginTop: 2 },
  activityRight: { alignItems: 'flex-end' },
  activityAmount: { fontSize: 15, fontWeight: '700' },
  activityBal: { fontSize: 10, color: '#445', marginTop: 2 },
});
