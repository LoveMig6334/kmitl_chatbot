"use client";

import { memo, useState, type ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";
import { useTranslation } from "@/providers/LocaleProvider";
import { cn } from "@/lib/cn";

const remarkPlugins = [remarkGfm];
const rehypePlugins = [[rehypeHighlight, { detect: false, ignoreMissing: true }] as const];

function Pre({ children, ...props }: ComponentProps<"pre">) {
  const t = useTranslation();
  const [copied, setCopied] = useState(false);
  async function copy(e: React.MouseEvent<HTMLButtonElement>) {
    const code = (e.currentTarget.parentElement?.querySelector("code")?.textContent ?? "").replace(/\n$/, "");
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }
  return (
    <div className="group/code relative">
      <pre {...props}>{children}</pre>
      <button
        type="button"
        onClick={copy}
        aria-label={copied ? t("chat.copied") : t("chat.copyCode")}
        className="focus-ring absolute right-2 top-2 inline-flex h-7 items-center gap-1 rounded-sm border border-border bg-surface px-2 text-xs text-fg-muted opacity-0 transition-opacity hover:text-fg focus-visible:opacity-100 group-hover/code:opacity-100"
      >
        {copied ? <Check className="size-3.5" aria-hidden="true" /> : <Copy className="size-3.5" aria-hidden="true" />}
        {copied ? t("chat.copied") : t("chat.copyCode")}
      </button>
    </div>
  );
}

function Table(props: ComponentProps<"table">) {
  return (
    <div className="overflow-x-auto">
      <table {...props} />
    </div>
  );
}

function Anchor(props: ComponentProps<"a">) {
  return <a {...props} target="_blank" rel="noreferrer noopener" />;
}

const components = { pre: Pre, table: Table, a: Anchor };

/** GitHub-flavoured Markdown (tables, lists, code with copy button) styled by `.markdown` in globals.css. */
export const Markdown = memo(function Markdown({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn("markdown", className)}>
      <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins as never} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
});
