import * as React from "react"
import { RotateCcw } from "lucide-react"
import * as RG from "@radix-ui/react-radio-group"
import { cn } from "../../lib/utils"
import { type Collapsible, useLayout } from "../../context/layout-provider"
import { type ColorTheme, useTheme } from "../../context/theme-provider"
import { useSidebar } from "../ui/sidebar"
import { Button } from "../ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "../ui/sheet"
import { ScrollArea } from "../ui/scroll-area"

/* ── Generic layout radio option ── */
function Opt({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <RG.Item
      value={value}
      className={cn(
        "group relative flex flex-col items-center gap-1 rounded-xl border-2 p-3",
        "cursor-pointer transition-all outline-none",
        "border-border/60 bg-background hover:border-primary/40 hover:bg-primary/5",
        "data-[state=checked]:border-primary data-[state=checked]:bg-primary/8",
        "focus-visible:ring-2 focus-visible:ring-ring",
      )}
    >
      <span className="text-xs font-semibold text-foreground">{label}</span>
      {sub && <span className="text-[10px] text-muted-foreground">{sub}</span>}
      <div className="absolute top-1.5 right-1.5 size-2 rounded-full bg-primary opacity-0 group-data-[state=checked]:opacity-100 transition-opacity" />
    </RG.Item>
  )
}

/* ── Section wrapper ── */
function Section({
  title,
  isDirty,
  onReset,
  children,
}: {
  title: string
  isDirty?: boolean
  onReset?: () => void
  children: React.ReactNode
}) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          {title}
        </span>
        {isDirty && onReset && (
          <button
            type="button"
            onClick={onReset}
            className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <RotateCcw className="size-2.5" />
            Reset
          </button>
        )}
      </div>
      {children}
    </div>
  )
}

/* ── Color Theme Swatch Definitions ── */
const COLOR_THEMES: {
  id: ColorTheme
  label: string
  sub: string
  bgLight: string
  bgDark: string
  accent: string
}[] = [
  {
    id: "blue",
    label: "Cobalt",
    sub: "Outfit · electric blue",
    bgLight: "oklch(0.9911 0 0)",
    bgDark: "oklch(0.1350 0.008 260)",
    accent: "oklch(0.5600 0.19 255)",
  },
  {
    id: "green",
    label: "Forest",
    sub: "Outfit · emerald accent",
    bgLight: "oklch(0.9911 0 0)",
    bgDark: "oklch(0.2393 0 0)",
    accent: "oklch(0.8348 0.1302 160.908)",
  },
  {
    id: "parchment",
    label: "Parchment",
    sub: "Warm slate · violet accent",
    bgLight: "oklch(0.923 0.003 48.72)",
    bgDark: "oklch(0.224 0.007 67.44)",
    accent: "oklch(0.585 0.204 277.12)",
  },
]

function ColorThemeSwatch({
  palette,
  isActive,
  isDark,
  onSelect,
}: {
  palette: (typeof COLOR_THEMES)[number]
  isActive: boolean
  isDark: boolean
  onSelect: () => void
}) {
  const bg = isDark ? palette.bgDark : palette.bgLight

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "relative flex flex-col gap-2 rounded-xl border-2 p-3 w-full text-left transition-all outline-none cursor-pointer",
        "hover:border-primary/50",
        "focus-visible:ring-2 focus-visible:ring-ring",
        isActive ? "border-primary shadow-sm" : "border-border/60",
      )}
      aria-pressed={isActive}
    >
      <div
        className="w-full h-8 rounded-lg border border-black/10 dark:border-white/10 overflow-hidden flex"
        style={{ background: bg }}
      >
        <div className="flex-1" style={{ background: bg }} />
        <div
          className="w-3 rounded-sm mx-0.5 my-1"
          style={{ background: palette.accent, opacity: 0.9 }}
        />
        <div
          className="w-3 rounded-sm mr-0.5 my-1"
          style={{ background: palette.accent, opacity: 0.4 }}
        />
      </div>

      <div>
        <p className="text-xs font-semibold text-foreground leading-none">{palette.label}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5">{palette.sub}</p>
      </div>

      {isActive && (
        <div
          className="absolute top-2 right-2 size-2.5 rounded-full"
          style={{ background: palette.accent }}
        />
      )}
    </button>
  )
}

