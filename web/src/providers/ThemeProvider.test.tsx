import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { ThemeToggle } from "@/components/ThemeToggle";
import { THEME_STORAGE_KEY, themeInitScript, useTheme } from "./ThemeProvider";

function Probe() {
  const { theme, resolvedTheme } = useTheme();
  return <output data-testid="probe">{`${theme}/${resolvedTheme}`}</output>;
}

describe("ThemeProvider", () => {
  it("defaults to system (light in jsdom) and toggles to dark", async () => {
    renderWithProviders(
      <>
        <ThemeToggle />
        <Probe />
      </>,
    );
    expect(screen.getByTestId("probe")).toHaveTextContent("system/light");
    expect(document.documentElement).not.toHaveClass("dark");

    await userEvent.click(screen.getByRole("button", { name: /สลับธีม/ }));
    expect(screen.getByTestId("probe")).toHaveTextContent("dark/dark");
    expect(document.documentElement).toHaveClass("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("persists across a reload (fresh mount reads localStorage)", async () => {
    const first = renderWithProviders(<ThemeToggle />);
    await userEvent.click(screen.getByRole("button"));
    first.unmount();

    renderWithProviders(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("dark/dark");
    expect(document.documentElement).toHaveClass("dark");
  });

  it("the head init script applies the stored theme before React runs", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    document.documentElement.classList.remove("dark");
    new Function(themeInitScript)();
    expect(document.documentElement).toHaveClass("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");

    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    new Function(themeInitScript)();
    expect(document.documentElement).not.toHaveClass("dark");

    window.localStorage.removeItem(THEME_STORAGE_KEY); // system → jsdom matchMedia says light
    new Function(themeInitScript)();
    expect(document.documentElement).not.toHaveClass("dark");
  });
});
