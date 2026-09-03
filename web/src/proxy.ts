import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { decideRedirect } from "@/lib/auth/routes";
import { isLocale, LOCALE_COOKIE } from "@/i18n";

/**
 * Runs before every page render (Next 16 "proxy", formerly middleware):
 *  1. `?lang=th|en` → locale cookie, so the server renders the right <html lang> and title;
 *  2. refreshes the Supabase session cookie and applies the redirect rules in lib/auth/routes.ts.
 * Without Supabase keys (demo mode) every page is public.
 */
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });

  const lang = request.nextUrl.searchParams.get("lang");
  if (isLocale(lang) && request.cookies.get(LOCALE_COOKIE)?.value !== lang) {
    request.cookies.set(LOCALE_COOKIE, lang); // visible to this render
    response = NextResponse.next({ request });
    response.cookies.set(LOCALE_COOKIE, lang, {
      path: "/",
      maxAge: 31536000,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) return response;

  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (cookiesToSet) => {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        const previous = response.cookies.getAll();
        response = NextResponse.next({ request });
        previous.forEach((c) => response.cookies.set(c));
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });

  // getUser() validates the token with Supabase (never trust the cookie alone).
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const target = decideRedirect(request.nextUrl.pathname, Boolean(user));
  if (target) {
    const redirect = NextResponse.redirect(new URL(target, request.url));
    response.cookies.getAll().forEach((c) => redirect.cookies.set(c));
    return redirect;
  }
  return response;
}

export const config = {
  // Pages only: skip API routes, the OAuth callback, Next internals and static assets.
  matcher: [
    "/((?!api/|auth/callback|_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|txt|xml)$).*)",
  ],
};
