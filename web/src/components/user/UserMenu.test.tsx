import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { dictionaries } from "@/i18n";
import { setDemoUser } from "@/lib/auth/demo";
import { UserMenu } from "./UserMenu";

const router = { replace: vi.fn(), push: vi.fn(), refresh: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const auth = vi.hoisted(() => ({ signOut: vi.fn() }));
vi.mock("@/lib/auth", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/auth")>()),
  signOut: auth.signOut,
}));

const th = dictionaries.th;

beforeEach(() => {
  vi.clearAllMocks();
  setDemoUser({ email: "som@kmitl.ac.th", displayName: "Som Chai" });
});

describe("UserMenu (demo mode)", () => {
  it("shows the user's initials and name, and opens with the keyboard", async () => {
    renderWithProviders(<UserMenu />);
    const trigger = await screen.findByRole("button", { name: th["user.menu"] });
    expect(trigger).toHaveTextContent("SC");
    expect(trigger).toHaveTextContent("Som Chai");

    trigger.focus();
    await userEvent.keyboard("{Enter}");
    const menu = await screen.findByRole("menu");
    expect(menu).toHaveTextContent("som@kmitl.ac.th");
    expect(menu).toHaveTextContent(th["user.demoBadge"]);
    expect(screen.getAllByRole("menuitemradio")).toHaveLength(5); // 3 themes + 2 locales
  });

  it("switches theme and language from the menu", async () => {
    renderWithProviders(<UserMenu />);
    await userEvent.click(await screen.findByRole("button", { name: th["user.menu"] }));
    await userEvent.click(screen.getByRole("menuitemradio", { name: th["theme.dark"] }));
    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem("kmitl.theme")).toBe("dark");

    await userEvent.click(screen.getByRole("button", { name: th["user.menu"] }));
    await userEvent.click(screen.getByRole("menuitemradio", { name: "English" }));
    expect(screen.getByRole("button", { name: dictionaries.en["user.menu"] })).toBeInTheDocument();
  });

  it("signs out and returns to /login", async () => {
    auth.signOut.mockResolvedValue({ ok: true });
    renderWithProviders(<UserMenu />);
    await userEvent.click(await screen.findByRole("button", { name: th["user.menu"] }));
    await userEvent.click(screen.getByRole("menuitem", { name: th["user.signOut"] }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
    expect(auth.signOut).toHaveBeenCalledTimes(1);
  });
});
