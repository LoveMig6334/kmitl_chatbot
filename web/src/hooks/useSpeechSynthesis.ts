"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

/** Read text aloud with the browser's SpeechSynthesis (TTS); no-op where unsupported. */
export function useSpeechSynthesis() {
  const supported = useSyncExternalStore(
    () => () => {},
    () => "speechSynthesis" in window,
    () => false,
  );
  const [speakingId, setSpeakingId] = useState<string | null>(null);

  const cancel = useCallback(() => {
    window.speechSynthesis?.cancel();
    setSpeakingId(null);
  }, []);

  const speak = useCallback(
    (id: string, text: string, lang: string) => {
      if (!("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      const voice = window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith(lang.slice(0, 2)));
      if (voice) utterance.voice = voice;
      utterance.onend = () => setSpeakingId(null);
      utterance.onerror = () => setSpeakingId(null);
      setSpeakingId(id);
      window.speechSynthesis.speak(utterance);
    },
    [],
  );

  useEffect(() => () => window.speechSynthesis?.cancel(), []);

  return { supported, speakingId, speak, cancel };
}
