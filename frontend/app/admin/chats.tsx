import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, FlatList, Platform, KeyboardAvoidingView, Animated } from 'react-native';
import { useState, useEffect, useRef, useCallback } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../store/authStore';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface ChatSession {
  chatId: string;
  userId: string;
  userName: string;
  lastMessage: string;
  lastMessageAt: string;
  online: boolean;
}

interface Message {
  chatId: string;
  senderId: string;
  senderName: string;
  isAdmin: boolean;
  message: string;
  createdAt: string;
  readAt?: string;
}

const TypingDots = () => {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const animate = (dot: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(dot, { toValue: 1, duration: 300, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0, duration: 300, useNativeDriver: true }),
          Animated.delay(600 - delay),
        ])
      );
    animate(dot1, 0).start();
    animate(dot2, 200).start();
    animate(dot3, 400).start();
  }, []);
  return (
    <View style={styles.typingRow}>
      <View style={styles.typingBubble}>
        {[dot1, dot2, dot3].map((dot, i) => (
          <Animated.View
            key={i}
            style={[styles.typingDot, { opacity: dot, transform: [{ translateY: dot.interpolate({ inputRange: [0, 1], outputRange: [0, -4] }) }] }]}
          />
        ))}
      </View>
    </View>
  );
};

export default function AdminChats() {
  const token = useAuthStore(state => state.token);
  const user = useAuthStore(state => state.user);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedChat, setSelectedChat] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [remoteTyping, setRemoteTyping] = useState(false);
  const [allRead, setAllRead] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTypingSentRef = useRef(0);

  const loadSessions = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/api/admin/chats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSessions(res.data);
    } catch (e) {
      console.error('Failed to load chat sessions:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadSessions();
    pollRef.current = setInterval(loadSessions, 10000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [loadSessions]);

  const openChat = useCallback(async (chatId: string) => {
    setSelectedChat(chatId);
    setRemoteTyping(false);
    setAllRead(false);
    try {
      const res = await axios.get(`${API_URL}/api/chat/messages/${chatId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setMessages(res.data);
    } catch (e) {
      console.error('Failed to load messages:', e);
    }

    // Connect WebSocket
    wsRef.current?.close();
    const wsUrl = API_URL?.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/api/ws/chat/${chatId}?token=${token}`);
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'read' }));
    };
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'typing') {
          if (data.senderId !== user?.id) {
            setRemoteTyping(data.isTyping);
            if (data.isTyping) {
              if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
              typingTimerRef.current = setTimeout(() => setRemoteTyping(false), 3000);
            }
          }
          return;
        }
        if (data.type === 'read') {
          if (data.readBy !== user?.id) {
            setAllRead(true);
          }
          return;
        }
        // Regular message
        setMessages(prev => [...prev, data]);
        setRemoteTyping(false);
        if (data.senderId !== user?.id) {
          ws.send(JSON.stringify({ type: 'read' }));
        }
      } catch {}
    };
    wsRef.current = ws;
  }, [token, user?.id]);

  const emitTyping = (isTyping: boolean) => {
    const now = Date.now();
    if (isTyping && now - lastTypingSentRef.current < 2000) return;
    lastTypingSentRef.current = now;
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'typing', isTyping }));
    }
  };

  const handleTextChange = (text: string) => {
    setInput(text);
    emitTyping(text.length > 0);
  };

  const sendMessage = () => {
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: 'message', message: text }));
    setInput('');
    setAllRead(false);
    emitTyping(false);
  };

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages.length]);

  useEffect(() => {
    return () => { wsRef.current?.close(); };
  }, []);

  if (selectedChat) {
    const session = sessions.find(s => s.chatId === selectedChat);
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.chatHeader}>
          <TouchableOpacity onPress={() => { setSelectedChat(null); wsRef.current?.close(); }} data-testid="admin-chat-back">
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <View style={styles.chatHeaderInfo}>
            <Text style={styles.chatHeaderName}>{session?.userName || 'User'}</Text>
            <View style={styles.onlineRow}>
              <View style={[styles.onlineDot, session?.online && styles.onlineDotActive]} />
              <Text style={styles.onlineLabel}>{session?.online ? 'Online' : 'Offline'}</Text>
            </View>
          </View>
        </View>

        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <FlatList
            ref={flatListRef}
            data={messages}
            renderItem={({ item }) => {
              const isMe = item.isAdmin;
              return (
                <View style={[styles.msgRow, isMe ? styles.msgRowRight : styles.msgRowLeft]}>
                  <View style={[styles.msgBubble, isMe ? styles.myBubble : styles.otherBubble]}>
                    {!isMe && <Text style={styles.msgSender}>{item.senderName}</Text>}
                    <Text style={[styles.msgText, isMe && styles.myMsgText]}>{item.message}</Text>
                    <Text style={[styles.msgTime, isMe && styles.myMsgTime]}>
                      {new Date(item.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </Text>
                  </View>
                </View>
              );
            }}
            keyExtractor={(_, i) => String(i)}
            style={styles.messageList}
            contentContainerStyle={styles.messageListContent}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
          />

          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              placeholder="Reply..."
              placeholderTextColor="#666"
              value={input}
              onChangeText={setInput}
              onSubmitEditing={sendMessage}
              returnKeyType="send"
              data-testid="admin-chat-input"
            />
            <TouchableOpacity
              style={[styles.sendBtn, !input.trim() && styles.sendBtnDisabled]}
              onPress={sendMessage}
              disabled={!input.trim()}
              data-testid="admin-chat-send"
            >
              <Ionicons name="send" size={20} color={input.trim() ? '#fff' : '#555'} />
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Live Chats</Text>
        <TouchableOpacity onPress={loadSessions} data-testid="admin-chats-refresh">
          <Ionicons name="refresh" size={22} color="#888" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.emptyWrap}><Text style={styles.emptyText}>Loading...</Text></View>
      ) : sessions.length === 0 ? (
        <View style={styles.emptyWrap}>
          <Ionicons name="chatbubbles-outline" size={48} color="#333" />
          <Text style={styles.emptyText}>No active chats</Text>
          <Text style={styles.emptySubtext}>Customer messages will appear here.</Text>
        </View>
      ) : (
        <ScrollView>
          {sessions.map((session) => (
            <TouchableOpacity
              key={session.chatId}
              style={styles.sessionCard}
              onPress={() => openChat(session.chatId)}
              data-testid={`admin-chat-session-${session.chatId}`}
            >
              <View style={styles.sessionLeft}>
                <View style={styles.avatarWrap}>
                  <Text style={styles.avatarText}>{(session.userName || '?')[0].toUpperCase()}</Text>
                  {session.online && <View style={styles.avatarOnline} />}
                </View>
                <View style={styles.sessionInfo}>
                  <Text style={styles.sessionName}>{session.userName}</Text>
                  <Text style={styles.sessionPreview} numberOfLines={1}>{session.lastMessage}</Text>
                </View>
              </View>
              <Text style={styles.sessionTime}>
                {session.lastMessageAt ? new Date(session.lastMessageAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0c0c0c' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16 },
  title: { color: '#fff', fontSize: 22, fontWeight: '700' },
  emptyWrap: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  emptyText: { color: '#aaa', fontSize: 16, fontWeight: '600' },
  emptySubtext: { color: '#666', fontSize: 13 },
  sessionCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },
  sessionLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  avatarWrap: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#1e1e1e', alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: '#fff', fontSize: 18, fontWeight: '700' },
  avatarOnline: { position: 'absolute', bottom: 0, right: 0, width: 12, height: 12, borderRadius: 6, backgroundColor: '#22c55e', borderWidth: 2, borderColor: '#0c0c0c' },
  sessionInfo: { flex: 1 },
  sessionName: { color: '#fff', fontSize: 15, fontWeight: '600' },
  sessionPreview: { color: '#888', fontSize: 13, marginTop: 2 },
  sessionTime: { color: '#666', fontSize: 11 },
  chatHeader: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 12, borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },
  chatHeaderInfo: { flex: 1 },
  chatHeaderName: { color: '#fff', fontSize: 17, fontWeight: '700' },
  onlineRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 },
  onlineDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#555' },
  onlineDotActive: { backgroundColor: '#22c55e' },
  onlineLabel: { color: '#888', fontSize: 12 },
  messageList: { flex: 1 },
  messageListContent: { padding: 16, gap: 8 },
  msgRow: { flexDirection: 'row', marginBottom: 4 },
  msgRowRight: { justifyContent: 'flex-end' },
  msgRowLeft: { justifyContent: 'flex-start' },
  msgBubble: { maxWidth: '78%', padding: 10, paddingBottom: 6, borderRadius: 16 },
  myBubble: { backgroundColor: '#2E6BFF', borderBottomRightRadius: 4 },
  otherBubble: { backgroundColor: '#1e1e1e', borderBottomLeftRadius: 4 },
  msgSender: { color: '#2E6BFF', fontSize: 11, fontWeight: '700', marginBottom: 2 },
  msgText: { color: '#ddd', fontSize: 14, lineHeight: 20 },
  myMsgText: { color: '#fff' },
  msgTime: { color: '#666', fontSize: 10, marginTop: 4, alignSelf: 'flex-end' },
  myMsgTime: { color: 'rgba(255,255,255,0.6)' },
  inputRow: { flexDirection: 'row', alignItems: 'center', padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: '#222', backgroundColor: '#0c0c0c' },
  input: { flex: 1, backgroundColor: '#1a1a1a', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, color: '#fff', fontSize: 14 },
  sendBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#2E6BFF', alignItems: 'center', justifyContent: 'center' },
  sendBtnDisabled: { backgroundColor: '#1a1a1a' },
});
