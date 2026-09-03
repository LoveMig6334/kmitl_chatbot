"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { EXAMPLE_KEYS } from "@/components/chat/EmptyState";
import { useLocale, useTranslation } from "@/providers/LocaleProvider";
import { useUser } from "@/hooks/useUser";
import { usePageTitle } from "@/hooks/usePageTitle";
import { PROGRAMS } from "@/lib/constants";
import { AFTER_LOGIN_PATH, LOGIN_PATH } from "@/lib/auth/routes";
import type { MessageKey } from "@/i18n";
import { cn } from "@/lib/cn";
import { LandingHeader } from "./LandingHeader";
import { ChatPreview } from "./ChatPreview";
import { SourceReference } from "./SourceReference";

const FEATURES = ["grounded", "citations", "compare", "scope", "bilingual", "history"] as const;
const STEPS = ["step1", "step2", "step3"] as const;
/** The six example questions split over two marquee rows. */
const EXAMPLE_ROWS = [EXAMPLE_KEYS.slice(0, 3), EXAMPLE_KEYS.slice(3)];
/** Each row is repeated so the loop stays full on wide screens; the CSS shifts by one copy. */
const MARQUEE_COPIES = [0, 1, 2];

/** Sections listed in the table of contents; the ids double as anchors. */
const SECTIONS = [
  { id: "programs", count: "landing.toc.programs" },
  { id: "features", count: "landing.toc.features" },
  { id: "how", count: "landing.toc.how" },
  { id: "examples", count: "landing.toc.examples" },
] as const;

/**
 * The landing page is laid out like the documents the bot reads: a headline that
 * carries a live citation marker, a table of contents with dot leaders, ruled tables
 * instead of cards, and the accent colour reserved for citations and the primary action.
 */
