"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, Mic, Square } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Tooltip } from "@/components/ui/Tooltip";
import { useLocale } from "@/providers/LocaleProvider";
import { useGhostText, localGhostTextProvider } from "@/hooks/useGhostText";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import type { ProgramId } from "@/lib/constants";
import { cn } from "@/lib/cn";
import { ScopePicker } from "./ScopePicker";
import { EXAMPLE_KEYS } from "./EmptyState";

export interface ComposerProps {
  onSend: (text: string) => void;
  onStop: () => void;
  generating: boolean;
  scope: ProgramId[];
  onScopeChange: (scope: ProgramId[]) => void;
  /** The user's previous questions — ghost-text candidates. */
  pastQuestions: readonly string[];
  /** Externally injected text (example question click). */
  seed?: { text: string; nonce: number } | null;
}

const MAX_ROWS_PX = 200;

export function Composer({ onSend, onStop, generating, scope, onScopeChange, pastQuestions, seed }: ComposerProps) {
  const { locale, t } = useLocale();
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const candidates = useMemo(() => [...pastQuestions, ...EXAMPLE_KEYS.map((k) => t(k))], [pastQuestions, t]);
  const provider = useMemo(() => localGhostTextProvider(() => candidates), [candidates]);
  const ghost = useGhostText({ text, enabled: !generating && !text.includes("\n"), provider });

  const speech = useSpeechRecognition({
    lang: locale === "th" ? "th-TH" : "en-US",
    onFinal: (segment) => setText((prev) => (prev.trim() ? `${prev.trimEnd()} ${segment}` : segment)),
  });

  // An example-question click seeds the composer (derived-state pattern: no effect needed).
  const [appliedSeed, setAppliedSeed] = useState(seed);
  if (seed !== appliedSeed) {
    setAppliedSeed(seed);
    if (seed) setText(seed.text);
  }
  useEffect(() => {
    if (seed) textareaRef.current?.focus();
  }, [seed]);

  // auto-grow
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    // +1 absorbs sub-pixel rounding of scrollHeight (fractional line-height) that would
    // otherwise leave a hairline overflow and show a scrollbar on an empty textarea.
    const needed = el.scrollHeight + 1;
    el.style.height = `${Math.min(needed, MAX_ROWS_PX)}px`;
    el.style.overflowY = needed > MAX_ROWS_PX ? "auto" : "hidden";
  }, [text, speech.interim]);

  const submit = useCallback(() => {
    const value = text.trim();
    if (!value || generating) return;
    ghost.dismiss();
    if (speech.listening) speech.stop();
    setText("");
    onSend(value);
  }, [text, generating, ghost, speech, onSend]);

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Tab" && ghost.suggestion && !e.shiftKey) {
      e.preventDefault();
      setText(ghost.accept());
      return;
    }
    if (e.key === "Escape") {
      if (generating) onStop();
      else ghost.dismiss();
      return;
    }
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
      return;
    }
    if (ghost.suggestion && !["Shift", "Control", "Alt", "Meta"].includes(e.key)) ghost.dismiss();
  }

  const display = speech.interim ? `${text}${text && !text.endsWith(" ") ? " " : ""}${speech.interim}` : text;
  const micError = speech.error === "unsupported" ? t("chat.micUnsupported") : speech.error === "denied" ? t("chat.micDenied") : null;

  return (
    <div className="flex flex-col gap-2">
      <div
        className={cn(
          "relative flex flex-col rounded-2xl border border-border bg-surface shadow-sm transition-colors",
          "focus-within:border-border-strong focus-within:ring-2 focus-within:ring-ring/30",
        )}
      >
        <div className="relative">
          {/* ghost text overlay: identical metrics to the textarea, only the suffix is visible */}
          {ghost.suggestion && !speech.interim && (
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 overflow-hidden whitespace-pre-wrap break-words px-4 pt-3.5 text-base leading-[1.65] sm:text-sm sm:leading-[1.6]"
            >
              <span className="invisible">{text}</span>
              <span className="text-fg-subtle">{ghost.suggestion}</span>
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={display}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={speech.listening ? t("chat.micListening") : t("chat.placeholder")}
            rows={1}
            aria-label={t("chat.placeholder")}
            aria-describedby={ghost.suggestion ? "ghost-hint" : undefined}
            enterKeyHint="send"
            className="relative w-full resize-none bg-transparent px-4 pt-3.5 pb-1 text-base leading-[1.65] text-fg outline-none placeholder:text-fg-subtle sm:text-sm sm:leading-[1.6]"
          />
        </div>
        <div className="flex items-center justify-between gap-2 px-2 pb-2">
          <div className="flex min-w-0 items-center gap-1">
            <ScopePicker scope={scope} onChange={onScopeChange} />
            {ghost.suggestion && (
              <span id="ghost-hint" className="hidden truncate text-xs text-fg-subtle sm:inline">
                {t("chat.ghostHint")}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Tooltip content={speech.listening ? t("chat.micStop") : t("chat.mic")}>
              <Button
                variant="ghost"
                size="icon"
                onClick={speech.toggle}
                aria-label={speech.listening ? t("chat.micStop") : t("chat.mic")}
                aria-pressed={speech.listening}
                disabled={!speech.supported && speech.error === "unsupported"}
                className={cn("size-8", speech.listening && "animate-pulse bg-accent-soft text-accent")}
              >
                <Mic className="size-4" />
              </Button>
            </Tooltip>
            {generating ? (
              <Tooltip content={t("chat.stop")}>
                <Button variant="secondary" size="icon" onClick={onStop} aria-label={t("chat.stop")} className="size-8 rounded-full">
                  <Square className="size-3.5 fill-current" />
                </Button>
              </Tooltip>
            ) : (
              <Tooltip content={t("chat.send")}>
                <Button size="icon" onClick={submit} disabled={!text.trim()} aria-label={t("chat.send")} className="size-8 rounded-full">
                  <ArrowUp className="size-4" />
                </Button>
              </Tooltip>
            )}
          </div>
        </div>
      </div>
      {micError && (
        <p role="alert" className="px-1 text-xs text-danger">
          {micError}
        </p>
      )}
      <p className="px-1 text-center text-xs text-fg-subtle">{t("chat.disclaimer")}</p>
    </div>
  );
}
