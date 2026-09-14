import { Root as Radio, Item } from '@radix-ui/react-radio-group'
import { Check, RotateCcw, Settings, Moon, Sun, Monitor, PanelLeft, Layout, Columns3 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLayout, type Variant, type Collapsible } from '@/context/layout-provider'
import { useTheme } from '@/context/theme-provider'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { useSidebar } from './ui/sidebar'

export function ConfigDrawer() {
  const { setOpen } = useSidebar()
  const { resetTheme, theme, setTheme, defaultTheme } = useTheme()
  const { resetLayout, variant, setVariant, defaultVariant, collapsible, setCollapsible, defaultCollapsible } = useLayout()

  const handleReset = () => {
    setOpen(true)
    resetTheme()
    resetLayout()
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          size="icon"
          variant="ghost"
          aria-label="Open theme and layout settings"
          className="size-8 rounded-lg hover:bg-white/[0.06] text-muted-foreground hover:text-foreground"
        >
          <Settings className="size-4" />
        </Button>
      </SheetTrigger>
      <SheetContent className="flex flex-col bg-[#08090c] border-sidebar-border text-foreground w-80 sm:w-96">
        <SheetHeader className="pb-2 text-start">
          <SheetTitle className="text-base font-semibold tracking-tight text-foreground">
            Workspace Configuration
          </SheetTitle>
          <SheetDescription className="text-xs text-muted-foreground">
            Bespoke appearance, sidebar docking, and viewport layout.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-6 overflow-y-auto py-2 pr-1">
          {/* Theme Section */}
          <div>
            <div className="mb-2.5 flex items-center justify-between text-xs font-mono tracking-wider uppercase text-muted-foreground">
              <span>Theme Appearance</span>
              {theme !== defaultTheme && (
                <button
                  onClick={() => setTheme(defaultTheme)}
                  className="flex items-center gap-1 text-[11px] text-primary hover:underline cursor-pointer"
                >
                  <RotateCcw className="size-3" /> Reset
                </button>
              )}
            </div>
            <Radio
              value={theme}
              onValueChange={(val) => setTheme(val as 'dark' | 'light' | 'system')}
              className="grid grid-cols-3 gap-2"
            >
              {[
                { value: 'dark', label: 'Dark Noir', icon: Moon },
                { value: 'light', label: 'Pure Light', icon: Sun },
                { value: 'system', label: 'System', icon: Monitor },
              ].map((item) => {
                const Icon = item.icon
                const isSelected = theme === item.value
                return (
                  <Item
                    key={item.value}
                    value={item.value}
                    className={cn(
                      'flex flex-col items-center justify-center gap-2 rounded-lg border p-3 text-xs transition-all cursor-pointer outline-none',
                      isSelected
                        ? 'border-primary bg-primary/10 text-primary font-medium'
                        : 'border-border/60 hover:border-border hover:bg-muted/40 text-muted-foreground'
                    )}
                  >
                    <Icon className="size-4" />
                    <span>{item.label}</span>
                  </Item>
                )
              })}
            </Radio>
          </div>

          {/* Sidebar Style Section */}
          <div>
            <div className="mb-2.5 flex items-center justify-between text-xs font-mono tracking-wider uppercase text-muted-foreground">
              <span>Sidebar Style</span>
              {variant !== defaultVariant && (
                <button
                  onClick={() => setVariant(defaultVariant)}
                  className="flex items-center gap-1 text-[11px] text-primary hover:underline cursor-pointer"
                >
                  <RotateCcw className="size-3" /> Reset
                </button>
              )}
            </div>
            <Radio
              value={variant}
              onValueChange={(val) => setVariant(val as Variant)}
              className="grid grid-cols-3 gap-2"
            >
              {[
                { value: 'inset', label: 'Inset Dock', icon: Columns3 },
                { value: 'sidebar', label: 'Full Edge', icon: Layout },
                { value: 'floating', label: 'Floating', icon: PanelLeft },
              ].map((item) => {
                const Icon = item.icon
                const isSelected = variant === item.value
                return (
                  <Item
                    key={item.value}
                    value={item.value}
                    className={cn(
                      'flex flex-col items-center justify-center gap-2 rounded-lg border p-3 text-xs transition-all cursor-pointer outline-none',
                      isSelected
                        ? 'border-primary bg-primary/10 text-primary font-medium'
                        : 'border-border/60 hover:border-border hover:bg-muted/40 text-muted-foreground'
                    )}
                  >
                    <Icon className="size-4" />
                    <span>{item.label}</span>
                  </Item>
                )
              })}
            </Radio>
          </div>

          {/* Collapse Behavior Section */}
          <div>
            <div className="mb-2.5 flex items-center justify-between text-xs font-mono tracking-wider uppercase text-muted-foreground">
              <span>Collapse Behavior</span>
              {collapsible !== defaultCollapsible && (
                <button
                  onClick={() => setCollapsible(defaultCollapsible)}
                  className="flex items-center gap-1 text-[11px] text-primary hover:underline cursor-pointer"
                >
                  <RotateCcw className="size-3" /> Reset
                </button>
              )}
            </div>
            <Radio
              value={collapsible}
              onValueChange={(val) => setCollapsible(val as Collapsible)}
              className="grid grid-cols-2 gap-2"
            >
              {[
                { value: 'icon', label: 'Icon Rail' },
                { value: 'offcanvas', label: 'Off-Canvas' },
              ].map((item) => {
                const isSelected = collapsible === item.value
                return (
                  <Item
                    key={item.value}
                    value={item.value}
                    className={cn(
                      'flex items-center justify-between rounded-lg border p-2.5 text-xs transition-all cursor-pointer outline-none',
                      isSelected
                        ? 'border-primary bg-primary/10 text-primary font-medium'
                        : 'border-border/60 hover:border-border hover:bg-muted/40 text-muted-foreground'
                    )}
                  >
                    <span>{item.label}</span>
                    {isSelected && <Check className="size-3.5 text-primary" />}
                  </Item>
                )
              })}
            </Radio>
          </div>
        </div>

        <SheetFooter className="pt-2 border-t border-border/40">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            className="w-full text-xs font-mono text-muted-foreground hover:text-foreground"
          >
            <RotateCcw className="size-3 mr-1.5" />
            Restore Factory Defaults
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
