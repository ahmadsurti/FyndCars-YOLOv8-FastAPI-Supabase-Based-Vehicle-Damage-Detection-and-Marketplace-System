import * as React from "react"
import { getCookie, setCookie } from "../lib/cookies"

export type Collapsible = "offcanvas" | "icon" | "none"
export type Variant = "inset" | "sidebar" | "floating"

const LAYOUT_COLLAPSIBLE_COOKIE = "layout_collapsible"
const LAYOUT_VARIANT_COOKIE = "layout_variant"
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7 // 7 days

const DEFAULT_VARIANT: Variant = "inset"
const DEFAULT_COLLAPSIBLE: Collapsible = "icon"

export type LayoutContextType = {
  resetLayout: () => void
  defaultCollapsible: Collapsible
  collapsible: Collapsible
  setCollapsible: (c: Collapsible) => void
  defaultVariant: Variant
  variant: Variant
  setVariant: (v: Variant) => void
}

const LayoutContext = React.createContext<LayoutContextType | null>(null)

export function LayoutProvider({ children }: { children: React.ReactNode }) {
  const [collapsible, _setCollapsible] = React.useState<Collapsible>(
    () => (getCookie(LAYOUT_COLLAPSIBLE_COOKIE) as Collapsible) || DEFAULT_COLLAPSIBLE,
  )
  const [variant, _setVariant] = React.useState<Variant>(
    () => (getCookie(LAYOUT_VARIANT_COOKIE) as Variant) || DEFAULT_VARIANT,
  )

  const setCollapsible = React.useCallback((c: Collapsible) => {
    _setCollapsible(c)
    setCookie(LAYOUT_COLLAPSIBLE_COOKIE, c, COOKIE_MAX_AGE)
  }, [])

  const setVariant = React.useCallback((v: Variant) => {
    _setVariant(v)
    setCookie(LAYOUT_VARIANT_COOKIE, v, COOKIE_MAX_AGE)
  }, [])

  const resetLayout = React.useCallback(() => {
    setCollapsible(DEFAULT_COLLAPSIBLE)
    setVariant(DEFAULT_VARIANT)
  }, [setCollapsible, setVariant])

  const value = React.useMemo(
    () => ({
      resetLayout,
      defaultCollapsible: DEFAULT_COLLAPSIBLE,
      collapsible,
      setCollapsible,
      defaultVariant: DEFAULT_VARIANT,
      variant,
      setVariant,
    }),
    [resetLayout, collapsible, setCollapsible, variant, setVariant],
  )

  return <LayoutContext.Provider value={value}>{children}</LayoutContext.Provider>
}

export function useLayout() {
  const context = React.useContext(LayoutContext)
  if (!context) throw new Error("useLayout must be used within a LayoutProvider")
  return context
}