function ColorThemeSection() {
  const {
    colorTheme,
    setColorTheme,
    defaultColorTheme,
    resetColorTheme,
    resolvedTheme,
  } = useTheme()

  return (
    <Section
      title="Colour Theme"
      isDirty={colorTheme !== defaultColorTheme}
      onReset={resetColorTheme}
    >
      <div className="grid grid-cols-3 gap-2">
        {COLOR_THEMES.map((p) => (
          <ColorThemeSwatch
            key={p.id}
            palette={p}
            isActive={colorTheme === p.id}
            isDark={resolvedTheme === "dark"}
            onSelect={() => setColorTheme(p.id)}
          />
        ))}
      </div>
    </Section>
  )
}

function SidebarSection() {
  const { defaultVariant, variant, setVariant } = useLayout()
  return (
    <Section
      title="Sidebar Style"
      isDirty={variant !== defaultVariant}
      onReset={() => setVariant(defaultVariant)}
    >
      <RG.Root value={variant} onValueChange={setVariant} className="grid grid-cols-3 gap-2">
        <Opt value="inset" label="Inset" sub="Rounded" />
        <Opt value="sidebar" label="Sidebar" sub="Full" />
        <Opt value="floating" label="Float" sub="Elevated" />
      </RG.Root>
    </Section>
  )
}

function LayoutSection() {
  const { open, setOpen } = useSidebar()
  const { defaultCollapsible, collapsible, setCollapsible } = useLayout()
  const radio = open ? "default" : collapsible

  return (
    <Section
      title="Layout Mode"
      isDirty={radio !== "default"}
      onReset={() => {
        setOpen(true)
        setCollapsible(defaultCollapsible)
      }}
    >
      <RG.Root
        value={radio}
        onValueChange={(v) => {
          if (v === "default") {
            setOpen(true)
            return
          }
          setOpen(false)
          setCollapsible(v as Collapsible)
        }}
        className="grid grid-cols-3 gap-2"
      >
        <Opt value="default" label="Default" sub="Expanded" />
        <Opt value="icon" label="Compact" sub="Icons" />
        <Opt value="offcanvas" label="Hidden" sub="Full width" />
      </RG.Root>
    </Section>
  )
}

export function ConfigDrawer({ children }: { children: React.ReactNode }) {
  const { setOpen: setSidebarOpen } = useSidebar()
  const { resetColorTheme } = useTheme()
  const { resetLayout } = useLayout()

  return (
    <Sheet>
      <SheetTrigger asChild>{children}</SheetTrigger>
      <SheetContent side="right" className="flex flex-col p-0 sm:max-w-xs">
        <SheetHeader className="border-b border-border/70 px-4 py-3">
          <SheetTitle className="text-sm font-semibold">Appearance</SheetTitle>
          <SheetDescription className="text-xs">
            Colour theme, sidebar style, and layout settings.
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1">
          <div className="flex flex-col gap-6 px-4 py-4">
            <ColorThemeSection />
            <div className="max-md:hidden">
              <SidebarSection />
            </div>
            <div className="max-md:hidden">
              <LayoutSection />
            </div>
          </div>
        </ScrollArea>

        <SheetFooter className="border-t border-border/70 px-4 py-3">
          <Button
            variant="outline"
            size="sm"
            className="w-full gap-1.5 text-xs cursor-pointer"
            onClick={() => {
              setSidebarOpen(true)
              resetColorTheme()
              resetLayout()
            }}
          >
            <RotateCcw className="size-3" />
            Reset to defaults
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
