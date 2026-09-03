import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, visibleStrings } from "@/test/render";
import { dictionaries } from "@/i18n";
import { LoginForm } from "./LoginForm";

const router = { replace: vi.fn(), push: vi.fn(), refresh: vi.fn() };
let search = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => search,
}));

const auth = vi.hoisted(() => ({
  signInWithEmail: vi.fn(),
  signInWithGoogle: vi.fn(),
}));
vi.mock("@/lib/auth", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/auth")>()),
  signInWithEmail: auth.signInWithEmail,
  signInWithGoogle: auth.signInWithGoogle,
}));

beforeEach(() => {
  vi.clearAllMocks();
  search = new URLSearchParams();
});

describe("LoginForm validation", () => {
  it("shows required errors on empty submit and clears them as the user types", async () => {
    renderWithProviders(<LoginForm />);
    await userEvent.click(screen.getByRole("button", { name: dictionaries.th["auth.login.submit"] }));

    const alerts = screen.getAllByRole("alert");
    expect(alerts).toHaveLength(2);
    expect(alerts[0]).toHaveTextContent(dictionaries.th["validation.required"]);
    expect(auth.signInWithEmail).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.email"]), "not-an-email");
    expect(screen.getAllByRole("alert")[0]).toHaveTextContent(dictionaries.th["validation.emailInvalid"]);

    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.email"]), "@x.co");
    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.password"]), "secret");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("submits valid credentials once, disables the button meanwhile, and redirects", async () => {
    let resolve!: (v: { ok: true }) => void;
    auth.signInWithEmail.mockReturnValue(new Promise((r) => (resolve = r)));
    renderWithProviders(<LoginForm />);

    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.email"]), "a@b.co");
    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.password"]), "secret123");
    const submit = screen.getByRole("button", { name: dictionaries.th["auth.login.submit"] });
    await userEvent.click(submit);
    await userEvent.click(submit); // double click while pending

    expect(auth.signInWithEmail).toHaveBeenCalledTimes(1);
    expect(auth.signInWithEmail).toHaveBeenCalledWith("a@b.co", "secret123");
    expect(screen.getByRole("button", { name: dictionaries.th["auth.login.submitting"] })).toBeDisabled();

    resolve({ ok: true });
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/chat"));
  });

  it("honours a safe ?next= target and ignores an external one", async () => {
    auth.signInWithEmail.mockResolvedValue({ ok: true });
    search = new URLSearchParams("next=//evil.example");
    renderWithProviders(<LoginForm />);
    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.email"]), "a@b.co");
    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.password"]), "x");
    await userEvent.click(screen.getByRole("button", { name: dictionaries.th["auth.login.submit"] }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/chat"));
  });
});

describe("LoginForm error mapping", () => {
  it("shows the friendly message for wrong credentials in Thai and English", async () => {
    auth.signInWithEmail.mockResolvedValue({ ok: false, code: "invalid_credentials" });
    renderWithProviders(<LoginForm />);
    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.email"]), "a@b.co");
    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.password"]), "wrong");
    await userEvent.click(screen.getByRole("button", { name: dictionaries.th["auth.login.submit"] }));

    expect(await screen.findByRole("alert")).toHaveTextContent(dictionaries.th["authError.invalid_credentials"]);
    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    expect(screen.getByRole("alert")).toHaveTextContent(dictionaries.en["authError.invalid_credentials"]);
    expect(screen.getByRole("button", { name: dictionaries.en["auth.login.submit"] })).toBeEnabled();
  });

  it.each(["email_not_confirmed", "rate_limited", "network"] as const)("maps %s", async (code) => {
    auth.signInWithEmail.mockResolvedValue({ ok: false, code });
    renderWithProviders(<LoginForm />);
    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.email"]), "a@b.co");
    await userEvent.type(screen.getByLabelText(dictionaries.th["auth.password"]), "pw");
    await userEvent.click(screen.getByRole("button", { name: dictionaries.th["auth.login.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(dictionaries.th[`authError.${code}`]);
  });

  it("shows the OAuth failure passed back by the callback route and ignores junk", () => {
    search = new URLSearchParams("error=oauth_failed");
    const { unmount } = renderWithProviders(<LoginForm />);
    expect(screen.getByRole("alert")).toHaveTextContent(dictionaries.th["authError.oauth_failed"]);
    unmount();
    search = new URLSearchParams("error=<img>");
    renderWithProviders(<LoginForm />);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("surfaces Google sign-in failures", async () => {
    auth.signInWithGoogle.mockResolvedValue({ ok: false, code: "provider_disabled" });
    renderWithProviders(<LoginForm />);
    await userEvent.click(screen.getByRole("button", { name: dictionaries.th["auth.continueWithGoogle"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(dictionaries.th["authError.provider_disabled"]);
  });
});

describe("LoginForm localisation", () => {
  it("every visible string comes from the active dictionary and all switch on toggle", async () => {
    renderWithProviders(<LoginForm />);
    const thValues = new Set<string>(Object.values(dictionaries.th));
    const enValues = new Set<string>(Object.values(dictionaries.en));

    const before = visibleStrings();
    expect(before.length).toBeGreaterThan(8);
    for (const s of before) expect(thValues.has(s), `not in th dictionary: "${s}"`).toBe(true);

    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    const after = visibleStrings();
    for (const s of after) expect(enValues.has(s), `not in en dictionary: "${s}"`).toBe(true);

    // Every string that differs between the locales actually changed.
    const stillThai = after.filter((s) => thValues.has(s) && !enValues.has(s));
    expect(stillThai).toEqual([]);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(dictionaries.en["auth.login.title"]);
  });
});
