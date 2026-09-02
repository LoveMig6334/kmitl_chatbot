# KMTL Chatbot

A bilingual (Thai / English) AI study-assistant chatbot for university students, built with **Next.js 16**, **Supabase**, and **Tailwind CSS**. Users can ask questions scoped to specific faculties, manage chat history, and toggle between light/dark and Thai/English modes.

```
Sign up → Create profile → Chat
```

## Features

### Accounts
- Sign-up with email & password, or **Continue with Google** (Supabase Auth).
- Profile creation: Full name, user name, degree, and educational faculty.
- Login screen for returning users.

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
| Styling       | Tailwind CSS v4          |
| Auth          | Supabase Auth (Google)   |
| User database | Supabase (profiles)      |
| State         | Zustand (persisted)      |
| Deployment    | Vercel                   |

## Getting started

```bash
npm install
npm run dev
```

Open http://localhost:3000/chat.

> The app runs in **demo mode** without any keys: auth is simulated in-browser and chat streams a placeholder reply. Add the keys below to go live.

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
3. Set the auth callback redirect URL to `${APP_URL}/auth/callback`.
4. Create a `profiles` table for user data (id, full_name, user_name, degree, faculty, email).

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
```

## Project structure

```
src/
├─ app/
│  ├─ api/chat/route.ts        # SSE streaming AI proxy
│  ├─ auth/callback/route.ts   # Supabase OAuth callback
│  ├─ chat/                    # main chatbot UI
│  ├─ login|signup|profile/    # account & profile flows
│  └─ register/                # redirects to /signup
├─ components/
│  ├─ auth/                    # sign-up, login, profile, Google
│  ├─ chat/                    # sidebar, composer, bubbles, scope
│  └─ ui/                      # Button, Input, Select, Checkbox, Avatar
├─ hooks/useT.ts               # locale-aware translation hook
└─ lib/                        # store, supabase clients, ai, i18n, constants
```

## License

MIT
