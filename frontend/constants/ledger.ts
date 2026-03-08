export const LEDGER_EVENT_TYPES: Record<string, { label: string; category: string }> = {
  purchase_reward: { label: 'Purchase Reward', category: 'reward' },
  referral_reward: { label: 'Referral Reward', category: 'reward' },
  tier_redemption: { label: 'Tier Redemption', category: 'redeem' },
  admin_adjustment: { label: 'Admin Adjustment', category: 'admin' },
};

export const LEDGER_FILTER_TYPES = [
  'all',
  'purchase_reward',
  'referral_reward',
  'tier_redemption',
  'admin_adjustment',
] as const;

export function getLedgerLabel(type: string): string {
  return LEDGER_EVENT_TYPES[type]?.label ?? type;
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
  return entry.type;
}
