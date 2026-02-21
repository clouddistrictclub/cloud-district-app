import { View, Text, StyleSheet, TouchableOpacity, TextInput, FlatList, Modal, Platform, KeyboardAvoidingView, Animated, PanResponder, Dimensions } from 'react-native';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useAuthStore } from '../store/authStore';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const SCREEN = Dimensions.get('window');
const FAB_SIZE = 56;
const TAB_BAR_HEIGHT = 65;
const EDGE_MARGIN = 16;
const MIN_Y = 60;
const MAX_Y = SCREEN.height - TAB_BAR_HEIGHT - FAB_SIZE - 16;

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
  const [unreadCount, setUnreadCount] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const bgWsRef = useRef<WebSocket | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTypingSentRef = useRef(0);
  const openRef = useRef(false);

  const chatId = user ? `chat_${user.id}` : '';

  // Draggable FAB state
  const defaultX = SCREEN.width - FAB_SIZE - EDGE_MARGIN;
  const defaultY = SCREEN.height - TAB_BAR_HEIGHT - FAB_SIZE - 16;
  const pan = useRef(new Animated.ValueXY({ x: defaultX, y: defaultY })).current;
  const lastPos = useRef({ x: defaultX, y: defaultY });
  const isDragging = useRef(false);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dragEnabled = useRef(false);

  const snapToEdge = (x: number, y: number) => {
    const clampedY = Math.max(MIN_Y, Math.min(y, MAX_Y));
    const snapX = x < SCREEN.width / 2 ? EDGE_MARGIN : SCREEN.width - FAB_SIZE - EDGE_MARGIN;
    lastPos.current = { x: snapX, y: clampedY };
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    Animated.spring(pan, {
      toValue: { x: snapX, y: clampedY },
      useNativeDriver: false,
      friction: 7,
      tension: 40,
    }).start();
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => false,
      onMoveShouldSetPanResponder: (_, g) => {
        return dragEnabled.current && (Math.abs(g.dx) > 5 || Math.abs(g.dy) > 5);
      },
      onPanResponderGrant: () => {
        isDragging.current = true;
        pan.setOffset({ x: lastPos.current.x, y: lastPos.current.y });
        pan.setValue({ x: 0, y: 0 });
      },
      onPanResponderMove: Animated.event(
        [null, { dx: pan.x, dy: pan.y }],
        { useNativeDriver: false }
      ),
      onPanResponderRelease: (_, g) => {
        pan.flattenOffset();
        const finalX = lastPos.current.x + g.dx;
        const finalY = lastPos.current.y + g.dy;
        snapToEdge(finalX, finalY);
        isDragging.current = false;
        dragEnabled.current = false;
      },
    })
  ).current;

  const handlePressIn = () => {
    longPressTimer.current = setTimeout(() => {
      dragEnabled.current = true;
    }, 300);
  };

  const handlePressOut = () => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
    if (!isDragging.current) {
      dragEnabled.current = false;
    }
  };

  const handleFabPress = () => {
    if (!isDragging.current && !dragEnabled.current) {
      setOpen(true);
      setUnreadCount(0);
      openRef.current = true;
    }
  };

  // Background WebSocket for unread count
  const connectBgWs = useCallback(() => {
    if (!chatId || !token) return;
    bgWsRef.current?.close();
    const wsUrl = API_URL?.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/api/ws/chat/${chatId}?token=${token}`);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'typing' || data.type === 'read') return;
        if (!openRef.current && data.senderId !== user?.id) {
          setUnreadCount(prev => prev + 1);
        }
      } catch {}
    };
    ws.onclose = () => {
      if (!openRef.current) {
        setTimeout(connectBgWs, 5000);
      }
    };
    bgWsRef.current = ws;
  }, [chatId, token, user?.id]);

  useEffect(() => {
    if (chatId && token && !open) {
      connectBgWs();
    }
    return () => { bgWsRef.current?.close(); };
  }, [chatId, token, open]);

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
    bgWsRef.current?.close();
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
        setMessages(prev => [...prev, data]);
        setRemoteTyping(false);
        if (data.senderId !== user?.id) {
          ws.send(JSON.stringify({ type: 'read' }));
        }
      } catch {}
    };
    ws.onclose = () => {
      setTimeout(() => { if (openRef.current) connectWS(); }, 3000);
    };
    wsRef.current = ws;
  }, [chatId, token, user?.id]);

  useEffect(() => {
    if (open && chatId) {
      loadHistory();
      connectWS();
    }
    return () => { wsRef.current?.close(); };
  }, [open, chatId]);

  const handleClose = () => {
    setOpen(false);
    openRef.current = false;
    wsRef.current?.close();
  };

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

  const renderMessage = ({ item }: { item: Message }) => {
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
      <Animated.View
        style={[styles.fabContainer, { transform: [{ translateX: pan.x }, { translateY: pan.y }] }]}
        {...panResponder.panHandlers}
      >
        <TouchableOpacity
          style={styles.fab}
          onPress={handleFabPress}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          activeOpacity={0.85}
          data-testid="chat-fab"
        >
          <Ionicons name="chatbubbles" size={24} color="#fff" />
          {unreadCount > 0 && (
            <View style={styles.badge} data-testid="chat-unread-badge">
              <Text style={styles.badgeText}>{unreadCount > 99 ? '99+' : unreadCount}</Text>
            </View>
          )}
        </TouchableOpacity>
      </Animated.View>

      <Modal visible={open} animationType="slide" transparent onRequestClose={handleClose}>
        <KeyboardAvoidingView
          style={styles.modalWrap}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={styles.chatContainer}>
            <View style={styles.chatHeader}>
              <Text style={styles.chatTitle}>Support Chat</Text>
              <TouchableOpacity onPress={handleClose} data-testid="chat-close-btn">
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
  fabContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: FAB_SIZE,
    height: FAB_SIZE,
    zIndex: 100,
  },
  fab: {
    width: FAB_SIZE,
    height: FAB_SIZE,
    borderRadius: FAB_SIZE / 2,
    backgroundColor: '#2E6BFF',
    alignItems: 'center',
    justifyContent: 'center',
    ...Platform.select({
      web: { boxShadow: '0 4px 12px rgba(46,107,255,0.4)' },
      default: { elevation: 8 },
    }),
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#FF3B3B',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 5,
    borderWidth: 2,
    borderColor: '#0c0c0c',
  },
  badgeText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
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
