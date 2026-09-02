import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Locale } from "./constants";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  messages: Message[];
}

export interface Profile {
  fullName: string;
  userName: string;
  degree: string;
  faculty: string;
  email: string;
  authed: boolean;
}

interface AppState {
  theme: "light" | "dark";
  locale: Locale;
  facultyScope: string[];
  sidebarOpen: boolean;
  generating: boolean;
  profile: Profile;
  sessions: ChatSession[];
  activeSessionId: string | null;
  setTheme: (t: "light" | "dark") => void;
  toggleTheme: () => void;
  setLocale: (l: Locale) => void;
  setFacultyScope: (ids: string[]) => void;
  toggleSidebar: () => void;
  setGenerating: (g: boolean) => void;
  setProfile: (p: Partial<Profile>) => void;
  newChat: () => string;
  selectSession: (id: string) => void;
  addMessage: (sessionId: string, msg: Message) => void;
  updateMessage: (sessionId: string, msgId: string, content: string) => void;
  insertMessageAfter: (sessionId: string, afterId: string, msg: Message) => void;
  deleteMessagesAfter: (sessionId: string, afterId: string) => void;
  deleteSession: (id: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: "light",
      locale: "th",
      facultyScope: [],
      sidebarOpen: true,
      generating: false,
      profile: {
        fullName: "Student",
        userName: "student",
        degree: "",
        faculty: "",
        email: "",
        authed: false,
      },
      sessions: [],
      activeSessionId: null,

      setTheme: (t) => set({ theme: t }),
      toggleTheme: () =>
        set((s) => ({ theme: s.theme === "light" ? "dark" : "light" })),
      setLocale: (l) => set({ locale: l }),
      setFacultyScope: (ids) => set({ facultyScope: ids }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setGenerating: (g) => set({ generating: g }),

      setProfile: (p) =>
        set((s) => ({ profile: { ...s.profile, ...p, authed: true } })),

      newChat: () => {
        const id = `c_${Date.now().toString(36)}`;
        const session: ChatSession = {
          id,
          title: "",
          createdAt: Date.now(),
          messages: [],
        };
        set((s) => ({
          sessions: [session, ...s.sessions],
          activeSessionId: id,
        }));
        return id;
      },

      selectSession: (id) => set({ activeSessionId: id }),

      addMessage: (sessionId, msg) =>
        set((s) => ({
          sessions: s.sessions.map((se) =>
            se.id === sessionId
              ? {
                  ...se,
                  title:
                    se.title ||
                    msg.content.slice(0, 40) ||
                    "New chat",
                  messages: [...se.messages, msg],
                }
              : se,
          ),
        })),

      updateMessage: (sessionId, msgId, content) =>
        set((s) => ({
          sessions: s.sessions.map((se) =>
            se.id === sessionId
              ? {
                  ...se,
                  messages: se.messages.map((m) =>
                    m.id === msgId ? { ...m, content } : m,
                  ),
                }
              : se,
          ),
        })),

      insertMessageAfter: (sessionId, afterId, msg) =>
        set((s) => ({
          sessions: s.sessions.map((se) =>
            se.id === sessionId
              ? {
                  ...se,
                  messages: se.messages.flatMap((m) =>
                    m.id === afterId ? [m, msg] : [m],
                  ),
                }
              : se,
          ),
        })),

      deleteMessagesAfter: (sessionId, afterId) =>
        set((s) => ({
          sessions: s.sessions.map((se) =>
            se.id === sessionId
              ? {
                  ...se,
                  messages: se.messages.filter(
                    (_, i) => i <= se.messages.findIndex((m) => m.id === afterId),
                  ),
                }
              : se,
          ),
        })),

      deleteSession: (id) =>
        set((s) => {
          const sessions = s.sessions.filter((se) => se.id !== id);
          return {
            sessions,
            activeSessionId:
              s.activeSessionId === id
                ? sessions[0]?.id ?? null
                : s.activeSessionId,
          };
        }),
    }),
    {
      name: "kmtl-chatbot",
      partialize: (s) => ({
        theme: s.theme,
        locale: s.locale,
        facultyScope: s.facultyScope,
        profile: s.profile,
        sessions: s.sessions,
        activeSessionId: s.activeSessionId,
      }),
    },
  ),
);