export function LandingPage() {
  const t = useTranslation();
  const { locale } = useLocale();
  const { user, loading } = useUser();
  usePageTitle("landing.pageTitle");

  const signedIn = Boolean(user);
  const chatHref = AFTER_LOGIN_PATH; // the chat is open to guests
  const ctaLabel = signedIn ? t("landing.hero.continue") : t("landing.hero.primary");
  const questionHref = (q: string) => `${AFTER_LOGIN_PATH}?q=${encodeURIComponent(q)}`;

  return (
    <div className="flex min-h-dvh flex-col bg-bg text-fg">
      <LandingHeader signedIn={signedIn} />

      <main className="flex-1">
        {/* Hero: headline with a live [1] marker; the mock exchange to the right. */}
        <section className="mx-auto grid w-full max-w-6xl gap-12 px-5 pb-16 pt-14 sm:px-8 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-center lg:gap-16 lg:pb-24 lg:pt-24">
          <div className="flex max-w-2xl flex-col gap-7">
            <p className="text-sm text-fg-muted">{t("landing.hero.eyebrow")}</p>
            <h1 className="text-[2.25rem] font-semibold leading-[1.3] tracking-[-0.02em] text-fg sm:text-[2.75rem] lg:text-[3.25rem] lg:leading-[1.25]">
              {t("landing.hero.title")}
              <SourceReference variant="marker" className="ml-[0.2em]" />
            </h1>
            <p className="max-w-[40rem] text-[1.0625rem] leading-[1.7] text-fg-muted">
              {t("landing.hero.subtitle")}
            </p>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pt-1">
              <Button asChild size="lg">
                <Link href={chatHref}>{ctaLabel}</Link>
              </Button>
              {!signedIn && !loading && (
                <Link
                  href={LOGIN_PATH}
                  className="focus-ring rounded-sm text-base font-medium text-fg underline decoration-border-strong underline-offset-[6px] transition-colors hover:decoration-fg"
                >
                  {t("landing.hero.secondary")}
                </Link>
              )}
              {signedIn && user && (
                <p className="text-sm text-fg-subtle">
                  {t("landing.hero.signedIn", { name: user.displayName || user.email || "" })}
                </p>
              )}
            </div>
          </div>
          <div className="flex justify-center lg:justify-end">
            <ChatPreview />
          </div>
        </section>

        {/* Table of contents: the way every curriculum handbook opens. */}
        <nav aria-label={t("landing.toc.title")} className="border-y border-border bg-bg-subtle">
          <div className="mx-auto grid w-full max-w-6xl gap-6 px-5 py-10 sm:px-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,9fr)] lg:gap-16">
            <h2 className="text-xl font-semibold tracking-tight">{t("landing.toc.title")}</h2>
            <ol className="flex max-w-[40rem] flex-col">
              {SECTIONS.map(({ id, count }) => (
                <li key={id}>
                  <a
                    href={`#${id}`}
                    className="focus-ring group flex items-baseline gap-3 rounded-sm py-2.5 text-base text-fg transition-colors hover:text-accent"
                  >
                    <span className="shrink-0">{t(`landing.${id}.title` as MessageKey)}</span>
                    <span
                      aria-hidden="true"
                      className="mb-[0.35em] min-w-6 flex-1 border-b border-dotted border-border-strong"
                    />
                    <span className="shrink-0 text-sm text-fg-muted">{t(count)}</span>
                  </a>
                </li>
              ))}
            </ol>
          </div>
        </nav>

        {/* Programs: four boxes under a centred heading. */}
        <Section
          id="programs"
          title={t("landing.programs.title")}
          subtitle={t("landing.programs.subtitle")}
          centered
        >
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PROGRAMS.map((p) => (
              <li
                key={p.id}
                className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-6 transition-colors hover:border-border-strong"
              >
                <span className="text-3xl font-semibold tracking-tight text-fg">{p.id}</span>
                <div className="flex flex-col gap-1">
                  <p className="text-base font-medium leading-snug text-fg">{locale === "th" ? p.th : p.en}</p>
                  <p className="text-sm text-fg-muted">{locale === "th" ? p.en : p.th}</p>
                </div>
                <p className="mt-auto pt-3 text-sm text-fg-muted">
                  {t(`landing.programs.version.${p.id}` as MessageKey)}
                </p>
              </li>
            ))}
          </ul>
        </Section>

        {/* Features: two columns of prose, no cards, no icons. */}
        <Section id="features" title={t("landing.features.title")} tinted>
          <dl className="grid gap-x-12 gap-y-9 sm:grid-cols-2">
            {FEATURES.map((key) => (
              <div key={key} className="flex max-w-[26rem] flex-col gap-1.5">
                <dt className="text-lg font-semibold leading-snug text-fg">
                  {t(`landing.features.${key}.title` as MessageKey)}
                </dt>
                <dd className="text-base leading-[1.7] text-fg-muted">
                  {t(`landing.features.${key}.body` as MessageKey)}
                </dd>
              </div>
            ))}
          </dl>
        </Section>

        {/* How it works: a real sequence, so it is numbered; each step shows its output. */}
        <Section id="how" title={t("landing.how.title")} subtitle={t("landing.how.subtitle")}>
          <ol className="grid gap-10 lg:grid-cols-3 lg:gap-8">
            {STEPS.map((step, i) => (
              <li key={step} className="relative flex flex-col gap-3 border-t-2 border-fg pt-5">
                <span className="text-sm text-fg-muted">{i + 1}</span>
                <h3 className="text-xl font-semibold tracking-tight text-fg">
                  {t(`landing.how.${step}.title` as MessageKey)}
                </h3>
                <p className="text-base leading-[1.7] text-fg-muted">{t(`landing.how.${step}.body` as MessageKey)}</p>
                <p className="mt-auto w-fit rounded-md bg-bg-subtle px-3 py-1.5 text-sm text-fg">
                  {t(`landing.how.${step}.output` as MessageKey)}
                </p>
              </li>
            ))}
          </ol>
        </Section>

        {/* Examples: two drifting rows; each question opens the chat with itself typed in. */}
        <Section id="examples" title={t("landing.examples.title")} subtitle={t("landing.examples.subtitle")} tinted centered>
          <div className="flex flex-col gap-3">
            {EXAMPLE_ROWS.map((row, r) => (
              <div key={r} className="marquee">
                <ul
                  className="marquee-track"
                  data-reverse={r % 2 === 1 || undefined}
                  style={{ ["--marquee-duration" as string]: `${36 + r * 8}s` }}
                >
                  {MARQUEE_COPIES.map((copy) =>
                    row.map((key) => (
                      <li key={`${copy}-${key}`} aria-hidden={copy > 0 || undefined}>
                        <Link
                          href={questionHref(t(key))}
                          tabIndex={copy > 0 ? -1 : undefined}
                          className="focus-ring block whitespace-nowrap rounded-full border border-border bg-surface px-5 py-2.5 text-base text-fg transition-colors hover:border-accent hover:text-accent"
                        >
                          {t(key)}
                        </Link>
                      </li>
                    )),
                  )}
                </ul>
              </div>
            ))}
          </div>
        </Section>

        {/* Closing line, not a banner. */}
        <section className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-5 py-16 sm:flex-row sm:items-end sm:justify-between sm:px-8 lg:py-24">
          <div className="flex flex-col gap-2">
            <h2 className="text-[2rem] font-semibold leading-[1.3] tracking-[-0.02em] text-fg">{t("landing.cta.title")}</h2>
            <p className="text-base text-fg-muted">{t("landing.cta.body")}</p>
          </div>
          <Button asChild size="lg">
            <Link href={chatHref}>{ctaLabel}</Link>
          </Button>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-1 px-5 py-6 text-sm text-fg-muted sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p>{t("landing.footer.built")}</p>
          <p className="text-fg-subtle">{t("landing.footer.stack")}</p>
        </div>
      </footer>
    </div>
  );
}

/**
 * Section frame. Default: title column on the left, content on the right, ruled like a
 * document. `centered`: title stacked above the content and centred.
 */
function Section({
  id,
  title,
  subtitle,
  tinted = false,
  centered = false,
  children,
}: {
  id: string;
  title: string;
  subtitle?: string;
  tinted?: boolean;
  centered?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className={cn("scroll-mt-6 border-b border-border", tinted && "bg-bg-subtle")}>
      <div
        className={cn(
          "mx-auto grid w-full max-w-6xl gap-8 px-5 py-14 sm:px-8 lg:py-20",
          centered ? "gap-10" : "lg:grid-cols-[minmax(0,3fr)_minmax(0,9fr)] lg:gap-16",
        )}
      >
        <div
          className={cn(
            "flex flex-col gap-3",
            centered ? "items-center text-center" : "lg:sticky lg:top-8 lg:self-start",
          )}
        >
          <h2 className="text-[1.75rem] font-semibold leading-[1.3] tracking-[-0.02em] text-fg">{title}</h2>
          {subtitle && <p className="max-w-[28rem] text-base leading-[1.7] text-fg-muted">{subtitle}</p>}
        </div>
        <div className="min-w-0">{children}</div>
      </div>
    </section>
  );
}
