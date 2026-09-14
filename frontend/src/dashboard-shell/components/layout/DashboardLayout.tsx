import * as React from "react"
import { getCookie } from "../../lib/cookies"
import { cn } from "../../lib/utils"
import { LayoutProvider, useLayout } from "../../context/layout-provider"
import { SidebarInset, SidebarProvider } from "../ui/sidebar"
import { DashboardSidebar, type DashboardSidebarProps } from "./DashboardSidebar"
import { DashboardHeader, type DashboardHeaderProps } from "./DashboardHeader"

export interface DashboardLayoutProps {
  /** Props passed through to the sidebar */
  sidebarProps?: DashboardSidebarProps
  /** Props passed through to the header */
  headerProps?: DashboardHeaderProps
  /** The main content of the dashboard */
  children: React.ReactNode
  /** Optional layout mode: 'fixed' (viewport height, internal scrolling) or 'fluid' (document scrolling) */
  contentLayout?: "fixed" | "fluid"
  /** Custom className for the content container */
  contentClassName?: string
}

function InnerLayout({
  sidebarProps = {},
  headerProps = {},
  children,
  contentLayout = "fixed",
  contentClassName,
}: DashboardLayoutProps) {
  const { variant } = useLayout()
  const defaultOpen = getCookie("sidebar_state") !== "false"

  return (
    <SidebarProvider defaultOpen={defaultOpen}>
      {/* Sidebar with Brand, Items, Resizing Rail, and User Menu */}
      <DashboardSidebar {...sidebarProps} />

      {/* Main Workspace Inset Area */}
      <SidebarInset
        className={cn(
          "@container/content",
          contentLayout === "fixed" && "has-data-[layout=fixed]:h-svh",
          variant === "inset" &&
            contentLayout === "fixed" &&
            "has-data-[layout=fixed]:h-[calc(100svh-(var(--spacing)*4))]",
        )}
      >
        {/* Sticky Header with SidebarTrigger, Title, Actions, Theme Toggle, Config Drawer */}
        <DashboardHeader {...headerProps} />

        {/* Dynamic Page Content Slot */}
        <main
          data-layout={contentLayout}
          className={cn(
            "flex flex-1 flex-col overflow-hidden px-4 py-0",
            contentLayout === "fluid" && "overflow-y-auto h-full",
            contentClassName,
          )}
        >
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

/**
 * Universal Dashboard Shell Wrapper.
 * Provides LayoutProvider & SidebarProvider.
 * Wrap your app or dashboard route with this component.
 */
export function DashboardLayout(props: DashboardLayoutProps) {
  return (
    <LayoutProvider>
      <InnerLayout {...props} />
    </LayoutProvider>
  )
}
