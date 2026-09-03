import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/render";
import { dictionaries } from "@/i18n";
import { setDemoUser } from "@/lib/auth/demo";
import { LandingPage } from "./LandingPage";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }),
}));

const th = dictionaries.th;

describe("LandingPage", () => {
  it("shows the pitch, the four programs and a sign-in path when signed out", async () => {
    renderWithProviders(<LandingPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(th["landing.hero.title"]);
    for (const id of ["AIT", "DSBA", "BIT", "IT"]) {
      expect(screen.getByText(id)).toBeInTheDocument();
    }
    // guests go straight to the chat; signing in is offered, not required
    const primary = await screen.findAllByRole("link", { name: th["landing.hero.primary"] });
    expect(primary.length).toBeGreaterThan(0);
    for (const link of primary) expect(link).toHaveAttribute("href", "/chat");
    expect(screen.getByRole("link", { name: th["landing.hero.secondary"] })).toHaveAttribute("href", "/login");
    // an example question opens the chat with itself pre-filled
    expect(screen.getByRole("link", { name: th["chat.example1"] })).toHaveAttribute(
      "href",
      `/chat?q=${encodeURIComponent(th["chat.example1"])}`,
    );
    expect(screen.getByRole("link", { name: th["landing.nav.signIn"] })).toHaveAttribute("href", "/login");
    // table of contents links to every section
    for (const id of ["programs", "features", "how", "examples"]) {
      expect(document.getElementById(id)).not.toBeNull();
    }
  });

  it("points a signed-in user straight at the chat", async () => {
    setDemoUser({ email: "som@kmitl.ac.th", displayName: "Som Chai" });
    renderWithProviders(<LandingPage />);
    const links = await screen.findAllByRole("link", { name: th["landing.hero.continue"] });
    for (const link of links) expect(link).toHaveAttribute("href", "/chat");
    expect(screen.getByText(/Som Chai/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: th["landing.hero.secondary"] })).toBeNull();
  });
});
