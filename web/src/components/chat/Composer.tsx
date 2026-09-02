"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, MicOff, Send, Square } from "lucide-react";
import { useT } from "@/hooks/useT";
import { useAppStore } from "@/lib/store";
import { GHOST_PROMPTS } from "@/lib/constants";
import { FacultyScope } from "./FacultyScope";

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  generating: boolean;
}

interface VoiceRecognition {
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: (e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void;
  onend: () => void;
}

export function Composer({ onSend, onStop, generating }: Props) {
  const t = useT();
  const locale = useAppStore((s) => s.locale);
  const [text, setText] = useState("");
  const [ghostIndex, setGhostIndex] = useState(0);
  const [listening, setListening] = useState(false);
  const [notice, setNotice] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const recogRef = useRef<{ stop: () => void } | null>(null);

  // Rotate ghost suggestions
  useEffect(() => {
    let mounted = true;
    const cycle = () => {
      if (!mounted) return;
      setGhostIndex((i) => (i + 1) % GHOST_PROMPTS.length);
    };
    const id = setInterval(cycle, 4000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  function submit() {
    const v = text.trim();
    if (!v || generating) return;
    setText("");
    onSend(v);
  }

  function toggleVoice() {
    const w = window as unknown as {
      SpeechRecognition?: new () => VoiceRecognition;
      webkitSpeechRecognition?: new () => VoiceRecognition;
    };
    const SR = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SR) {
      setNotice("Voice input not supported in this browser");
      return;
    }
    if (listening) {
      recogRef.current?.stop();
      setListening(false);
      return;
    }
    setNotice("");
    const recog = new SR();
    recog.lang = locale === "th" ? "th-TH" : "en-US";
    recog.onresult = (e) => {
      const transcript = Array.from(e.results)
        .map((r) => r[0].transcript)
        .join("");
      setText((prev) => (prev ? prev + " " : "") + transcript);
    };
    recog.onend = () => setListening(false);
    recogRef.current = recog;
    recog.start();
    setListening(true);
  }

  return (
    <div className="flex flex-col gap-2">
      <FacultyScope />
      {notice && <p className="px-1 text-xs text-red-500">{notice}</p>}
      <div className="rounded-2xl border border-border bg-surface p-2 focus-within:ring-2 focus-within:ring-accent/40">
        <textarea
          ref={ref}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={generating ? "" : GHOST_PROMPTS[ghostIndex]}
          rows={2}
          className="w-full resize-none bg-transparent px-2 py-1.5 text-sm text-foreground outline-none placeholder:text-muted/60"
        />
        <div className="flex items-center justify-between gap-2 px-1 py-1">
          <button
            onClick={toggleVoice}
            title={listening ? t.voiceOn : t.voiceOff}
            className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
              listening
                ? "animate-pulse bg-accent text-accent-foreground"
                : "text-muted hover:bg-surface-muted hover:text-foreground"
            }`}
          >
            {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </button>
          <div className="flex items-center gap-2">
            {generating && (
              <button
                onClick={onStop}
                title={t.stop}
                className="flex h-9 items-center gap-1.5 rounded-full bg-red-500 px-4 text-sm font-medium text-white transition-colors hover:bg-red-600"
              >
                <Square className="h-3.5 w-3.5 fill-current" />
                {t.stop}
              </button>
            )}
            <button
              onClick={submit}
              disabled={!text.trim() || generating}
              title={t.send}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-accent-foreground transition-colors hover:bg-accent-strong disabled:opacity-40"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
