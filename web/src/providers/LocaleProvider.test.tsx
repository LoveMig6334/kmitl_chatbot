import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { LanguageToggle } from "@/components/LanguageToggle";
import { LOCALE_STORAGE_KEY, useTranslation } from "./LocaleProvider";

function Probe() {
  const t = useTranslation();
  return <output data-testid="probe">{t("theme.dark")}</output>;
}

describe("LocaleProvider", () => {
  it("defaults to Thai and switches to English, persisting the choice", async () => {
    renderWithProviders(
      <>
        <LanguageToggle />
        <Probe />
      </>,
    );
    expect(screen.getByTestId("probe")).toHaveTextContent("มืด");
    expect(document.documentElement.lang).toBe("th");

    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    expect(screen.getByTestId("probe")).toHaveTextContent("Dark");
    expect(document.documentElement.lang).toBe("en");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("en");
  });

  it("restores the stored locale on a fresh mount", () => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, "en");
    renderWithProviders(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("Dark");
  });
});

describe("LocaleProvider cookie mirror", () => {
  it("writes the locale cookie so the server can render lang/title", async () => {
    renderWithProviders(<LanguageToggle />);
    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    expect(document.cookie).toContain("kmitl.locale=en");
  });
});
