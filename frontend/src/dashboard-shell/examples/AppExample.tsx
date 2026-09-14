import * as React from "react"
import { BarChart3, Bell, CheckCircle2, FileText, Home, Plus, Settings, Users } from "lucide-react"
import { ThemeProvider } from "../context/theme-provider"
import { DashboardLayout } from "../components/layout/DashboardLayout"
import { Button } from "../components/ui/button"

const DEMO_ITEMS = [
  { id: "overview", title: "Project Overview", icon: Home },
  { id: "analytics", title: "Analytics & Metrics", icon: BarChart3 },
  { id: "team", title: "Team Members", icon: Users, badge: "12" },
  { id: "docs", title: "Documentation", icon: FileText },
  { id: "settings", title: "General Settings", icon: Settings },
]

export function AppExample() {
  const [activeId, setActiveId] = React.useState("overview")
  const [items, setItems] = React.useState(DEMO_ITEMS)

  const handleNewItem = () => {
    const id = `item-${Date.now()}`
    const newItem = { id, title: `New Item (${items.length + 1})`, icon: FileText }
    setItems((prev) => [newItem, ...prev])
    setActiveId(id)
  }

  const handleDeleteItem = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id))
    if (activeId === id) setActiveId("overview")
  }

  const handleRenameItem = (id: string, newTitle: string) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, title: newTitle } : item)),
    )
  }

  return (
    <ThemeProvider defaultTheme="system">
      <DashboardLayout
        sidebarProps={{
          brand: {
            name: "HyperScale",
            subtitle: "Cloud Workspace",
          },
          items,
          itemsLabel: "Navigation",
          activeId,
          onSelectItem: setActiveId,
          onNewItem: handleNewItem,
          newItemLabel: "New Workspace",
          onDeleteItem: handleDeleteItem,
          onRenameItem: handleRenameItem,
          onSearchClick: () => alert("Search triggered (⌘K)"),
          user: {
            name: "Ahmad Surti",
            email: "ahmad@example.com",
          },
          onSignOut: () => alert("Signed out"),
        }}
        headerProps={{
          title: items.find((i) => i.id === activeId)?.title ?? "Dashboard",
          actions: (
            <>
              <div className="hidden sm:flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-md bg-primary/10 text-primary border border-primary/20">
                <CheckCircle2 className="size-3" />
                <span>Operational</span>
              </div>
              <Button variant="outline" size="sm" className="h-7 text-xs gap-1">
                <Plus className="size-3" />
                <span>Add Widget</span>
              </Button>
            </>
          ),
          onSearchClick: () => alert("Search shortcut triggered"),
        }}
        contentLayout="fixed"
      >
        {/* Sample Content Slot — Replace this with your actual page components */}
        <div className="flex-1 flex flex-col p-6 overflow-y-auto gap-6">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              {items.find((i) => i.id === activeId)?.title ?? "Workspace"}
            </h1>
            <p className="text-sm text-muted-foreground">
              Universal shell ready for your product logic. Resize the sidebar, change themes in the top-right drawer, or collapse to compact mode.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Active Nodes", val: "1,248", delta: "+12.4%" },
              { label: "Throughput", val: "84.2 MB/s", delta: "+8.1%" },
              { label: "Avg Latency", val: "14ms", delta: "-2.3%" },
              { label: "Uptime", val: "99.98%", delta: "Solid" },
            ].map((stat, i) => (
              <div
                key={i}
                className="rounded-xl border border-border/70 bg-card p-4 shadow-sm flex flex-col gap-1"
              >
                <span className="text-xs font-medium text-muted-foreground">{stat.label}</span>
                <div className="flex items-baseline justify-between">
                  <span className="text-xl font-bold font-mono text-foreground">{stat.val}</span>
                  <span className="text-xs font-semibold text-primary">{stat.delta}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex-1 rounded-xl border border-border/70 bg-card/60 p-6 flex flex-col items-center justify-center text-center">
            <p className="text-sm font-medium text-foreground">Your project content goes right here</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-sm">
              The shell handles the responsive header, collapsible & resizable sidebar, dark/light themes, and appearance controls.
            </p>
          </div>
        </div>
      </DashboardLayout>
    </ThemeProvider>
  )
}
