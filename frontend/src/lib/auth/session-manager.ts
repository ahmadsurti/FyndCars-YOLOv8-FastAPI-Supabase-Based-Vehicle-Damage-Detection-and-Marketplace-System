import { supabase } from '@/lib/supabase/client'
import { useAuthStore } from './auth-store'

export async function getAuthHeader(): Promise<string | null> {
  // Check Zustand store first (supports Demo tokens)
  const currentToken = useAuthStore.getState().token
  if (currentToken) {
    return currentToken.startsWith('Bearer ') ? currentToken : `Bearer ${currentToken}`
  }

  try {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ? `Bearer ${session.access_token}` : null
  } catch {
    return null
  }
}
