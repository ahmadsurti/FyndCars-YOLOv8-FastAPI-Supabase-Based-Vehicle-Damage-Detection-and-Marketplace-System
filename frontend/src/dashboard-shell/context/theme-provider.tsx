import * as React from "react"
import { getCookie, setCookie, removeCookie } from "../lib/cookies"

/* ── Types ──────────────────────────────────────────────────── */
export type Theme = "dark" | "light" | "system"
export type ColorTheme = "blue" | "green" | "parchment"
export type ResolvedTheme = "dark" | "light"

const COLOR_THEME_MODES: Record<ColorTheme, ReadonlyArray<ResolvedTheme>> = {
  blue: ["light", "dark"],
  green: ["light", "dark"],
  parchment: ["light", "dark"],
}

/* ── Cookie keys ────────────────────────────────────────────── */
const THEME_COOKIE = "app-ui-theme"
const COLOR_THEME_COOKIE = "app-color-theme"
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365 // 1 year

const DEFAULT_THEME: Theme = "system"
const DEFAULT_COLOR_THEME: ColorTheme = "blue"

/* ── Context shape ──────────────────────────────────────────── */
export type ThemeProviderState = {
  theme: Theme
  resolvedTheme: ResolvedTheme
  setTheme: (t: Theme) => void
  resetTheme: () => void
  defaultTheme: Theme

  colorTheme: ColorTheme
  setColorTheme: (c: ColorTheme) => void
  resetColorTheme: () => void
  defaultColorTheme: ColorTheme

  modeSupported: (mode: ResolvedTheme) => boolean
}

const ThemeContext = React.createContext<ThemeProviderState>({
  theme: DEFAULT_THEME,
  resolvedTheme: "light",
  setTheme: () => null,
  resetTheme: () => null,
  defaultTheme: DEFAULT_THEME,
  colorTheme: DEFAULT_COLOR_THEME,
  setColorTheme: () => null,
  resetColorTheme: () => null,
  defaultColorTheme: DEFAULT_COLOR_THEME,
  modeSupported: () => true,
})

/* ── Provider ───────────────────────────────────────────────── */
export function ThemeProvider({
  children,
  defaultTheme = DEFAULT_THEME,
  defaultColorTheme = DEFAULT_COLOR_THEME,
}: {
  children: React.ReactNode
  defaultTheme?: Theme
  defaultColorTheme?: ColorTheme
}) {
  const [theme, _setTheme] = React.useState<Theme>(
    () => (getCookie(THEME_COOKIE) as Theme) || defaultTheme,
  )
  const [colorTheme, _setColorTheme] = React.useState<ColorTheme>(
    () => (getCookie(COLOR_THEME_COOKIE) as ColorTheme) || defaultColorTheme,
  )

  /* Resolved light/dark based on theme + OS */
  const resolvedTheme = React.useMemo((): ResolvedTheme => {
    if (theme === "system") {
      return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
    }
    return theme
  }, [theme])

  const modeSupported = React.useCallback(
    (mode: ResolvedTheme) => {
      const activeTheme = colorTheme as ColorTheme
      const modes = COLOR_THEME_MODES[activeTheme]
      return modes ? modes.includes(mode) : true
    },
    [colorTheme],
  )

  /* Apply classes to <html> whenever values change */
  React.useEffect(() => {
    if (typeof document === "undefined") return
    const root = document.documentElement
    const mq = window.matchMedia("(prefers-color-scheme: dark)")

    const apply = (resolved: ResolvedTheme) => {
      const activeTheme = colorTheme as ColorTheme
      // Remove all colour-theme classes, then re-add the active one
      root.classList.remove("theme-blue", "parchment")
      if (activeTheme === "blue") root.classList.add("theme-blue")
      else if (activeTheme === "parchment") root.classList.add("parchment")
      // "green" needs no extra class — theme.css :root is the default

      // Light / dark class
      const modes = COLOR_THEME_MODES[activeTheme]
      const supported = modes ?? ["light", "dark"]
      const effective = supported.includes(resolved) ? resolved : (supported[0] ?? "dark")

      root.classList.remove("light", "dark")
      root.classList.add(effective)
    }

    const handleOsChange = () => {
      if (theme === "system") apply(mq.matches ? "dark" : "light")
    }

    apply(resolvedTheme)
    mq.addEventListener("change", handleOsChange)
    return () => mq.removeEventListener("change", handleOsChange)
  }, [theme, resolvedTheme, colorTheme])

  const setTheme = React.useCallback((t: Theme) => {
    setCookie(THEME_COOKIE, t, COOKIE_MAX_AGE)
    _setTheme(t)
  }, [])

  const resetTheme = React.useCallback(() => {
    removeCookie(THEME_COOKIE)
    _setTheme(DEFAULT_THEME)
  }, [])

  const setColorTheme = React.useCallback((c: ColorTheme) => {
    setCookie(COLOR_THEME_COOKIE, c, COOKIE_MAX_AGE)
    _setColorTheme(c)
  }, [])

  const resetColorTheme = React.useCallback(() => {
    removeCookie(COLOR_THEME_COOKIE)
    _setColorTheme(DEFAULT_COLOR_THEME)
  }, [])

  const value = React.useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
      resetTheme,
      defaultTheme: DEFAULT_THEME,
      colorTheme,
      setColorTheme,
      resetColorTheme,
      defaultColorTheme: DEFAULT_COLOR_THEME,
      modeSupported,
    }),
    [theme, resolvedTheme, setTheme, resetTheme, colorTheme, setColorTheme, resetColorTheme, modeSupported],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = React.useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider")
  return ctx
}
