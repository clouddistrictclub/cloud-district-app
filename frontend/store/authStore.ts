import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

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
    await AsyncStorage.setItem('token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    set({ user, token: access_token, isAuthenticated: true });
  },

  register: async (email: string, password: string, firstName: string, lastName: string, dateOfBirth: string, referralCode?: string) => {
    const response = await axios.post(`${API_URL}/api/auth/register`, {
      email,
      password,
      firstName,
      lastName,
      dateOfBirth,
      referralCode: referralCode || undefined,
    });
    const { access_token, user } = response.data;
    await AsyncStorage.setItem('token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    set({ user, token: access_token, isAuthenticated: true });
  },

  logout: async () => {
    await AsyncStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadToken: async () => {
    try {
      const token = await AsyncStorage.getItem('token');
      if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        const response = await axios.get(`${API_URL}/api/auth/me`);
        set({ user: response.data, token, isAuthenticated: true, isLoading: false });
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      await AsyncStorage.removeItem('token');
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
  }
}));