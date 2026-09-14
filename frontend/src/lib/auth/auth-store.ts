import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { supabase } from '@/lib/supabase/client'
import type { User } from '@supabase/supabase-js'

export type UserRole = 'admin' | 'seller' | 'buyer'

export interface AuthProfile {
  id: string
  email: string
  fullName?: string
  role: UserRole
  isDemo?: boolean
}

interface AuthState {
  user: User | null
  profile: AuthProfile | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  isAuthModalOpen: boolean
  authModalMode: 'signin' | 'signup'
  
  // Modal controls
  openAuthModal: (mode?: 'signin' | 'signup') => void
  closeAuthModal: () => void
  setAuthModalMode: (mode: 'signin' | 'signup') => void

  // Session actions
  setSession: (user: User | null, token: string | null, profile?: AuthProfile | null) => void
  loginAsDemo: (role: UserRole) => void
  signOut: () => Promise<void>
  initializeAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      profile: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,
      isAuthModalOpen: false,
      authModalMode: 'signin',

      openAuthModal: (mode = 'signin') => set({ isAuthModalOpen: true, authModalMode: mode }),
      closeAuthModal: () => set({ isAuthModalOpen: false }),
      setAuthModalMode: (mode) => set({ authModalMode: mode }),

      setSession: (user, token, profile) => {
        if (!user) {
          set({ user: null, token: null, profile: null, isAuthenticated: false, isLoading: false })
          return
        }

        const resolvedProfile: AuthProfile = profile || {
          id: user.id,
          email: user.email || '',
          fullName: user.user_metadata?.full_name || user.user_metadata?.name || '',
          role: (user.app_metadata?.role as UserRole) || (user.user_metadata?.role as UserRole) || 'buyer',
          isDemo: false,
        }

        set({
          user,
          token,
          profile: resolvedProfile,
          isAuthenticated: true,
          isLoading: false,
        })
      },

      loginAsDemo: (role: UserRole) => {
        const demoProfile: AuthProfile = {
          id: `demo-${role}-id`,
          email: `${role}@fyndcars.dev`,
          fullName: `Demo ${role.charAt(0).toUpperCase() + role.slice(1)}`,
          role,
          isDemo: true,
        }
        set({
          user: {
            id: demoProfile.id,
            email: demoProfile.email,
            app_metadata: { role },
            user_metadata: { full_name: demoProfile.fullName },
            aud: 'authenticated',
            created_at: new Date().toISOString(),
          } as User,
          token: `demo-${role}`,
          profile: demoProfile,
          isAuthenticated: true,
          isLoading: false,
          isAuthModalOpen: false,
        })
      },

      signOut: async () => {
        try {
          if (!get().profile?.isDemo) {
            await supabase.auth.signOut()
          }
        } catch (err) {
          console.error('Error signing out:', err)
        } finally {
          set({
            user: null,
            profile: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      },

      initializeAuth: async () => {
        try {
          // If a demo user is active in local storage, keep it
          if (get().profile?.isDemo) {
            set({ isLoading: false })
            return
          }

          const { data: { session } } = await supabase.auth.getSession()
          if (session?.user) {
            // Fetch profile role from public.profiles
            let role: UserRole = (session.user.app_metadata?.role as UserRole) || 'buyer'
            try {
              const { data: profileRow } = await supabase
                .from('profiles')
                .select('role, full_name')
                .eq('id', session.user.id)
                .single()
              if (profileRow?.role) {
                role = profileRow.role as UserRole
              }
            } catch {
              // fallback to metadata role
            }

            get().setSession(session.user, session.access_token, {
              id: session.user.id,
              email: session.user.email || '',
              fullName: session.user.user_metadata?.full_name || '',
              role,
              isDemo: false,
            })
          } else {
            set({ isLoading: false, isAuthenticated: false })
          }
        } catch {
          set({ isLoading: false, isAuthenticated: false })
        }
      },
    }),
    {
      name: 'fyndcars_auth_session',
      partialize: (state) => ({
        profile: state.profile,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
