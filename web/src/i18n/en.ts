import type { Dictionary } from "./th";

export const en: Dictionary = {
  // brand
  "app.name": "IT KMITL Chatbot",
  "app.tagline": "Curriculum assistant for the Faculty of IT, KMITL",
  "app.description":
    "Ask anything about the faculty's B.Sc. programs (AIT, DSBA, BIT, IT)",

  // common
  "common.loading": "Loading…",
  "common.cancel": "Cancel",
  "common.close": "Close",
  "common.back": "Back",
  "common.or": "or",
  "common.retry": "Try again",
  "common.optional": "optional",
  "common.showPassword": "Show password",
  "common.hidePassword": "Hide password",
  "common.backToChat": "Back to chat",
  "common.openMenu": "Open menu",

  // theme
  "theme.label": "Theme",
  "theme.light": "Light",
  "theme.dark": "Dark",
  "theme.system": "System",
  "theme.toggle": "Toggle theme",

  // locale
  "locale.label": "Language",
  "locale.th": "ไทย",
  "locale.en": "English",
  "locale.toggle": "Change language",

  // user menu
  "user.menu": "User menu",
  "user.signOut": "Sign out",
  "user.signedInAs": "Signed in as",
  "user.guest": "Guest",
  "user.guestHint": "Chat history is kept in this browser only",
  "user.signIn": "Sign in",
  "user.demoBadge": "Demo mode",
  "user.settings": "Settings",

  // auth: shared
  "auth.email": "Email",
  "auth.emailPlaceholder": "you@example.com",
  "auth.password": "Password",
  "auth.passwordPlaceholder": "Enter your password",
  "auth.confirmPassword": "Confirm password",
  "auth.confirmPasswordPlaceholder": "Enter the password again",
  "auth.displayName": "Display name",
  "auth.displayNamePlaceholder": "What should we call you?",
  "auth.continueWithGoogle": "Continue with Google",
  "auth.demoNotice":
    "Supabase is not configured — running in demo mode; sign-in is simulated in the browser",
  "auth.legal": "By continuing you acknowledge this is a competition demo system",

  // auth: login
  "auth.login.title": "Welcome back",
  "auth.login.subtitle": "Sign in to pick up your curriculum questions where you left off",
  "auth.login.submit": "Sign in",
  "auth.login.submitting": "Signing in…",
  "auth.login.forgot": "Forgot password?",
  "auth.login.noAccount": "Don't have an account?",
  "auth.login.registerLink": "Create one",
  "auth.login.pageTitle": "Sign in",

  // auth: register
  "auth.register.title": "Create your account",
  "auth.register.subtitle": "Takes less than a minute, then start asking",
  "auth.register.submit": "Create account",
  "auth.register.submitting": "Creating account…",
  "auth.register.haveAccount": "Already have an account?",
  "auth.register.loginLink": "Sign in",
  "auth.register.pageTitle": "Create account",
  "auth.register.checkEmailTitle": "Check your email",
  "auth.register.checkEmailBody":
    "We sent a confirmation link to {email}. Open it to activate your account, then come back and sign in.",
  "auth.register.goToLogin": "Go to sign in",

  // auth: password requirements
  "auth.pw.title": "Your password needs",
  "auth.pw.minLength": "At least 8 characters",
  "auth.pw.letter": "At least one letter",
  "auth.pw.number": "At least one number",
  "auth.pw.strength.weak": "Weak",
  "auth.pw.strength.fair": "Fair",
  "auth.pw.strength.strong": "Strong",

  // auth: forgot password
  "auth.forgot.title": "Forgot your password?",
  "auth.forgot.subtitle": "Enter your email and we'll send you a link to set a new one",
  "auth.forgot.submit": "Send reset link",
  "auth.forgot.submitting": "Sending…",
  "auth.forgot.sentTitle": "Email sent",
  "auth.forgot.sentBody":
    "If an account exists for {email}, we've sent it a password reset link. The link expires in one hour.",
  "auth.forgot.backToLogin": "Back to sign in",
  "auth.forgot.pageTitle": "Forgot password",

  // auth: update password
  "auth.update.title": "Set a new password",
  "auth.update.subtitle": "Choose a new password for your account",
  "auth.update.newPassword": "New password",
  "auth.update.submit": "Save new password",
  "auth.update.submitting": "Saving…",
  "auth.update.successTitle": "Password updated",
  "auth.update.successBody": "Your new password is active. Taking you to the chat…",
  "auth.update.noSessionTitle": "This link is invalid or has expired",
  "auth.update.noSessionBody":
    "Request a new password reset link and open it from your email within one hour.",
  "auth.update.requestAgain": "Request a new link",
  "auth.update.pageTitle": "Set new password",

  // validation
  "validation.required": "This field is required",
  "validation.emailInvalid": "Enter a valid email address",
  "validation.passwordTooShort": "Password must be at least 8 characters",
  "validation.passwordMismatch": "The passwords don't match",
  "validation.displayNameTooShort": "Display name must be at least 2 characters",
  "validation.displayNameTooLong": "Display name must be 40 characters or fewer",

  // auth errors
  "authError.invalid_credentials": "Incorrect email or password",
  "authError.email_not_confirmed":
    "This email hasn't been confirmed yet. Open the confirmation link we emailed you, then sign in.",
  "authError.rate_limited": "Too many attempts. Please wait a moment and try again.",
  "authError.network": "Couldn't reach the server. Check your connection and try again.",
  "authError.user_exists": "An account with this email already exists. Try signing in instead.",
  "authError.weak_password": "That password is too easy to guess. Please choose a stronger one.",
  "authError.same_password": "The new password must be different from the old one.",
  "authError.session_expired": "Your session has expired. Please sign in again.",
  "authError.oauth_failed": "Google sign-in didn't complete. Please try again.",
  "authError.link_invalid": "This link is no longer valid (expired or already used). Please request a new password reset link.",
  "authError.confirm_link_used":
    "The confirmation link was already used or opened in another browser. Your account is probably confirmed — try signing in.",
  "authError.provider_disabled": "This sign-in method isn't enabled yet.",
  "authError.unknown": "Something went wrong. Please try again.",

  // toasts
  "toast.region": "Notifications",
  "toast.signedOut": "Signed out",
  "toast.signedIn": "Signed in",
  "toast.accountCreated": "Account created",
  "toast.passwordUpdated": "Password updated",

  // chat: layout
  "chat.pageTitle": "Chat",
  "chat.newChat": "New chat",
  "chat.history": "Chat history",
  "chat.searchPlaceholder": "Search chats…",
  "chat.noChats": "No chats yet. Ask your first question to start one.",
  "chat.noResults": "No chats match your search",
  "chat.openSidebar": "Open sidebar",
  "chat.closeSidebar": "Close sidebar",
  "chat.resizeSidebar": "Resize sidebar",
  "chat.untitled": "Untitled chat",
  "chat.today": "Today",
  "chat.yesterday": "Yesterday",
  "chat.thisWeek": "Previous 7 days",
  "chat.older": "Older",
  "chat.menu": "Chat options",
  "chat.rename": "Rename",
  "chat.renameTitle": "Rename chat",
  "chat.renameLabel": "Chat title",
  "chat.delete": "Delete",
  "chat.deleteTitle": "Delete this chat?",
  "chat.deleteBody": "All messages in “{title}” will be permanently removed.",
  "chat.deleteConfirm": "Delete chat",
  "chat.save": "Save",
  "chat.loadFailed": "Couldn't load your chat history",

  // chat: empty state
  "chat.emptyTitle": "What would you like to know about the programs?",
  "chat.emptySubtitle": "Ask anything about the B.Sc. programs of the Faculty of IT, KMITL — AIT, DSBA, BIT or IT",
  "chat.example1": "How many credits does the AIT program require?",
  "chat.example2": "What's the difference between DSBA and IT?",
  "chat.example3": "Which language is the BIT program taught in?",
  "chat.example4": "What do first-year IT students study?",
  "chat.example5": "What are the admission requirements for DSBA?",
  "chat.example6": "What careers can AIT graduates pursue?",

  // chat: composer
  "chat.placeholder": "Ask about the curricula… (Enter to send, Shift+Enter for a new line)",
  "chat.send": "Send message",
  "chat.stop": "Stop generating",
  "chat.ghostHint": "Press Tab to accept the suggestion",
  "chat.scope": "Program scope",
  "chat.scopeAll": "All programs",
  "chat.scopeSome": "{count} programs",
  "chat.scopeHint": "Choose which programs to search (sent with every question)",
  "chat.scopeSelectAll": "Select all",
  "chat.mic": "Speak your question",
  "chat.micStop": "Stop listening",
  "chat.micListening": "Listening…",
  "chat.micUnsupported": "Voice input isn't supported in this browser. Try Chrome or Edge.",
  "chat.micDenied": "Microphone permission was denied",
  "chat.disclaimer": "Answers come from the curriculum documents. Confirm with the faculty before deciding.",

  // chat: messages
  "chat.you": "You",
  "chat.assistant": "Assistant",
  "chat.thinking": "Looking that up…",
  "chat.copy": "Copy",
  "chat.copied": "Copied",
  "chat.copyCode": "Copy code",
  "chat.edit": "Edit message",
  "chat.editSave": "Save & resend",
  "chat.regenerate": "Regenerate",
  "chat.retry": "Try again",
  "chat.readAloud": "Read aloud",
  "chat.stopReading": "Stop reading",
  "chat.stopped": "Stopped before the answer finished",
  "chat.partial": "The answer may be incomplete",
  "chat.error.generic": "Couldn't generate an answer. Please try again.",
  "chat.error.rateLimited": "Too many questions in a row. Wait a moment and try again.",
  "chat.error.timeout": "The system took too long to answer. Please try again.",
  "chat.error.network": "Couldn't reach the server. Check your connection.",
  "chat.mockNotice": "Demo mode — the backend isn't connected; this is a placeholder answer.",
  "chat.jumpToLatest": "Jump to latest",
  "chat.newAnswer": "New answer",

  // chat: sources
  "chat.sources": "Sources",
  "chat.sourceChip": "{program} p. {page}",
  "chat.sourcesTitle": "Referenced documents",
  "chat.openSources": "Open sources",
  "chat.sourcePage": "Page {page}",
  "chat.sourceExcerpt": "Cited passage",
  "chat.openPdf": "Open PDF page",
  "chat.closePanel": "Close document panel",
  "chat.pdfTitle": "{program} curriculum document",
  "chat.pdfUnavailable": "The PDF isn't available on this server (place the curriculum files in PDF_DIR).",
  "chat.pdfOpenNewTab": "Open in new tab",
  "chat.backToSources": "Back to sources",

  // settings dialog
  "settings.title": "Settings",
  "settings.profile": "Profile",
  "settings.appearance": "Appearance",
  "settings.displayName": "Display name",
  "settings.email": "Email",
  "settings.saveProfile": "Save profile",
  "settings.profileSaved": "Profile saved",
  "settings.guestProfile": "You are using the chat as a guest. History is kept in this browser only. Sign in to set a name and keep your history with your account.",
  "settings.profileDemo": "Demo mode: the name is only stored in this browser",

  // landing page
  "landing.pageTitle": "Home",
  "landing.nav.signIn": "Sign in",
  "landing.nav.openChat": "Open chat",
  "landing.hero.eyebrow": "Faculty of Information Technology, King Mongkut's Institute of Technology Ladkrabang",
  "landing.hero.title": "Ask about IT KMITL programs and get answers that cite the page",
  "landing.hero.subtitle":
    "An assistant that reads the official handbooks of all four B.Sc. programs, answers in Thai or English, and points every sentence back to the page it came from. For high-school students and parents choosing a major.",
  "landing.hero.primary": "Start asking",
  "landing.hero.secondary": "Sign in to save your history",
  "landing.hero.signedIn": "Signed in as {name}",
  "landing.hero.continue": "Continue to chat",
  "landing.toc.title": "Contents",
  "landing.toc.programs": "4 programs",
  "landing.toc.features": "6 points",
  "landing.toc.how": "3 steps",
  "landing.toc.examples": "6 questions",
  "landing.programs.title": "Programs covered",
  "landing.programs.subtitle":
    "All four B.Sc. programs of the faculty. Ask about one, or compare across them.",
  "landing.programs.version.AIT": "New curriculum, B.E. 2566 (2023)",
  "landing.programs.version.DSBA": "Revised curriculum, B.E. 2565 (2022)",
  "landing.programs.version.BIT": "Revised curriculum, B.E. 2565 (2022)",
  "landing.programs.version.IT": "Revised curriculum, B.E. 2565 (2022)",
  "landing.features.title": "What it does",
  "landing.features.grounded.title": "Answers only from the handbooks",
  "landing.features.grounded.body":
    "Nothing is filled in from the model's memory. When the documents don't cover something, it says so instead of guessing.",
  "landing.features.citations.title": "Cites the PDF page",
  "landing.features.citations.body":
    "Every sentence carries a reference number. Click it to open that page of the source document in a side panel.",
  "landing.features.compare.title": "Compares programs side by side",
  "landing.features.compare.body":
    "Ask how DSBA differs from IT and it searches both handbooks and lays the answer out together.",
  "landing.features.scope.title": "Knows what is out of scope",
  "landing.features.scope.body":
    "Off-topic questions, other faculties or other universities get pointed to the right place instead of a made-up answer.",
  "landing.features.bilingual.title": "Replies in the language you ask in",
  "landing.features.bilingual.body":
    "Thai and English are both supported. The interface switches language and light/dark theme too.",
  "landing.features.history.title": "Keeps your conversations",
  "landing.features.history.body":
    "Sign in with Google or email to come back and pick up where you left off.",
  "landing.how.title": "How it works",
  "landing.how.subtitle": "Every step runs on ThaiLLM Thai-language models only, as the competition rules require.",
  "landing.how.step1.title": "Screen the question",
  "landing.how.step1.body":
    "Detect the language, the programs mentioned and the kind of question. Block out-of-scope requests and attempts to override the rules.",
  "landing.how.step1.output": "Thai, program AIT, fact lookup",
  "landing.how.step2.title": "Search the handbooks",
  "landing.how.step2.body":
    "Find the relevant passages across all four handbooks with combined keyword and meaning search, then re-rank them.",
  "landing.how.step2.output": "AIT page 12, page 9, page 3",
  "landing.how.step3.title": "Answer with citations",
  "landing.how.step3.body":
    "Write the answer from those passages alone, stream it word by word, and end every sentence with its page number.",
  "landing.how.step3.output": "120 credits [1] over 4 years [1]",
  "landing.examples.title": "Example questions",
  "landing.examples.subtitle": "Pick any question and it opens the chat with that question typed in for you.",
  "landing.cta.title": "Ready to pick a major?",
  "landing.cta.body": "Sign in and start asking right away.",
  "landing.footer.built": "A ThaiLLM competition project, not an official KMITL service.",
  "landing.footer.stack": "Built with Next.js, FastAPI and models from ThaiLLM.",
  "landing.preview.question": "How many credits is the AIT program?",
  "landing.preview.answer":
    "The Artificial Intelligence Technology (AIT) program requires 120 credits in total [1] over a 4-year study period [1].",
  "landing.preview.source": "AIT page 12, General information",
  "landing.preview.docName": "AIT.pdf",
  "landing.preview.docHeading": "General information",
  "landing.preview.excerpt": "Total credits for the program: 120 credits",
  "landing.preview.excerptLabel": "Cited passage",
  "landing.preview.assistant": "Assistant",
  "landing.preview.you": "You",
};
