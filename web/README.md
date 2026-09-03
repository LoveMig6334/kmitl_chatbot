# KMTL Chatbot

A bilingual (Thai / English) AI study-assistant chatbot for university students, built with **Next.js 16**, **Supabase**, and **Tailwind CSS**. Users can ask questions scoped to specific faculties, manage chat history, and toggle between light/dark and Thai/English modes.

```
Register / Login → Chat
```

## Features

### Accounts
- `/register` (display name, email, password with live requirements) and `/login`, both with
  **Continue with Google** (Supabase Auth). `/forgot-password` → email link → `/update-password`.
- Route protection in `src/proxy.ts`: signed-out users are sent to `/login`, signed-in users are
  kept out of the auth pages. Without Supabase keys the app runs in **demo mode** (simulated sign-in).
- User menu (avatar, theme light/dark/system, language, sign out) in `src/components/user/UserMenu.tsx`.
- `POST /api/chat` is deliberately **not** behind the proxy in Phase 1 (judges can hit the demo without
  keys; `scripts/smoke_web.py` relies on it). Phase 2 adds a session check there when chats are persisted.

### Chatbot (`/chat`, `/chat/<id>`)
- ChatGPT-style layout: resizable + collapsible sidebar on desktop, drawer on mobile, centred
  message column, composer pinned at the bottom.
- Sidebar: **New chat**, search by title, history grouped by day with a 3-dot menu (**rename**,
  **delete**), and the user entry at the bottom (theme, language, **Settings** dialog with profile,
  sign out). A new chat is only listed after its first message and is auto-titled from it.
- Streaming answers with **Stop** (Esc), **edit & resend** (replace semantics), **regenerate**,
  copy, read-aloud, Markdown with tables + code copy, per-message error/retry, jump-to-latest pill.
- **Program scope** checkboxes (AIT / DSBA / BIT / IT, default all) persisted per chat and sent as
  `facultyScope`.
- **Citations** as numbered chips → right-hand panel with document, page and excerpt, and the actual
  **PDF page** (`/api/pdf/<program>#page=N`, served from `PDF_DIR` with HTTP Range support).
- **Voice input** (Web Speech API, `th-TH`/`en-US`) with live interim text; **ghost text** completion
  (Tab to accept) from your past questions + the example list (`useGhostText`, provider swappable).
- History is stored in Supabase (`web/supabase/migrations/0001_chats.sql`, RLS per user) or, in demo
  mode, in localStorage.

## Tech stack

| Part          | Tool                     |
| ------------- | ------------------------ |
| Frontend      | Next.js (App Router, TS) |
| Styling       | Tailwind CSS v4 + design tokens (`src/app/globals.css`), Radix primitives (`radix-ui`) |
| Auth          | Supabase Auth (Google)   |
| User database | Supabase (profiles)      |
| State         | React context (theme, locale) + Zustand (chat, persisted) |
| Tests         | Vitest + Testing Library |
| Deployment    | Vercel                   |

## Getting started

```bash
npm install
npm run dev
```

Open http://localhost:3000/chat.

> The app runs in **demo mode** without any keys: auth is simulated in-browser and chat streams a placeholder reply. Add the keys below to go live.
>
> Design conventions (tokens, `t()`, theme) are listed under "UI conventions" in `../CLAUDE.md`.

## Configuration

Copy `.env.example` to `.env.local` and fill in:

| Variable                      | Description                                          |
| ----------------------------- | ---------------------------------------------------- |
| `NEXT_PUBLIC_SUPABASE_URL`    | Supabase project URL                                 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon (public) API key                     |
| `FASTAPI_URL`                 | Backend base URL (server-side only, default `http://localhost:8000`) |
| `NEXT_PUBLIC_APP_URL`         | Public app URL (for auth callbacks)                  |
| `PDF_DIR`                     | Folder with the curriculum PDFs for the source viewer (default `../data/raw`) |

### Supabase setup

1. Create a project at [supabase.com](https://supabase.com) and copy the URL + anon key.
2. In **Authentication → Providers**, enable **Google** and add your OAuth credentials.
3. Set the auth callback redirect URL to `${APP_URL}/auth/callback` (used by Google OAuth,
   email confirmation and password-reset links).
4. The display name is stored in `auth.users.user_metadata.display_name` — no table needed for sign-up.
5. Run `supabase/migrations/0001_chats.sql` in the SQL editor to create `chats` / `messages` (with RLS).

### Backend

`src/lib/ai.ts` talks to the FastAPI gatekeeper + RAG backend (`POST ${FASTAPI_URL}/chat`,
contract in `../docs/api-contract.md`) and `app/api/chat/route.ts` re-streams its events to
the browser as `data: {...}` lines: `{meta}`, `{delta}`, `{citations}`, `{done, partial}`,
`{error}`. Run both servers with `../scripts/dev.sh`; if the backend is unreachable the
route streams a mock reply instead.

## Scripts

```bash
npm run dev      # start the dev server (Turbopack)
npm run build    # production build
npm run start    # serve the production build
npm run lint     # run ESLint
npm run typecheck  # tsc --noEmit
npm test         # Vitest (jsdom + Testing Library)
```

## Project structure

```
src/
├─ app/
│  ├─ api/chat/route.ts        # SSE streaming AI proxy
│  ├─ auth/callback/route.ts   # Supabase OAuth callback
│  ├─ api/pdf/[program]/       # curriculum PDFs with Range support (PDF_DIR)
│  ├─ chat/[[...chatId]]/      # chat UI (/chat = new, /chat/<id>)
│  └─ login|register|forgot-password|update-password/   # auth pages (signup → register)
├─ proxy.ts                    # route protection (Supabase session refresh + redirects)
├─ components/
│  ├─ auth/                    # AuthLayout, Login/Register/Forgot/UpdatePassword forms, Google button
│  ├─ user/UserMenu.tsx        # avatar menu: theme, language, settings, sign out
│  ├─ chat/                    # ChatApp, ChatSidebar, Composer, MessageList/Item, Markdown, SourcePanel, SettingsDialog
│  ├─ ui/                      # design-system primitives (Radix-based)
│  └─ icons/                   # brand marks (only place literal colours are allowed)
├─ i18n/                       # th.ts (source of truth), en.ts, translate()
├─ providers/                  # ThemeProvider, LocaleProvider, AppProviders
├─ hooks/                      # useChatController, useGhostText, useSpeechRecognition, useAutoScroll, useSidebarLayout, useUser …
└─ lib/                        # chat/ (types, stream reducer, payload, repositories, store), auth/, supabase clients, ai, pdf
supabase/migrations/           # SQL to apply by hand (never run automatically)
```

## License

MIT
