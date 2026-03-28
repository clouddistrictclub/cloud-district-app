export const LEDGER_TYPE_CONFIG: Record<string, { label: string; icon: string; color: string; category: string }> = {
  signup_bonus:            { label: 'Signup Bonus',          icon: 'gift',        color: '#22c55e', category: 'reward' },
  referral_signup_bonus:   { label: 'Referral Signup Bonus', icon: 'people',      color: '#22c55e', category: 'reward' },
  referral_new_user_bonus: { label: 'Referral Bonus',        icon: 'person-add',  color: '#22c55e', category: 'reward' },
  referral_bonus:          { label: 'Referral Bonus',        icon: 'people',      color: '#22c55e', category: 'reward' },
  referral_reward:         { label: 'Referral Reward',       icon: 'people',      color: '#22c55e', category: 'reward' },
  purchase_reward:         { label: 'Purchase Reward',       icon: 'cart',        color: '#22c55e', category: 'reward' },
  tier_redemption:         { label: 'Tier Redemption',       icon: 'diamond',     color: '#ef4444', category: 'redeem' },
  admin_adjustment:        { label: 'Admin Adjustment',      icon: 'shield',      color: '#f59e0b', category: 'admin' },
  streak_bonus:            { label: 'Streak Bonus',          icon: 'flame',       color: '#22c55e', category: 'reward' },
  credit_adjustment:       { label: 'Credit Adjustment',     icon: 'wallet',      color: '#f59e0b', category: 'admin' },
};

export function formatLedgerType(type: string): string {
  const config = LEDGER_TYPE_CONFIG[type];
  if (config) return config.label;
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getLedgerIcon(type: string): string {
  return LEDGER_TYPE_CONFIG[type]?.icon ?? 'ellipse';
}

export function getLedgerColor(type: string, amount?: number): string {
  const config = LEDGER_TYPE_CONFIG[type];
  if (config) return config.color;
  return (amount ?? 0) >= 0 ? '#22c55e' : '#ef4444';
}

export function getLedgerLabel(type: string): string {
  return formatLedgerType(type);
}

export function getLedgerDescription(entry: {
  type: string;
  description?: string;
  reference?: string;
  orderId?: string;
}): string {
  if (entry.description) return entry.description;
  if (entry.reference) return entry.reference;
  const oid = entry.orderId ? `#${entry.orderId}` : '';
  if (entry.type === 'purchase_reward') return `Purchase reward from order ${oid}`.trim();
  if (entry.type === 'referral_reward') return `Referral reward from order ${oid}`.trim();
  if (entry.type === 'tier_redemption') return 'Tier redemption';
  if (entry.type === 'admin_adjustment') return 'Admin adjustment';
  return formatLedgerType(entry.type);
}

export const ADMIN_LEDGER_FILTERS = [
  'all',
  'purchase_reward',
  'referral_signup_bonus',
  'referral_new_user_bonus',
  'referral_reward',
  'signup_bonus',
  'tier_redemption',
  'admin_adjustment',
  'streak_bonus',
] as const;
