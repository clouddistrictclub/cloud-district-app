import { View, Text, StyleSheet, TouchableOpacity, TextInput, FlatList, Modal, Platform, KeyboardAvoidingView } from 'react-native';
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
}

export default function ChatBubble() {
  const user = useAuthStore(state => state.user);
  const token = useAuthStore(state => state.token);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const flatListRef = useRef<FlatList>(null);

  const chatId = user ? `chat_${user.id}` : '';

  const loadHistory = useCallback(async () => {
    if (!chatId || !token) return;
    try {
      const res = await axios.get(`${API_URL}/api/chat/messages/${chatId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setMessages(res.data);
    } catch (e) {
      console.error('Failed to load chat history:', e);
    }
  }, [chatId, token]);

  const connectWS = useCallback(() => {
    if (!chatId || !token) return;
    const wsUrl = API_URL?.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/api/ws/chat/${chatId}?token=${token}`);
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        setMessages(prev => [...prev, msg]);
      } catch {}
    };
    ws.onclose = () => {
      setTimeout(() => {
        if (open) connectWS();
      }, 3000);
    };
    wsRef.current = ws;
  }, [chatId, token, open]);

  useEffect(() => {
    if (open && chatId) {
      loadHistory();
      connectWS();
    }
    return () => { wsRef.current?.close(); };
  }, [open, chatId]);

  const sendMessage = () => {
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ message: text }));
    setInput('');
  };

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages.length]);

  if (!user) return null;

  const renderMessage = ({ item }: { item: Message }) => {
    const isMe = item.senderId === user.id;
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

            {messages.length === 0 ? (
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
              />
            )}

            <View style={styles.inputRow}>
              <TextInput
                style={styles.input}
                placeholder="Type a message..."
                placeholderTextColor="#666"
                value={input}
                onChangeText={setInput}
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
  modalWrap: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  chatContainer: {
    height: '85%',
    backgroundColor: '#111',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    overflow: 'hidden',
  },
  chatHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  chatTitle: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '700',
  },
  emptyWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    gap: 12,
  },
  emptyText: {
    color: '#aaa',
    fontSize: 16,
    fontWeight: '600',
  },
  emptySubtext: {
    color: '#666',
    fontSize: 13,
    textAlign: 'center',
  },
  messageList: {
    flex: 1,
  },
  messageListContent: {
    padding: 16,
    gap: 8,
  },
  msgRow: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  msgRowRight: {
    justifyContent: 'flex-end',
  },
  msgRowLeft: {
    justifyContent: 'flex-start',
  },
  msgBubble: {
    maxWidth: '78%',
    padding: 10,
    paddingBottom: 6,
    borderRadius: 16,
  },
  myBubble: {
    backgroundColor: '#2E6BFF',
    borderBottomRightRadius: 4,
  },
  otherBubble: {
    backgroundColor: '#1e1e1e',
    borderBottomLeftRadius: 4,
  },
  msgSender: {
    color: '#2E6BFF',
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 2,
  },
  msgText: {
    color: '#ddd',
    fontSize: 14,
    lineHeight: 20,
  },
  myMsgText: {
    color: '#fff',
  },
  msgTime: {
    color: '#666',
    fontSize: 10,
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  myMsgTime: {
    color: 'rgba(255,255,255,0.6)',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: '#222',
    backgroundColor: '#0c0c0c',
  },
  input: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: '#fff',
    fontSize: 14,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#2E6BFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: {
    backgroundColor: '#1a1a1a',
  },
});
