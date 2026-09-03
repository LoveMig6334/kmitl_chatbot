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

### Chatbot
- Chat window with a **left sidebar** (Profile, Your chats, Settings, Language).
- **New chat**, chat history, and rename/delete.
- **Stop** button to halt generation mid-stream (SSE streaming).
- **Edit & resend** messages you've already sent.
- **Program scope** selector (AIT / DSBA / BIT / IT) sent to the backend as `scope`.
- **Citations** under each answer (`{program} หน้า {page}` chips, snippet on click) and a retry link when an answer was cut short.

### App utilities
- **Dark / Light** mode toggle.
- **Thai / English** UI toggle.
- **Voice mode** (mic) using the browser Web Speech API.
- **Ghost text** while typing with rotating suggested prompts.

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

### Supabase setup

1. Create a project at [supabase.com](https://supabase.com) and copy the URL + anon key.
2. In **Authentication → Providers**, enable **Google** and add your OAuth credentials.
3. Set the auth callback redirect URL to `${APP_URL}/auth/callback` (used by Google OAuth,
   email confirmation and password-reset links).
4. The display name is stored in `auth.users.user_metadata.display_name` — no table needed for sign-up.
   (The legacy `/profile` page still upserts a `profiles` table; revisited in Phase 2.)

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
│  ├─ chat/                    # main chatbot UI
│  ├─ login|register|forgot-password|update-password/   # auth pages (signup → register)
│  └─ profile|settings/        # legacy pages, revisited in Phase 2
├─ proxy.ts                    # route protection (Supabase session refresh + redirects)
├─ components/
│  ├─ auth/                    # AuthLayout, Login/Register/Forgot/UpdatePassword forms, Google button
│  ├─ user/UserMenu.tsx        # avatar menu: theme, language, sign out
│  ├─ chat/                    # sidebar, composer, bubbles, scope (Phase 2)
│  ├─ ui/                      # design-system primitives (Radix-based)
│  └─ icons/                   # brand marks (only place literal colours are allowed)
├─ i18n/                       # th.ts (source of truth), en.ts, translate()
├─ providers/                  # ThemeProvider, LocaleProvider, AppProviders
├─ hooks/                      # useUser, useFormState, usePageTitle, useT (legacy)
└─ lib/                        # auth/ (client, errors, validation, routes), supabase clients, ai, store
```

## License

MIT
