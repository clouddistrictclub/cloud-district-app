import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../store/authStore';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { theme } from '../theme';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

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

const TIER_COLORS: Record<string, { bg: string; border: string; accent: string }> = {
  tier_1: { bg: '#1a1510', border: '#CD7F32', accent: '#CD7F32' },
  tier_2: { bg: '#151518', border: '#C0C0C0', accent: '#C0C0C0' },
  tier_3: { bg: '#1a1810', border: '#FFD700', accent: '#FFD700' },
  tier_4: { bg: '#141418', border: '#A8B8D0', accent: '#A8B8D0' },
  tier_5: { bg: '#141620', border: '#B9F2FF', accent: '#B9F2FF' },
};

export default function Cloudz() {
  const router = useRouter();
  const { user, refreshUser } = useAuthStore();
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [history, setHistory] = useState<Reward[]>([]);
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [tiersRes, rewardsRes, historyRes] = await Promise.all([
        axios.get(`${API_URL}/api/loyalty/tiers`),
        axios.get(`${API_URL}/api/loyalty/rewards`),
        axios.get(`${API_URL}/api/loyalty/history`),
      ]);
      setTiers(tiersRes.data.tiers);
      setRewards(rewardsRes.data);
      setHistory(historyRes.data);
    } catch (error) {
      console.error('Failed to load loyalty data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

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
      `Spend ${tier.pointsRequired.toLocaleString()} points for a $${tier.reward.toFixed(2)} reward?\n\nThis will deduct ${tier.pointsRequired.toLocaleString()} Cloudz Points from your balance.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Redeem',
          onPress: async () => {
            setRedeeming(tier.id);
            try {
              await axios.post(`${API_URL}/api/loyalty/redeem`, { tierId: tier.id });
              await refreshUser();
              await loadData();
              Alert.alert('Redeemed!', `You now have a $${tier.reward.toFixed(2)} reward ready to use at checkout.`);
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

  // Find the next tier to work towards
  const nextTier = tiers.find(t => !t.unlocked);
  const progressPercent = nextTier
    ? Math.min(100, (userPoints / nextTier.pointsRequired) * 100)
    : 100;

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton} data-testid="cloudz-back-btn">
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Cloudz Rewards</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Points Balance Card */}
        <View style={styles.balanceCard} data-testid="cloudz-balance-card">
          <Ionicons name="star" size={36} color="#fbbf24" />
          <Text style={styles.balanceLabel}>Your Cloudz Points</Text>
          <Text style={styles.balanceValue} data-testid="cloudz-points-balance">{userPoints.toLocaleString()}</Text>
          {nextTier && (
            <View style={styles.progressSection}>
              <Text style={styles.progressLabel}>
                {nextTier.pointsNeeded.toLocaleString()} pts to {nextTier.name}
              </Text>
              <View style={styles.progressBarBg}>
                <View style={[styles.progressBarFill, { width: `${progressPercent}%` }]} />
              </View>
            </View>
          )}
          {!nextTier && (
            <Text style={styles.maxTierText}>All tiers unlocked!</Text>
          )}
        </View>

        {/* Active Rewards */}
        {rewards.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Active Rewards</Text>
            <Text style={styles.sectionSubtitle}>Use at checkout</Text>
            {rewards.map((reward) => (
              <View key={reward.id} style={styles.activeRewardCard} data-testid={`active-reward-${reward.tierId}`}>
                <View style={styles.rewardBadge}>
                  <Text style={styles.rewardBadgeText}>${reward.rewardAmount.toFixed(2)}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rewardName}>{reward.tierName}</Text>
                  <Text style={styles.rewardDesc}>Ready to use at checkout</Text>
                </View>
                <Ionicons name="checkmark-circle" size={24} color={theme.colors.success} />
              </View>
            ))}
          </View>
        )}

        {/* Tiers */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Reward Tiers</Text>
          <Text style={styles.sectionSubtitle}>Redeem points for discounts</Text>

          {tiers.map((tier) => {
            const colors = TIER_COLORS[tier.id] || TIER_COLORS.tier_1;
            const hasActiveReward = rewards.some(r => r.tierId === tier.id);
            const isRedeeming = redeeming === tier.id;

            return (
              <View
                key={tier.id}
                style={[
                  styles.tierCard,
                  { backgroundColor: tier.unlocked ? colors.bg : '#0f0f0f', borderColor: tier.unlocked ? colors.border : '#222' },
                ]}
                data-testid={`tier-card-${tier.id}`}
              >
                <View style={styles.tierHeader}>
                  <View style={[styles.tierIconCircle, { borderColor: tier.unlocked ? colors.accent : '#333' }]}>
                    <Ionicons
                      name={(tier.icon as any) || 'cloud'}
                      size={24}
                      color={tier.unlocked ? colors.accent : '#444'}
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.tierName, { color: tier.unlocked ? colors.accent : '#555' }]}>
                      {tier.name}
                    </Text>
                    <Text style={[styles.tierPoints, { color: tier.unlocked ? '#aaa' : '#444' }]}>
                      {tier.pointsRequired.toLocaleString()} points
                    </Text>
                  </View>
                  <View style={styles.tierRewardBadge}>
                    <Text style={[styles.tierRewardText, { color: tier.unlocked ? '#fff' : '#555' }]}>
                      ${tier.reward.toFixed(2)}
                    </Text>
                  </View>
                </View>

                {!tier.unlocked && (
                  <View style={styles.tierLockedBar}>
                    <Ionicons name="lock-closed" size={14} color="#555" />
                    <Text style={styles.tierLockedText}>
                      {tier.pointsNeeded.toLocaleString()} more points needed
                    </Text>
                  </View>
                )}

                {tier.unlocked && !hasActiveReward && (
                  <TouchableOpacity
                    style={[styles.redeemButton, { backgroundColor: colors.accent }]}
                    onPress={() => handleRedeem(tier)}
                    disabled={isRedeeming}
                    data-testid={`redeem-btn-${tier.id}`}
                  >
                    {isRedeeming ? (
                      <ActivityIndicator size="small" color="#000" />
                    ) : (
                      <Text style={styles.redeemButtonText}>Redeem {tier.name}</Text>
                    )}
                  </TouchableOpacity>
                )}

                {tier.unlocked && hasActiveReward && (
                  <View style={styles.alreadyRedeemedBar}>
                    <Ionicons name="checkmark-circle" size={14} color={theme.colors.success} />
                    <Text style={styles.alreadyRedeemedText}>Reward active — use at checkout</Text>
                  </View>
                )}
              </View>
            );
          })}
        </View>

        {/* Redemption History */}
        {history.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>History</Text>
            {history.map((item) => (
              <View key={item.id} style={styles.historyRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.historyName}>{item.tierName}</Text>
                  <Text style={styles.historyDate}>
                    {new Date(item.createdAt).toLocaleDateString()}
                  </Text>
                </View>
                <Text style={styles.historyAmount}>-{item.pointsSpent.toLocaleString()} pts</Text>
                <View style={[styles.historyBadge, { backgroundColor: item.used ? '#333' : theme.colors.success + '22' }]}>
                  <Text style={[styles.historyBadgeText, { color: item.used ? '#666' : theme.colors.success }]}>
                    {item.used ? 'Used' : 'Active'}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}

        <View style={styles.infoCard}>
          <Ionicons name="information-circle" size={20} color={theme.colors.primary} />
          <Text style={styles.infoText}>
            Earn 1 Cloudz Point for every $1 spent. Points are awarded when your order is confirmed as paid.
          </Text>
        </View>

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  backButton: {
    width: 40,
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
  balanceCard: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.borderRadius.lg,
    padding: 24,
    alignItems: 'center',
    marginBottom: 24,
  },
  balanceLabel: {
    fontSize: 14,
    color: '#e0e7ff',
    marginTop: 8,
  },
  balanceValue: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 4,
  },
  progressSection: {
    width: '100%',
    marginTop: 16,
  },
  progressLabel: {
    fontSize: 12,
    color: '#e0e7ff',
    marginBottom: 8,
    textAlign: 'center',
  },
  progressBarBg: {
    height: 6,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#fff',
    borderRadius: 3,
  },
  maxTierText: {
    fontSize: 14,
    color: '#e0e7ff',
    marginTop: 12,
    fontWeight: '600',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  sectionSubtitle: {
    fontSize: 13,
    color: theme.colors.textMuted,
    marginBottom: 12,
  },
  activeRewardCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.success + '15',
    borderWidth: 1,
    borderColor: theme.colors.success + '44',
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    gap: 12,
    marginBottom: 8,
  },
  rewardBadge: {
    backgroundColor: theme.colors.success,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  rewardBadgeText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
  rewardName: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 15,
  },
  rewardDesc: {
    color: theme.colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  tierCard: {
    borderWidth: 1,
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    marginBottom: 12,
  },
  tierHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  tierIconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.3)',
  },
  tierName: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  tierPoints: {
    fontSize: 13,
    marginTop: 2,
  },
  tierRewardBadge: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  tierRewardText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  tierLockedBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#222',
  },
  tierLockedText: {
    fontSize: 12,
    color: '#555',
  },
  redeemButton: {
    marginTop: 12,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  redeemButtonText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#000',
  },
  alreadyRedeemedBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#222',
  },
  alreadyRedeemedText: {
    fontSize: 12,
    color: theme.colors.success,
  },
  historyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.md,
    padding: 14,
    marginBottom: 8,
    gap: 12,
  },
  historyName: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
  },
  historyDate: {
    color: '#666',
    fontSize: 12,
    marginTop: 2,
  },
  historyAmount: {
    color: theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '600',
  },
  historyBadge: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  historyBadgeText: {
    fontSize: 11,
    fontWeight: '600',
  },
  infoCard: {
    flexDirection: 'row',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    gap: 10,
    alignItems: 'flex-start',
  },
  infoText: {
    flex: 1,
    fontSize: 13,
    color: theme.colors.textMuted,
    lineHeight: 18,
  },
});
