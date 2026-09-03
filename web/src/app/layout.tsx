import type { Metadata, Viewport } from "next";
import { Anuphan } from "next/font/google";
import "./globals.css";
import { AppProviders } from "@/providers/AppProviders";
import { themeInitScript } from "@/providers/ThemeProvider";
import { serverLocale } from "@/i18n/server";

// Anuphan ships Thai + Latin in one variable face, so mixed text keeps one rhythm.
const anuphan = Anuphan({
  variable: "--font-anuphan",
  subsets: ["thai", "latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "IT KMITL Chatbot", template: "%s · IT KMITL Chatbot" },
  description:
    "Curriculum assistant for the Faculty of Information Technology, KMITL (AIT, DSBA, BIT, IT).",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const locale = await serverLocale();
  return (
    <html
      lang={locale}
      suppressHydrationWarning
      className={`${anuphan.variable} h-full`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-full bg-bg text-fg">
        <AppProviders initialLocale={locale}>{children}</AppProviders>
      </body>
    </html>
  );
}
