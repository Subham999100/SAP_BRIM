import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Menu, ArrowDown, Shield, Database } from 'lucide-react';
import type { Chat, Message } from '../types';
import { Sidebar } from '../components/sidebar/Sidebar';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { WelcomeScreen } from '../components/chat/WelcomeScreen';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Avatar } from '../components/ui/avatar';
import { useAuth } from '../context/AuthContext';
import {
  apiGetChats,
  apiCreateChat,
  apiUpdateChat,
  apiDeleteChat,
  apiGetMessages,
  apiStreamMessage,
  type StreamMetadata,
} from '../services/api';

export const ChatPage: React.FC = () => {
  const { user } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [streamingMeta, setStreamingMeta] = useState<StreamMetadata | null>(null);
  const [isScrolledUp, setIsScrolledUp] = useState(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check scroll position to determine if user scrolled away from bottom
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    // If more than 120px from bottom, consider user scrolled up
    setIsScrolledUp(distanceToBottom > 120);
  }, []);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
    setIsScrolledUp(false);
  }, []);

  // Follow stream if user hasn't scrolled up
  useEffect(() => {
    if (!isScrolledUp) {
      // Use instant scroll during rapid streaming to prevent jitter
      const behavior = streamingContent ? 'auto' : 'smooth';
      messagesEndRef.current?.scrollIntoView({ behavior });
    }
  }, [messages, streamingContent, isScrolledUp]);

  // Load chats on initial mount
  useEffect(() => {
    loadChats();
  }, []);

  const loadChats = async () => {
    try {
      const data = await apiGetChats();
      setChats(data);
      if (data.length > 0 && !activeChatId) {
        selectChat(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load chats:', err);
    }
  };

  const selectChat = async (chatId: string) => {
    setActiveChatId(chatId);
    setStreamingContent(null);
    setStreamingMeta(null);
    setIsScrolledUp(false);
    try {
      const msgs = await apiGetMessages(chatId);
      setMessages(msgs);
      setTimeout(() => scrollToBottom('auto'), 50);
    } catch (err) {
      console.error('Failed to load messages for chat:', chatId, err);
      setMessages([]);
    }
  };

  const handleNewChat = async () => {
    try {
      const newChat = await apiCreateChat('New SAP Chat');
      setChats([newChat, ...chats]);
      setActiveChatId(newChat.id);
      setMessages([]);
      setStreamingContent(null);
      setStreamingMeta(null);
      setSidebarOpen(false);
      setIsScrolledUp(false);
    } catch (err) {
      console.error('Failed to create new chat:', err);
    }
  };

  const handleRenameChat = async (id: string, newTitle: string) => {
    try {
      const updated = await apiUpdateChat(id, newTitle);
      setChats((prev) => prev.map((c) => (c.id === id ? updated : c)));
    } catch (err) {
      console.error('Failed to rename chat:', err);
    }
  };

  const handleDeleteChat = async (id: string) => {
    try {
      await apiDeleteChat(id);
      const remaining = chats.filter((c) => c.id !== id);
      setChats(remaining);
      if (activeChatId === id) {
        if (remaining.length > 0) {
          selectChat(remaining[0].id);
        } else {
          setActiveChatId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete chat:', err);
    }
  };

  const handleSendMessage = async (content: string) => {
    let currentId = activeChatId;

    // If no active chat exists, create one automatically
    if (!currentId) {
      try {
        const newChat = await apiCreateChat(content.slice(0, 30));
        setChats([newChat, ...chats]);
        currentId = newChat.id;
        setActiveChatId(currentId);
      } catch (err) {
        console.error('Could not create initial chat:', err);
        return;
      }
    }

    // Optimistically add user message to UI
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      chat_id: currentId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      citations: [],
      web_sources: [],
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);
    setStreamingContent('');
    setStreamingMeta(null);
    setIsScrolledUp(false);

    let accumulatedText = '';
    let streamMetaRef: StreamMetadata | null = null;

    // Stream response via real SSE backend
    await apiStreamMessage(
      currentId,
      content,
      (meta) => {
        streamMetaRef = meta;
        setStreamingMeta(meta);
      },
      (token) => {
        accumulatedText += token;
        setStreamingContent(accumulatedText);
      },
      () => {
        // SSE streaming finished
        setIsLoading(false);
        const finalAssistantMsg: Message = {
          id: streamMetaRef?.message_id || `msg-${Date.now()}`,
          chat_id: currentId!,
          role: 'assistant',
          content: accumulatedText,
          source_type: streamMetaRef?.source_type || 'knowledge_base',
          grounding_score: streamMetaRef?.grounding_score,
          created_at: new Date().toISOString(),
          citations: streamMetaRef?.citations || [],
          web_sources: streamMetaRef?.web_sources || [],
        };

        setMessages((prev) => {
          if (prev.some((m) => m.id === finalAssistantMsg.id)) {
            return prev;
          }
          return [...prev, finalAssistantMsg];
        });

        setStreamingContent(null);
        setStreamingMeta(null);

        // Refresh chat list to update timestamps or auto-generated title
        apiGetChats().then(setChats).catch(() => {});
      },
      (err) => {
        console.error('Stream error:', err);
        setIsLoading(false);
        setStreamingContent(null);
        const errorMsg: Message = {
          id: `err-${Date.now()}`,
          chat_id: currentId!,
          role: 'assistant',
          content: 'An error occurred while connecting to the SAP Knowledge Assistant. Please try again.',
          source_type: 'error',
          created_at: new Date().toISOString(),
          citations: [],
          web_sources: [],
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    );
  };

  const activeChat = chats.find((c) => c.id === activeChatId);

  return (
    <div className="flex h-screen w-full bg-[#090d16] text-slate-100 overflow-hidden font-sans">
      {/* Sidebar (Desktop fixed 256px, Mobile Sheet) */}
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={(id) => {
          selectChat(id);
          setSidebarOpen(false);
        }}
        onNewChat={handleNewChat}
        onRenameChat={handleRenameChat}
        onDeleteChat={handleDeleteChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 bg-[#090d16] relative">
        {/* Compact Professional Header */}
        <header className="h-12 border-b border-slate-800/80 bg-slate-950/80 px-4 flex items-center justify-between shrink-0 z-10 select-none">
          <div className="flex items-center gap-2.5 min-w-0">
            {/* Mobile Hamburger */}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(true)}
              className="md:hidden h-7 w-7 text-slate-400 hover:text-slate-100"
              aria-label="Open sidebar"
            >
              <Menu className="w-4 h-4" />
            </Button>

            {/* Title & Scope */}
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs font-medium text-slate-200 truncate">
                {activeChat ? activeChat.title : 'New SAP Session'}
              </span>
              <Badge variant="sap" className="hidden sm:inline-flex gap-1 text-[10px]">
                <Shield className="w-2.5 h-2.5" />
                <span>SAP Scope Only</span>
              </Badge>
            </div>
          </div>

          {/* Right Header Status / User Info */}
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant="secondary" className="hidden md:inline-flex gap-1 text-[10px] text-slate-400">
              <Database className="w-2.5 h-2.5 text-sap-400" />
              <span>S/4HANA &middot; Fiori &middot; BRIM</span>
            </Badge>

            {user && (
              <Avatar
                fallback={user.name ? user.name.charAt(0).toUpperCase() : 'U'}
                className="h-6 w-6 text-[10px]"
                title={user.name}
              />
            )}
          </div>
        </header>

        {/* Message Area */}
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto flex flex-col relative"
        >
          {messages.length === 0 && !streamingContent ? (
            <WelcomeScreen onSelectPrompt={(prompt) => handleSendMessage(prompt)} />
          ) : (
            <div className="flex-1 pb-4">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}

              {/* In-flight streaming response indicator */}
              {streamingContent !== null && (
                <ChatMessage
                  isStreaming={true}
                  message={{
                    id: 'streaming-assistant',
                    chat_id: activeChatId || '',
                    role: 'assistant',
                    content: streamingContent,
                    source_type: streamingMeta?.source_type,
                    grounding_score: streamingMeta?.grounding_score,
                    created_at: new Date().toISOString(),
                    citations: streamingMeta?.citations || [],
                    web_sources: streamingMeta?.web_sources || [],
                  }}
                />
              )}

              <div ref={messagesEndRef} className="h-px" />
            </div>
          )}

          {/* Jump to latest floating button */}
          {isScrolledUp && (
            <div className="sticky bottom-3 left-0 right-0 flex justify-center pointer-events-none z-20">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => scrollToBottom('smooth')}
                className="pointer-events-auto gap-1.5 shadow-md bg-slate-900/95 border-slate-700 text-slate-200 hover:text-white"
                aria-label="Jump to latest message"
              >
                <ArrowDown className="w-3.5 h-3.5" />
                <span>Jump to latest</span>
              </Button>
            </div>
          )}
        </div>

        {/* Bottom Composer Area */}
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};
