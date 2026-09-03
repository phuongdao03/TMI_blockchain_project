"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type ThemePreference = "light" | "dark" | "system";

const storageKey = "thv-theme";
const darkScheme = "(prefers-color-scheme: dark)";
const themeChangeEvent = "thv-theme-change";

function preferredDarkMode() {
  return typeof window.matchMedia === "function"
    ? window.matchMedia(darkScheme).matches
    : false;
}

function isThemePreference(value: string | null): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

function applyTheme(preference: ThemePreference) {
  const resolved =
    preference === "system"
      ? preferredDarkMode()
        ? "dark"
        : "light"
      : preference;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.dataset.themePreference = preference;
}

export function ThemeToggle() {
  const [preference, setPreference] = useState<ThemePreference>("system");
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(storageKey);
    const initial = isThemePreference(stored) ? stored : "system";
    applyTheme(initial);
    queueMicrotask(() => {
      setPreference(initial);
      setIsReady(true);
    });

    const media =
      typeof window.matchMedia === "function"
        ? window.matchMedia(darkScheme)
        : null;
    const syncSystemTheme = () => {
      if ((localStorage.getItem(storageKey) ?? "system") === "system") {
        applyTheme("system");
      }
    };
    const syncThemeControls = (event: Event) => {
      const nextPreference = (event as CustomEvent<ThemePreference>).detail;
      if (isThemePreference(nextPreference)) {
        setPreference(nextPreference);
      }
    };
    media?.addEventListener("change", syncSystemTheme);
    window.addEventListener(themeChangeEvent, syncThemeControls);
    return () => {
      media?.removeEventListener("change", syncSystemTheme);
      window.removeEventListener(themeChangeEvent, syncThemeControls);
    };
  }, []);

  const options = [
    { value: "system" as const, label: "Theo thiết bị", icon: Monitor },
    { value: "light" as const, label: "Giao diện sáng", icon: Sun },
    { value: "dark" as const, label: "Giao diện tối", icon: Moon },
  ];

  return (
    <div aria-label="Chọn giao diện" className="theme-toggle" role="group">
      {options.map(({ icon: Icon, label, value }) => (
        <button
          aria-pressed={preference === value}
          className="theme-toggle-option"
          disabled={!isReady}
          key={value}
          onClick={() => {
            setPreference(value);
            localStorage.setItem(storageKey, value);
            applyTheme(value);
            window.dispatchEvent(
              new CustomEvent<ThemePreference>(themeChangeEvent, {
                detail: value,
              }),
            );
          }}
          title={label}
          type="button"
        >
          <Icon aria-hidden="true" className="size-4" />
          <span className="sr-only">{label}</span>
        </button>
      ))}
    </div>
  );
}
