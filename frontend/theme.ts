export const theme = {
  colors: {
    background: '#0C0C0C',
    card: '#151515',
    cardBorder: '#222222',
    
    primary: '#2E6BFF',
    primaryGradientStart: '#2E6BFF',
    primaryGradientEnd: '#7A4DFF',
    
    success: '#1BC47D',
    danger: '#FF3B3B',
    warning: '#FBBF24',
    
    text: '#FFFFFF',
    textMuted: '#A0A0A0',
    textSecondary: '#666666',
    
    tabActive: '#2E6BFF',
    tabInactive: '#666666',
    
    inputBackground: '#1A1A1A',
    inputBorder: '#333333',
  },
  
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  
  borderRadius: {
    sm: 8,
    md: 12,
    lg: 18,
    xl: 24,
    full: 9999,
  },
  
  gradients: {
    primary: ['#2E6BFF', '#7A4DFF'],
  },
};

export type Theme = typeof theme;
