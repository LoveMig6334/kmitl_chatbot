import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, visibleStrings } from "@/test/render";
import { dictionaries } from "@/i18n";
import { RegisterForm } from "./RegisterForm";

const router = { replace: vi.fn(), push: vi.fn(), refresh: vi.fn() };
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
}));

const auth = vi.hoisted(() => ({ signUpWithEmail: vi.fn(), signInWithGoogle: vi.fn() }));
vi.mock("@/lib/auth", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/auth")>()),
  signUpWithEmail: auth.signUpWithEmail,
  signInWithGoogle: auth.signInWithGoogle,
}));

const th = dictionaries.th;

async function fill(values: { name?: string; email?: string; password?: string; confirm?: string }) {
  if (values.name) await userEvent.type(screen.getByLabelText(th["auth.displayName"]), values.name);
  if (values.email) await userEvent.type(screen.getByLabelText(th["auth.email"]), values.email);
  if (values.password) await userEvent.type(screen.getByLabelText(th["auth.password"]), values.password);
  if (values.confirm) await userEvent.type(screen.getByLabelText(th["auth.confirmPassword"]), values.confirm);
}

beforeEach(() => vi.clearAllMocks());

describe("RegisterForm", () => {
  it("validates every field and shows the password requirements live", async () => {
    renderWithProviders(<RegisterForm />);
    await userEvent.click(screen.getByRole("button", { name: th["auth.register.submit"] }));
    expect(screen.getAllByRole("alert")).toHaveLength(4);
    expect(auth.signUpWithEmail).not.toHaveBeenCalled();

    const list = screen.getByRole("list", { name: th["auth.pw.title"] });
    expect(within(list).getAllByRole("listitem").map((li) => li.dataset.ok)).toEqual(["false", "false", "false"]);

    await fill({ name: "Som", email: "a@b.co", password: "abc" });
    expect(within(list).getAllByRole("listitem").map((li) => li.dataset.ok)).toEqual(["false", "true", "false"]);
    expect(screen.getByLabelText(th["auth.password"])).toHaveAccessibleDescription(
      expect.stringContaining(th["validation.passwordTooShort"]),
    );

    await fill({ password: "defgh1" }); // now "abcdefgh1"
    expect(within(list).getAllByRole("listitem").map((li) => li.dataset.ok)).toEqual(["true", "true", "true"]);
    expect(screen.getByText(th["auth.pw.strength.fair"])).toBeInTheDocument();

    await fill({ confirm: "abcdefgh2" });
    expect(screen.getByRole("alert")).toHaveTextContent(th["validation.passwordMismatch"]);
    await userEvent.clear(screen.getByLabelText(th["auth.confirmPassword"]));
    await fill({ confirm: "abcdefgh1" });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("show/hide password toggles the input type", async () => {
    renderWithProviders(<RegisterForm />);
    const pw = screen.getByLabelText(th["auth.password"]);
    expect(pw).toHaveAttribute("type", "password");
    await userEvent.click(screen.getAllByRole("button", { name: th["common.showPassword"] })[0]);
    expect(pw).toHaveAttribute("type", "text");
  });

  it("shows the check-your-email state when confirmation is required", async () => {
    auth.signUpWithEmail.mockResolvedValue({ ok: true, needsConfirmation: true });
    renderWithProviders(<RegisterForm />);
    await fill({ name: "Som", email: "som@kmitl.ac.th", password: "abcdefgh1", confirm: "abcdefgh1" });
    await userEvent.click(screen.getByRole("button", { name: th["auth.register.submit"] }));

    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(th["auth.register.checkEmailTitle"]);
    expect(screen.getByText(/som@kmitl\.ac\.th/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: th["auth.register.goToLogin"] })).toHaveAttribute("href", "/login");
    expect(auth.signUpWithEmail).toHaveBeenCalledWith("Som", "som@kmitl.ac.th", "abcdefgh1");
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("redirects to the chat when no confirmation is needed", async () => {
    auth.signUpWithEmail.mockResolvedValue({ ok: true, needsConfirmation: false });
    renderWithProviders(<RegisterForm />);
    await fill({ name: "Som", email: "a@b.co", password: "abcdefgh1", confirm: "abcdefgh1" });
    await userEvent.click(screen.getByRole("button", { name: th["auth.register.submit"] }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/chat"));
  });

  it("maps an existing-account error", async () => {
    auth.signUpWithEmail.mockResolvedValue({ ok: false, code: "user_exists" });
    renderWithProviders(<RegisterForm />);
    await fill({ name: "Som", email: "a@b.co", password: "abcdefgh1", confirm: "abcdefgh1" });
    await userEvent.click(screen.getByRole("button", { name: th["auth.register.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(th["authError.user_exists"]);
  });

  it("switches every visible string between th and en", async () => {
    renderWithProviders(<RegisterForm />);
    const thValues = new Set<string>(Object.values(dictionaries.th));
    const enValues = new Set<string>(Object.values(dictionaries.en));
    for (const s of visibleStrings()) expect(thValues.has(s), `not in th: "${s}"`).toBe(true);

    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    const after = visibleStrings();
    for (const s of after) expect(enValues.has(s), `not in en: "${s}"`).toBe(true);
    expect(after.filter((s) => thValues.has(s) && !enValues.has(s))).toEqual([]);
  });
});
