import { type LinkProps } from '@tanstack/react-router'
import { type ComponentType } from 'react'

export type User = {
  name: string
  email: string
  avatar: string
  role?: string
}

export type Team = {
  name: string
  logo: ComponentType<{ className?: string }>
  plan: string
}

export type BaseNavItem = {
  title: string
  badge?: string
  icon?: ComponentType<{ className?: string }>
}

export type NavLink = BaseNavItem & {
  url: LinkProps['to'] | (string & {})
  items?: never
}

export type NavCollapsible = BaseNavItem & {
  items: (BaseNavItem & { url: LinkProps['to'] | (string & {}) })[]
  url?: never
}

export type NavItem = NavCollapsible | NavLink

export type NavGroup = {
  title: string
  items: NavItem[]
}

export type SidebarData = {
  user: User
  teams: Team[]
  navGroups: NavGroup[]
}
