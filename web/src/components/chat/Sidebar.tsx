"use client";

import Link from "next/link";
import {
  ChevronRight,
  LogOut,
  MessageSquare,
  PanelLeftClose,
  Plus,
  Settings,
  User,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useT } from "@/hooks/useT";
import { useAppStore } from "@/lib/store";
import type { ChatSession } from "@/lib/store";
import { Avatar } from "@/components/ui/Avatar";

interface Props {
  onNewChat: () => void;
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function Sidebar({ onNewChat, sessions, activeId, onSelect, onDelete }: Props) {
  const t = useT();
  const router = useRouter();
  const profile = useAppStore((s) => s.profile);
  const setProfile = useAppStore((s) => s.setProfile);

  function logout() {
    setProfile({ authed: false });
    router.push("/login");
  }

  const menu = [
    { href: "/settings", label: t.profile, icon: <User className="h-4 w-4" /> },
    {
      href: "/settings?section=language",
      label: t.language,
      icon: <MessageSquare className="h-4 w-4" />,
    },
    {
      href: "/settings?section=settings",
      label: t.settings,
      icon: <Settings className="h-4 w-4" />,
    },
  ];

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col gap-3 p-3">
      <div className="flex items-center justify-between rounded-xl bg-surface p-2.5 shadow-sm">
        <span className="text-sm font-semibold">{t.newChat}</span>
        <button
          onClick={onNewChat}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-accent-foreground transition-colors hover:bg-accent-strong"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-col gap-0.5 rounded-xl bg-surface p-2 shadow-sm">
        {menu.map((m) => (
          <Link
            key={m.href}
            href={m.href}
            className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-sm font-medium transition-colors hover:bg-surface-muted"
          >
            <span className="text-muted">{m.icon}</span>
            <span className="flex-1 text-left">{m.label}</span>
            <ChevronRight className="h-4 w-4 text-muted" />
          </Link>
        ))}
      </div>

      <div className="flex flex-1 flex-col gap-2 overflow-hidden rounded-xl bg-surface p-2.5 shadow-sm">
        <div className="flex items-center gap-2 px-2 py-1 text-xs font-medium text-muted">
          <PanelLeftClose className="h-3.5 w-3.5" />
          {t.yourChats} ({sessions.length})
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {sessions.length === 0 && (
            <p className="px-2 py-1 text-xs text-muted">{t.emptyHistory}</p>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`group flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors ${
                s.id === activeId
                  ? "bg-surface-muted text-foreground"
                  : "text-muted hover:bg-surface-muted hover:text-foreground"
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5 shrink-0" />
              <span className="flex-1 truncate">{s.title || t.newChat}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(s.id);
                }}
                className="hidden text-muted opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
              >
                <Settings className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={logout}
        className="flex items-center gap-2.5 rounded-xl bg-surface p-2.5 text-sm shadow-sm transition-colors hover:bg-surface-muted"
      >
        <Avatar name={profile.fullName} size={32} />
        <span className="flex-1 truncate text-left">{profile.fullName}</span>
        <LogOut className="h-4 w-4 text-muted" />
      </button>
    </aside>
  );
}
