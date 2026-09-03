import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { dictionaries } from "@/i18n";
import { ForgotPasswordForm } from "./ForgotPasswordForm";
import { UpdatePasswordForm } from "./UpdatePasswordForm";

const router = { replace: vi.fn(), push: vi.fn(), refresh: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router, useSearchParams: () => new URLSearchParams() }));

const auth = vi.hoisted(() => ({
  requestPasswordReset: vi.fn(),
  updatePassword: vi.fn(),
  hasSession: vi.fn(),
}));
vi.mock("@/lib/auth", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/auth")>()),
  ...auth,
}));

const th = dictionaries.th;

beforeEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

describe("ForgotPasswordForm", () => {
  it("validates the email, then shows the sent state with the address", async () => {
    auth.requestPasswordReset.mockResolvedValue({ ok: true });
    renderWithProviders(<ForgotPasswordForm />);
    await userEvent.click(screen.getByRole("button", { name: th["auth.forgot.submit"] }));
    expect(screen.getByRole("alert")).toHaveTextContent(th["validation.required"]);
    await waitFor(() => expect(screen.getByLabelText(th["auth.email"])).toHaveFocus());

    await userEvent.type(screen.getByLabelText(th["auth.email"]), "som@kmitl.ac.th");
    await userEvent.click(screen.getByRole("button", { name: th["auth.forgot.submit"] }));
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(th["auth.forgot.sentTitle"]);
    expect(screen.getByText(/som@kmitl\.ac\.th/)).toBeInTheDocument();
    expect(auth.requestPasswordReset).toHaveBeenCalledWith("som@kmitl.ac.th");
  });

  it("shows a mapped error and keeps the form", async () => {
    auth.requestPasswordReset.mockResolvedValue({ ok: false, code: "rate_limited" });
    renderWithProviders(<ForgotPasswordForm />);
    await userEvent.type(screen.getByLabelText(th["auth.email"]), "som@kmitl.ac.th");
    await userEvent.click(screen.getByRole("button", { name: th["auth.forgot.submit"] }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(th["authError.rate_limited"]);
    expect(screen.getByRole("button", { name: th["auth.forgot.submit"] })).toBeEnabled();
  });
});

describe("UpdatePasswordForm", () => {
  it("shows the invalid-link state without a recovery session", async () => {
    auth.hasSession.mockResolvedValue(false);
    renderWithProviders(<UpdatePasswordForm />);
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(th["auth.update.noSessionTitle"]);
    expect(screen.getByRole("link", { name: th["auth.update.requestAgain"] })).toHaveAttribute("href", "/forgot-password");
  });

  it("with a session: validates, saves, shows success and redirects", async () => {
    auth.hasSession.mockResolvedValue(true);
    auth.updatePassword.mockResolvedValue({ ok: true });
    renderWithProviders(<UpdatePasswordForm />);
    const submit = await screen.findByRole("button", { name: th["auth.update.submit"] });
    await userEvent.click(submit);
    expect(screen.getAllByRole("alert")).toHaveLength(2);

    await userEvent.type(screen.getByLabelText(th["auth.update.newPassword"]), "abcdefgh1");
    await userEvent.type(screen.getByLabelText(th["auth.confirmPassword"]), "abcdefgh1");
    await userEvent.click(submit);
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(th["auth.update.successTitle"]);
    expect(auth.updatePassword).toHaveBeenCalledWith("abcdefgh1");
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/chat"), { timeout: 3000 });
  });

  it("maps same_password", async () => {
    auth.hasSession.mockResolvedValue(true);
    auth.updatePassword.mockResolvedValue({ ok: false, code: "same_password" });
    renderWithProviders(<UpdatePasswordForm />);
    await screen.findByRole("button", { name: th["auth.update.submit"] });
    await userEvent.type(screen.getByLabelText(th["auth.update.newPassword"]), "abcdefgh1");
    await userEvent.type(screen.getByLabelText(th["auth.confirmPassword"]), "abcdefgh1");
    await userEvent.click(screen.getByRole("button", { name: th["auth.update.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(th["authError.same_password"]);
  });
});
