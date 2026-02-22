import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const TOKEN_KEY = 'cloud-district-token';

// Storage helpers — same pattern as cartStore
function readToken(): string | null {
  if (Platform.OS === 'web') {
    if (typeof window === 'undefined') return null;
    try { return window.localStorage.getItem(TOKEN_KEY); } catch { return null; }
  }
  return null; // native handled async
}

function writeToken(token: string) {
  if (Platform.OS === 'web') {
    if (typeof window === 'undefined') return;
    try { window.localStorage.setItem(TOKEN_KEY, token); } catch {}
    return;
  }
  try { AsyncStorage.setItem(TOKEN_KEY, token); } catch {}
}

function clearToken() {
  if (Platform.OS === 'web') {
    if (typeof window === 'undefined') return;
    try { window.localStorage.removeItem(TOKEN_KEY); } catch {}
    return;
  }
  try { AsyncStorage.removeItem(TOKEN_KEY); } catch {}
}

interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  isAdmin: boolean;
  loyaltyPoints: number;
  phone?: string;
  profilePhoto?: string;
  referralCode?: string;
  referralCount?: number;
  referralRewardsEarned?: number;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, firstName: string, lastName: string, dateOfBirth: string, referralCode?: string) => Promise<void>;
  logout: () => Promise<void>;
  loadToken: () => Promise<void>;
  refreshUser: () => Promise<void>;
  registerPushToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email: string, password: string) => {
    const response = await axios.post(`${API_URL}/api/auth/login`, { email, password });
    const { access_token, user } = response.data;
    writeToken(access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    set({ user, token: access_token, isAuthenticated: true });
    get().registerPushToken();
  },

  register: async (email: string, password: string, firstName: string, lastName: string, dateOfBirth: string, referralCode?: string) => {
    const response = await axios.post(`${API_URL}/api/auth/register`, {
      email, password, firstName, lastName, dateOfBirth,
      referralCode: referralCode || undefined,
    });
    const { access_token, user } = response.data;
    writeToken(access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    set({ user, token: access_token, isAuthenticated: true });
    get().registerPushToken();
  },

  logout: async () => {
    clearToken();
    delete axios.defaults.headers.common['Authorization'];
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadToken: async () => {
    try {
      let token: string | null = null;
      if (Platform.OS === 'web') {
        token = readToken();
      } else {
        token = await AsyncStorage.getItem(TOKEN_KEY);
      }
      if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        const response = await axios.get(`${API_URL}/api/auth/me`);
        set({ user: response.data, token, isAuthenticated: true, isLoading: false });
        get().registerPushToken();
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      clearToken();
      set({ isLoading: false });
    }
  },

  refreshUser: async () => {
    try {
      const response = await axios.get(`${API_URL}/api/auth/me`);
      set({ user: response.data });
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  },

  registerPushToken: async () => {
    if (Platform.OS === 'web') return;
    try {
      const { status: existing } = await Notifications.getPermissionsAsync();
      let finalStatus = existing;
      if (existing !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }
      if (finalStatus !== 'granted') return;
      const tokenData = await Notifications.getExpoPushTokenAsync();
      const pushToken = tokenData.data;
      if (pushToken) {
        await axios.post(`${API_URL}/api/push/register`, { token: pushToken });
      }
    } catch (error) {
      console.log('Push token registration skipped:', error);
    }
  },
}));
