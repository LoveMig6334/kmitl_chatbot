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
  "chat.example5": "What is the tuition for each program?",
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
  "settings.profileDemo": "Demo mode: the name is only stored in this browser",
};
