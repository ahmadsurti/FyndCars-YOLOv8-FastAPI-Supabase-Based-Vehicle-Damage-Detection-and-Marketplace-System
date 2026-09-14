import * as React from "react"
import { Moon, Search, Settings, Sun } from "lucide-react"
import { Separator } from "../ui/separator"
import { SidebarTrigger } from "../ui/sidebar"
import { Button } from "../ui/button"
import { useTheme } from "../../context/theme-provider"
import { ConfigDrawer } from "./ConfigDrawer"
import { cn } from "../../lib/utils"

export interface DashboardHeaderProps {
  /** Title or breadcrumb node to display in the header */
  title?: React.ReactNode
  /** Custom action elements placed on the right side of the header */
  actions?: React.ReactNode
  /** Callback fired when the search action is clicked */
  onSearchClick?: () => void
  /** Optional custom className */
  className?: string
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme, colorTheme, modeSupported } = useTheme()
  const canToggle = modeSupported("light") && modeSupported("dark")

  const handleToggle = () => {
    if (!canToggle) return
    setTheme(resolvedTheme === "dark" ? "light" : "dark")
  }

  React.useEffect(() => {
    if (typeof document === "undefined") return
    const color =
      resolvedTheme === "dark"
        ? colorTheme === "parchment"
          ? "#1c1610"
          : "#1a2416"
        : colorTheme === "parchment"
          ? "#ece8e0"
          : "#f3f8f3"
    document.querySelector("meta[name='theme-color']")?.setAttribute("content", color)
  }, [resolvedTheme, colorTheme])

  return (
    <Button
      variant="ghost"
      size="icon"
      className="size-8 rounded-lg cursor-pointer"
      aria-label="Toggle light/dark"
      onClick={handleToggle}
      disabled={!canToggle}
      title={canToggle ? "Toggle light / dark" : "This theme has one mode only"}
    >
      <Sun className="size-3.5 scale-100 rotate-0 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute size-3.5 scale-0 rotate-90 transition-all dark:rotate-0 dark:scale-100" />
    </Button>
  )
}

export function DashboardHeader({
  title = "Dashboard",
  actions,
  onSearchClick,
  className,
}: DashboardHeaderProps) {
  const [scrolled, setScrolled] = React.useState(false)

  React.useEffect(() => {
    const onScroll = () =>
      setScrolled(document.body.scrollTop > 10 || document.documentElement.scrollTop > 10)
    document.addEventListener("scroll", onScroll, { passive: true })
    return () => document.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header
      className={cn(
        "sticky top-0 z-40 h-12 border-b border-border/70 bg-background/90 backdrop-blur-md transition-shadow",
        scrolled && "shadow-sm",
        className,
      )}
    >
      <div className="flex h-full items-center gap-2 px-3">
        {/* Sidebar toggle button */}
        <SidebarTrigger className="size-7 rounded-md" />
        <Separator orientation="vertical" className="h-4 mx-1" />

        {/* Title / Breadcrumbs */}
        <div className="text-xs font-semibold text-foreground truncate max-w-[200px] sm:max-w-xs md:max-w-md">
          {title}
        </div>

        {/* Center / Right Spacer */}
        <div className="flex-1" />

        {/* Custom Actions (Filters, Badges, Secondary CTAs) */}
        {actions && <div className="flex items-center gap-1.5">{actions}</div>}

        {/* Search button (⌘K trigger) */}
        {onSearchClick && (
          <Button
            variant="ghost"
            size="icon"
            className="size-8 rounded-lg cursor-pointer"
            onClick={onSearchClick}
            aria-label="Search (⌘K)"
            title="Search (⌘K)"
          >
            <Search className="size-3.5" />
          </Button>
        )}

        {/* Dark / Light Mode Toggle */}
        <ThemeToggle />

        {/* Appearance Settings Drawer */}
        <ConfigDrawer>
          <Button
            variant="ghost"
            size="icon"
            className="size-8 rounded-lg cursor-pointer"
            aria-label="Appearance settings"
            title="Appearance settings"
          >
            <Settings className="size-3.5" />
          </Button>
        </ConfigDrawer>
      </div>
    </header>
  )
}
