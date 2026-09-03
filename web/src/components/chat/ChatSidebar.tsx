"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { PanelLeftClose, Search, SquarePen } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Tooltip } from "@/components/ui/Tooltip";
import { Skeleton } from "@/components/ui/Skeleton";
import { BrandMark } from "@/components/auth/BrandMark";
import { UserMenu } from "@/components/user/UserMenu";
import { useTranslation } from "@/providers/LocaleProvider";
import type { MessageKey } from "@/i18n";
import type { Chat } from "@/lib/chat";
import { ChatListItem } from "./ChatListItem";

export interface ChatSidebarProps {
  chats: Chat[];
  activeId: string | null;
  ready: boolean;
  loadError: boolean;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onCollapse?: () => void;
  /** Called after any navigation (closes the mobile drawer). */
  onNavigate?: () => void;
  onOpenSettings: () => void;
}

const DAY = 86_400_000;

export function groupChats(chats: Chat[], now = Date.now()): { key: MessageKey; chats: Chat[] }[] {
  const startOfToday = new Date(now).setHours(0, 0, 0, 0);
  const buckets: Record<string, Chat[]> = { today: [], yesterday: [], week: [], older: [] };
  for (const c of chats) {
    if (c.updatedAt >= startOfToday) buckets.today.push(c);
    else if (c.updatedAt >= startOfToday - DAY) buckets.yesterday.push(c);
    else if (c.updatedAt >= startOfToday - 7 * DAY) buckets.week.push(c);
    else buckets.older.push(c);
  }
  const keys: [string, MessageKey][] = [
    ["today", "chat.today"],
    ["yesterday", "chat.yesterday"],
    ["week", "chat.thisWeek"],
    ["older", "chat.older"],
  ];
  return keys.filter(([k]) => buckets[k].length > 0).map(([k, key]) => ({ key, chats: buckets[k] }));
}

export function ChatSidebar({ chats, activeId, ready, loadError, onRename, onDelete, onCollapse, onNavigate, onOpenSettings }: ChatSidebarProps) {
  const t = useTranslation();
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? chats.filter((c) => c.title.toLowerCase().includes(q)) : chats;
  }, [chats, query]);
  const groups = useMemo(() => groupChats(filtered), [filtered]);

  return (
    <div className="flex h-full flex-col bg-bg-subtle">
      <div className="flex items-center justify-between gap-2 px-3 pt-3">
        <BrandMark label={t("app.name")} />
        {onCollapse && (
          <Tooltip content={t("chat.closeSidebar")}>
            <Button variant="ghost" size="icon" onClick={onCollapse} aria-label={t("chat.closeSidebar")} className="size-8">
              <PanelLeftClose className="size-4" />
            </Button>
          </Tooltip>
        )}
      </div>

      <div className="flex flex-col gap-1 px-3 pt-3">
        <Button asChild variant="outline" className="justify-start">
          <Link href="/chat" onClick={onNavigate}>
            <SquarePen className="size-4" />
            {t("chat.newChat")}
          </Link>
        </Button>
        <label className="relative mt-1 block">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-fg-subtle" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("chat.searchPlaceholder")}
            aria-label={t("chat.searchPlaceholder")}
            className="focus-ring h-9 w-full rounded-md border border-border bg-surface pl-8 pr-2 text-sm text-fg"
          />
        </label>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-3" aria-label={t("chat.history")}>
        {!ready ? (
          <div className="flex flex-col gap-2 px-1">
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
            <Skeleton className="h-8 w-2/3" />
          </div>
        ) : loadError ? (
          <p className="px-2 text-xs text-danger">{t("chat.loadFailed")}</p>
        ) : chats.length === 0 ? (
          <p className="px-2 text-xs text-fg-muted">{t("chat.noChats")}</p>
        ) : groups.length === 0 ? (
          <p className="px-2 text-xs text-fg-muted">{t("chat.noResults")}</p>
        ) : (
          groups.map((g) => (
            <div key={g.key} className="mb-3">
              <h2 className="px-3 pb-1 text-xs font-medium text-fg-muted">{t(g.key)}</h2>
              <ul className="flex flex-col gap-0.5">
                {g.chats.map((c) => (
                  <ChatListItem
                    key={c.id}
                    chat={c}
                    active={c.id === activeId}
                    onRename={(title) => onRename(c.id, title)}
                    onDelete={() => onDelete(c.id)}
                    onNavigate={onNavigate}
                  />
                ))}
              </ul>
            </div>
          ))
        )}
      </nav>

      <div className="border-t border-border p-2">
        <UserMenu className="w-full justify-start rounded-md" onOpenSettings={onOpenSettings} side="top" />
      </div>
    </div>
  );
}
