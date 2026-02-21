import { View, Text, StyleSheet, TouchableOpacity, TextInput, FlatList, Modal, Platform, KeyboardAvoidingView, Animated } from 'react-native';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../store/authStore';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Message {
  chatId: string;
  senderId: string;
  senderName: string;
  isAdmin: boolean;
  message: string;
  createdAt: string;
  readAt?: string;
  type?: string;
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

export default function ChatBubble() {
  const user = useAuthStore(state => state.user);
  const token = useAuthStore(state => state.token);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [remoteTyping, setRemoteTyping] = useState(false);
  const [allRead, setAllRead] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTypingSentRef = useRef(0);

  const chatId = user ? `chat_${user.id}` : '';

  const loadHistory = useCallback(async () => {
    if (!chatId || !token) return;
    try {
      const res = await axios.get(`${API_URL}/api/chat/messages/${chatId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setMessages(res.data);
    } catch (e) {
      console.error('Load chat history:', e);
    }
  }, [chatId, token]);

  const connectWS = useCallback(() => {
    if (!chatId || !token) return;
    const wsUrl = API_URL?.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/api/ws/chat/${chatId}?token=${token}`);
    ws.onopen = () => {
      // Send read receipt when chat opens
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
        // Auto-send read receipt for incoming messages
        if (data.senderId !== user?.id) {
          ws.send(JSON.stringify({ type: 'read' }));
        }
      } catch {}
    };
    ws.onclose = () => {
      setTimeout(() => { if (open) connectWS(); }, 3000);
    };
    wsRef.current = ws;
  }, [chatId, token, open, user?.id]);

  useEffect(() => {
    if (open && chatId) {
      loadHistory();
      connectWS();
    }
    return () => { wsRef.current?.close(); };
  }, [open, chatId]);

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

  if (!user) return null;

  const lastMyMsg = [...messages].reverse().find(m => m.senderId === user.id);

  const renderMessage = ({ item, index }: { item: Message; index: number }) => {
    const isMe = item.senderId === user.id;
    const isLastMyMsg = isMe && item === lastMyMsg;
    return (
      <View style={[styles.msgRow, isMe ? styles.msgRowRight : styles.msgRowLeft]}>
        <View style={[styles.msgBubble, isMe ? styles.myBubble : styles.otherBubble]}>
          {!isMe && <Text style={styles.msgSender}>{item.senderName}</Text>}
          <Text style={[styles.msgText, isMe && styles.myMsgText]}>{item.message}</Text>
          <View style={styles.msgMeta}>
            <Text style={[styles.msgTime, isMe && styles.myMsgTime]}>
              {new Date(item.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </Text>
            {isLastMyMsg && (
              <Ionicons
                name={allRead ? 'checkmark-done' : 'checkmark'}
                size={14}
                color={allRead ? '#60a5fa' : 'rgba(255,255,255,0.5)'}
                style={{ marginLeft: 4 }}
              />
            )}
          </View>
        </View>
      </View>
    );
  };

  return (
    <>
      <TouchableOpacity
        style={styles.fab}
        onPress={() => setOpen(true)}
        activeOpacity={0.85}
        data-testid="chat-fab"
      >
        <Ionicons name="chatbubbles" size={24} color="#fff" />
      </TouchableOpacity>

      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <KeyboardAvoidingView
          style={styles.modalWrap}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={styles.chatContainer}>
            <View style={styles.chatHeader}>
              <Text style={styles.chatTitle}>Support Chat</Text>
              <TouchableOpacity onPress={() => setOpen(false)} data-testid="chat-close-btn">
                <Ionicons name="close" size={24} color="#999" />
              </TouchableOpacity>
            </View>

            {messages.length === 0 && !remoteTyping ? (
              <View style={styles.emptyWrap}>
                <Ionicons name="chatbubble-ellipses-outline" size={48} color="#333" />
                <Text style={styles.emptyText}>How can we help you?</Text>
                <Text style={styles.emptySubtext}>Send a message and our team will respond shortly.</Text>
              </View>
            ) : (
              <FlatList
                ref={flatListRef}
                data={messages}
                renderItem={renderMessage}
                keyExtractor={(_, i) => String(i)}
                style={styles.messageList}
                contentContainerStyle={styles.messageListContent}
                onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
                ListFooterComponent={remoteTyping ? <TypingDots /> : null}
              />
            )}

            <View style={styles.inputRow}>
              <TextInput
                style={styles.input}
                placeholder="Type a message..."
                placeholderTextColor="#666"
                value={input}
                onChangeText={handleTextChange}
                onSubmitEditing={sendMessage}
                returnKeyType="send"
                data-testid="chat-input"
              />
              <TouchableOpacity
                style={[styles.sendBtn, !input.trim() && styles.sendBtnDisabled]}
                onPress={sendMessage}
                disabled={!input.trim()}
                data-testid="chat-send-btn"
              >
                <Ionicons name="send" size={20} color={input.trim() ? '#fff' : '#555'} />
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: 'absolute',
    bottom: 80,
    right: 16,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2E6BFF',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
    ...Platform.select({
      web: { boxShadow: '0 4px 12px rgba(46,107,255,0.4)' },
      default: { elevation: 8 },
    }),
  },
  modalWrap: { flex: 1, justifyContent: 'flex-end' },
  chatContainer: { height: '85%', backgroundColor: '#111', borderTopLeftRadius: 20, borderTopRightRadius: 20, overflow: 'hidden' },
  chatHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: '#222' },
  chatTitle: { color: '#fff', fontSize: 17, fontWeight: '700' },
  emptyWrap: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 12 },
  emptyText: { color: '#aaa', fontSize: 16, fontWeight: '600' },
  emptySubtext: { color: '#666', fontSize: 13, textAlign: 'center' },
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
  msgMeta: { flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', marginTop: 4 },
  msgTime: { color: '#666', fontSize: 10 },
  myMsgTime: { color: 'rgba(255,255,255,0.6)' },
  inputRow: { flexDirection: 'row', alignItems: 'center', padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: '#222', backgroundColor: '#0c0c0c' },
  input: { flex: 1, backgroundColor: '#1a1a1a', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, color: '#fff', fontSize: 14 },
  sendBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#2E6BFF', alignItems: 'center', justifyContent: 'center' },
  sendBtnDisabled: { backgroundColor: '#1a1a1a' },
  typingRow: { flexDirection: 'row', justifyContent: 'flex-start', marginBottom: 4, marginTop: 4 },
  typingBubble: { flexDirection: 'row', gap: 4, backgroundColor: '#1e1e1e', paddingHorizontal: 14, paddingVertical: 10, borderRadius: 16, borderBottomLeftRadius: 4 },
  typingDot: { width: 7, height: 7, borderRadius: 3.5, backgroundColor: '#666' },
});
