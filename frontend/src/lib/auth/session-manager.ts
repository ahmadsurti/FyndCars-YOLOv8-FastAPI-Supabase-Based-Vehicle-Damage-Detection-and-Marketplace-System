import { supabase } from '@/lib/supabase/client'

export async function getAuthHeader(): Promise<string | null> {
  try {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ? `Bearer ${session.access_token}` : null
  } catch {
    return null
  }
}
