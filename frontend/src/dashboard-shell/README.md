# Universal Dashboard Shell Starter Kit

A production-grade, zero-RAG universal dashboard shell extracted directly from this workspace. Drop this folder into any React/Vite/Next.js project to get the exact layout, resizable sidebar, appearance config drawer, dark/light modes, and design system tokens.

---

## 🤖 Prompt for your AI Agents (Copy & Paste)

Whenever you start a new project with an AI agent (Antigravity, Claude Code, Cursor, ChatGPT, etc.), paste this prompt into your conversation:

```markdown
I have a pre-built universal dashboard shell located in `/dashboard-shell`.
Please use this exact shell architecture for my application. Do NOT build custom sidebars, layout wrappers, theme providers, or appearance drawers from scratch.

1. Ensure the following dependencies are installed:
   pnpm add @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-avatar @radix-ui/react-separator @radix-ui/react-tooltip @radix-ui/react-scroll-area @radix-ui/react-radio-group @radix-ui/react-slot lucide-react clsx tailwind-merge class-variance-authority tw-animate-css

2. Import `dashboard-shell/styles/theme.css` in your global CSS entrypoint (`src/index.css` or `src/main.tsx`).

3. Wrap the app with `<ThemeProvider>` from `dashboard-shell/context/theme-provider`.

4. Use `<DashboardLayout>` from `dashboard-shell/components/layout/DashboardLayout` as the workspace frame. Pass my navigation items into `sidebarProps`, header titles/actions into `headerProps`, and mount my view components inside `<DashboardLayout>{children}</DashboardLayout>`.
```

---

## 📦 What's Included

```text
dashboard-shell/
├── README.md                      # This documentation & AI prompt guide
├── styles/
│   └── theme.css                  # OKLCH design tokens for Light/Dark + Forest/Parchment themes, fonts, skeletons
├── context/
│   ├── theme-provider.tsx         # Dark/Light/System mode + Forest/Parchment color themes (cookie persisted)
│   └── layout-provider.tsx        # Sidebar variants (inset/sidebar/floating) & collapse modes (cookie persisted)
├── hooks/
│   └── use-mobile.tsx             # Zero-jank useSyncExternalStore hook for 768px mobile breakpoint
├── lib/
│   ├── cookies.ts                 # Zero-dependency cookie getter/setter/remover
│   └── utils.ts                   # Standard cn() utility (clsx + tailwind-merge)
├── components/
│   ├── layout/
│   │   ├── DashboardLayout.tsx    # Master shell: Provider + Sidebar + SidebarInset + Header + Content Slot
│   │   ├── DashboardHeader.tsx    # Sticky blur header with SidebarTrigger, breadcrumbs, actions slot, ThemeToggle, ConfigDrawer
│   │   ├── DashboardSidebar.tsx   # Universal sidebar: Brand header, search shortcut, items (active, pin, rename, delete), NavUser footer, and resizable rail
│   │   └── ConfigDrawer.tsx       # Slide-out appearance drawer with live color swatches and layout controls
│   └── ui/                        # Accessible UI primitives
│       ├── button.tsx
│       ├── input.tsx
│       ├── separator.tsx
│       ├── skeleton.tsx
│       ├── avatar.tsx
│       ├── tooltip.tsx
│       ├── scroll-area.tsx
│       ├── sheet.tsx
│       ├── dropdown-menu.tsx
│       └── sidebar.tsx            # Shadcn sidebar with SidebarRail (drag to resize!), SidebarInset, Sheet mobile drawer
└── examples/
    └── AppExample.tsx             # Complete, runnable demo demonstrating how to wire everything up
```

---

## ⚡ Quick Start in Any Project

### Step 1: Install Dependencies

```bash
pnpm add @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-avatar @radix-ui/react-separator @radix-ui/react-tooltip @radix-ui/react-scroll-area @radix-ui/react-radio-group @radix-ui/react-slot lucide-react clsx tailwind-merge class-variance-authority tw-animate-css
```

### Step 2: Import Theme CSS

In your main CSS file (`src/index.css`):
```css
@import "./dashboard-shell/styles/theme.css";
```

### Step 3: Implement Your Dashboard

```tsx
import { ThemeProvider } from "./dashboard-shell/context/theme-provider"
import { DashboardLayout } from "./dashboard-shell/components/layout/DashboardLayout"
import { Home, Layers, Settings } from "lucide-react"

const NAV_ITEMS = [
  { id: "overview", title: "Overview", icon: Home },
  { id: "projects", title: "Projects", icon: Layers, badge: 5 },
  { id: "settings", title: "Settings", icon: Settings },
]

export function App() {
  const [activeId, setActiveId] = React.useState("overview")

  return (
    <ThemeProvider defaultTheme="system">
      <DashboardLayout
        sidebarProps={{
          brand: { name: "My Product", subtitle: "Workspace" },
          items: NAV_ITEMS,
          activeId,
          onSelectItem: setActiveId,
          user: { name: "John Doe", email: "john@example.com" },
          onSignOut: () => console.log("Sign out"),
        }}
        headerProps={{
          title: "My Product Dashboard",
        }}
      >
        {/* Your Page Content Renders Here */}
        <div className="p-6">
          <h1 className="text-xl font-bold">Welcome to your dashboard</h1>
        </div>
      </DashboardLayout>
    </ThemeProvider>
  )
}
```

---

## 🎨 Key Features & Controls

1. **Resizable Sidebar Rail (`SidebarRail`)**:
   - Hover the edge of the sidebar and drag or click to collapse/expand smoothly.
   - Press `⌘B` or `Ctrl+B` anywhere to toggle the sidebar.

2. **Light / Dark Mode (`ThemeToggle`)**:
   - Animated flip button between Sun and Moon.
   - Synchronizes with system preferences (`prefers-color-scheme`) and `<meta name="theme-color">`.
   - Persisted via cookies so refreshes never flash.

3. **Appearance Drawer (`ConfigDrawer`)**:
   - Accessible via the top-right Settings icon in the header.
   - **Colour Theme**: Switch between **Forest** (emerald accent) and **Parchment** (warm violet accent) with live preview swatches.
   - **Sidebar Style**: Switch between **Inset** (card-like rounded container), **Sidebar** (full-height flush), and **Floating**.
   - **Layout Mode**: Switch between **Default** (expanded), **Compact** (icon-only rail), and **Hidden** (offcanvas drawer).
   - **Reset to Defaults**: One-click restore to base configuration.

4. **Item Pinning & Inline Renaming**:
   - Pin important items to the top pinned group.
   - Rename items inline with automatic autofocus and Escape/Enter keyboard bindings.
   - 3-dots action menu for easy actions.
