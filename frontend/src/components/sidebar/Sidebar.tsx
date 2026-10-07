import React, { useState, useMemo } from 'react';
import {
  Plus,
  Search,
  Layers,
  LogOut,
  Pin,
  Archive,
  ChevronDown,
  ChevronRight,
  X,
} from 'lucide-react';
import type { Chat } from '../../types';
import { ChatListItem } from './ChatListItem';
import { ShareModal } from '../chat/ShareModal';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Separator } from '../ui/separator';
import { Avatar } from '../ui/avatar';
import { Sheet } from '../ui/sheet';

interface SidebarProps {
  chats: Chat[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onRenameChat: (id: string, newTitle: string) => void;
  onDeleteChat: (id: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onRenameChat,
  onDeleteChat,
  isOpen,
  onToggle,
}) => {
  const { user, logout } = useAuth();
  const [search, setSearch] = useState('');
  const [shareChat, setShareChat] = useState<Chat | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [showPinned, setShowPinned] = useState(true);

  // Persistent Pinned Chats in localStorage
  const [pinnedIds, setPinnedIds] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem('sap_assistant_pinned');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // Persistent Archived Chats in localStorage
  const [archivedIds, setArchivedIds] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem('sap_assistant_archived');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const togglePin = (id: string) => {
    setPinnedIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      localStorage.setItem('sap_assistant_pinned', JSON.stringify(next));
      return next;
    });
  };

  const toggleArchive = (id: string) => {
    setArchivedIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      localStorage.setItem('sap_assistant_archived', JSON.stringify(next));
      return next;
    });
  };

  const filteredChats = useMemo(() => {
    if (!search.trim()) return chats;
    return chats.filter((c) => c.title.toLowerCase().includes(search.toLowerCase()));
  }, [chats, search]);

  const { pinnedChats, normalChats, archivedChats } = useMemo(() => {
    const pinned: Chat[] = [];
    const normal: Chat[] = [];
    const archived: Chat[] = [];

    filteredChats.forEach((chat) => {
      if (archivedIds.includes(chat.id)) {
        archived.push(chat);
      } else if (pinnedIds.includes(chat.id)) {
        pinned.push(chat);
      } else {
        normal.push(chat);
      }
    });

    return { pinnedChats: pinned, normalChats: normal, archivedChats: archived };
  }, [filteredChats, pinnedIds, archivedIds]);

  const groupedChats = useMemo(() => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const last7Days = new Date(today);
    last7Days.setDate(last7Days.getDate() - 7);

    const groups: { [key: string]: Chat[] } = {
      Today: [],
      Yesterday: [],
      'Previous 7 Days': [],
      Older: [],
    };

    normalChats.forEach((chat) => {
      const chatDate = new Date(chat.updated_at);
      if (chatDate.toDateString() === today.toDateString()) {
        groups['Today'].push(chat);
      } else if (chatDate.toDateString() === yesterday.toDateString()) {
        groups['Yesterday'].push(chat);
      } else if (chatDate >= last7Days) {
        groups['Previous 7 Days'].push(chat);
      } else {
        groups['Older'].push(chat);
      }
    });

    return groups;
  }, [normalChats]);

  // Sidebar content markup reused across desktop and mobile Sheet
  const sidebarContent = (
    <div className="flex flex-col h-full w-full bg-slate-950 border-r border-slate-800 text-slate-200 select-none">
      {/* Top Header */}
      <div className="flex items-center justify-between px-3.5 py-3 border-b border-slate-850 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-slate-900 border border-slate-700/80 flex items-center justify-center text-sap-400">
            <Layers className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-semibold text-slate-100 tracking-tight">
            SAP Knowledge Assistant
          </span>
        </div>

        {/* Mobile close button */}
        <button
          type="button"
          onClick={onToggle}
          className="md:hidden p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          aria-label="Close sidebar"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-2.5 shrink-0">
        <Button
          onClick={onNewChat}
          variant="sap"
          className="w-full flex items-center justify-center gap-2 py-2"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Chat</span>
        </Button>
      </div>

      {/* Search Bar */}
      <div className="px-2.5 pb-2 shrink-0">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500 pointer-events-none" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations..."
            className="pl-8 h-8 text-xs bg-slate-900/60 border-slate-800"
          />
        </div>
      </div>

      <Separator />

      {/* Chat List Scrollable Area */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-3">
        {/* Pinned Section */}
        {pinnedChats.length > 0 && (
          <div>
            <button
              type="button"
              onClick={() => setShowPinned((v) => !v)}
              className="w-full flex items-center justify-between px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-200 transition group"
            >
              <div className="flex items-center gap-1.5">
                <Pin className="w-3 h-3 text-sap-400" />
                <span>Pinned</span>
              </div>
              <ChevronDown
                className={`w-3 h-3 text-slate-500 transition-transform ${
                  showPinned ? 'rotate-0' : '-rotate-90'
                }`}
              />
            </button>
            {showPinned && (
              <div className="space-y-0.5 mt-0.5">
                {pinnedChats.map((chat) => (
                  <ChatListItem
                    key={chat.id}
                    chat={chat}
                    isActive={chat.id === activeChatId}
                    isPinned={true}
                    isArchived={false}
                    onSelect={onSelectChat}
                    onRename={onRenameChat}
                    onDelete={onDeleteChat}
                    onShare={(c) => setShareChat(c)}
                    onTogglePin={togglePin}
                    onToggleArchive={toggleArchive}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Regular Date-grouped Sections */}
        {Object.entries(groupedChats).map(([groupName, groupChats]) => {
          if (groupChats.length === 0) return null;
          return (
            <div key={groupName}>
              <div className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                {groupName}
              </div>
              <div className="space-y-0.5">
                {groupChats.map((chat) => (
                  <ChatListItem
                    key={chat.id}
                    chat={chat}
                    isActive={chat.id === activeChatId}
                    isPinned={false}
                    isArchived={false}
                    onSelect={onSelectChat}
                    onRename={onRenameChat}
                    onDelete={onDeleteChat}
                    onShare={(c) => setShareChat(c)}
                    onTogglePin={togglePin}
                    onToggleArchive={toggleArchive}
                  />
                ))}
              </div>
            </div>
          );
        })}

        {/* Archived Section */}
        {archivedChats.length > 0 && (
          <div className="pt-2 border-t border-slate-900">
            <button
              type="button"
              onClick={() => setShowArchived((v) => !v)}
              className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-medium text-slate-400 hover:text-slate-200 transition"
            >
              <div className="flex items-center gap-1.5">
                <Archive className="w-3 h-3 text-slate-400" />
                <span>Archived ({archivedChats.length})</span>
              </div>
              {showArchived ? (
                <ChevronDown className="w-3 h-3 text-slate-500" />
              ) : (
                <ChevronRight className="w-3 h-3 text-slate-500" />
              )}
            </button>

            {showArchived && (
              <div className="space-y-0.5 mt-1">
                {archivedChats.map((chat) => (
                  <ChatListItem
                    key={chat.id}
                    chat={chat}
                    isActive={chat.id === activeChatId}
                    isPinned={false}
                    isArchived={true}
                    onSelect={onSelectChat}
                    onRename={onRenameChat}
                    onDelete={onDeleteChat}
                    onShare={(c) => setShareChat(c)}
                    onTogglePin={togglePin}
                    onToggleArchive={toggleArchive}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {filteredChats.length === 0 && (
          <div className="text-center py-8 px-4 text-xs text-slate-500">
            {search ? 'No matching conversations' : 'No conversations yet'}
          </div>
        )}
      </div>

      <Separator />

      {/* User Footer */}
      {user && (
        <div className="p-2.5 shrink-0 bg-slate-950">
          <div className="flex items-center justify-between p-1.5 rounded-lg bg-slate-900/60 border border-slate-850">
            <div className="flex items-center gap-2 min-w-0">
              <Avatar fallback={user.name ? user.name.charAt(0).toUpperCase() : 'U'} />
              <div className="min-w-0">
                <span className="text-xs font-medium text-slate-200 block truncate leading-tight">
                  {user.name}
                </span>
                <span className="text-[10px] text-slate-500 block truncate">
                  {user.email}
                </span>
              </div>
            </div>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={logout}
              title="Log out"
              aria-label="Log out"
              className="h-7 w-7 text-slate-400 hover:text-rose-400"
            >
              <LogOut className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop fixed sidebar (256px) */}
      <aside className="hidden md:flex flex-col w-64 shrink-0 h-full">
        {sidebarContent}
      </aside>

      {/* Mobile Sheet Drawer */}
      <Sheet open={isOpen} onOpenChange={(open) => !open && onToggle()} side="left">
        {sidebarContent}
      </Sheet>

      {/* Share Modal */}
      <ShareModal
        chat={shareChat}
        isOpen={!!shareChat}
        onClose={() => setShareChat(null)}
      />
    </>
  );
};
