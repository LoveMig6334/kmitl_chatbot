"use client";

import { useCallback, useMemo, useState } from "react";
import type { FieldErrors } from "@/lib/auth/validation";

/**
 * Minimal form state: values + validate-on-submit, with errors re-evaluated on every
 * change once the user has tried to submit (so they disappear as fields become valid).
 */
export function useFormState<V extends Record<string, string>>(
  initial: V,
  validate: (values: V) => FieldErrors<Extract<keyof V, string>>,
) {
  const [values, setValues] = useState<V>(initial);
  const [submitted, setSubmitted] = useState(false);

  const errors = useMemo(
    () => (submitted ? validate(values) : ({} as FieldErrors<Extract<keyof V, string>>)),
    [submitted, validate, values],
  );

  const set = useCallback(
    (field: keyof V) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const next = event.target.value;
      setValues((v) => ({ ...v, [field]: next }));
    },
    [],
  );

  /**
   * Marks the form as submitted and returns whether it is valid right now.
   * When invalid, focuses the first field that carries an error (after React paints it).
   */
  const check = useCallback(
    (form?: HTMLFormElement | null) => {
      setSubmitted(true);
      const invalid = Object.keys(validate(values));
      if (invalid.length > 0 && form) {
        window.requestAnimationFrame(() => {
          const el = form.querySelector<HTMLElement>(`[name="${invalid[0]}"]`);
          el?.focus();
        });
      }
      return invalid.length === 0;
    },
    [validate, values],
  );

  return { values, errors, set, check, setValues };
}
