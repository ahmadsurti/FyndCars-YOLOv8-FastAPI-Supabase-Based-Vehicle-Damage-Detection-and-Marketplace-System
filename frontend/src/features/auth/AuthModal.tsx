import { useState, useEffect, useRef, type FormEvent } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { X, ArrowRight, Eye, EyeOff, Loader2 } from 'lucide-react'
import { supabase } from '@/lib/supabase/client'
import { useAuthStore } from '@/lib/auth/auth-store'
import { useNavigate } from '@tanstack/react-router'
import { DiaText } from '@/components/ui/dia-text'

const SIGNUP_PHRASES = [
  'the cult',
  'the future of car buying',
  'fynd(cars)',
]

const SIGNIN_PHRASES = [
  'big dawg',
  'Mr. Spender',
  'to fynd(cars)',
]

interface DraggableToggleProps {
  mode: 'signin' | 'signup'
  onChange: (mode: 'signin' | 'signup') => void
}

function DraggableAuthToggle({ mode, onChange }: DraggableToggleProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [trackWidth, setTrackWidth] = useState(0)
  const isSignUp = mode === 'signup'

  useEffect(() => {
    if (!trackRef.current) return
    const updateWidth = () => {
      if (trackRef.current) {
        setTrackWidth(trackRef.current.offsetWidth)
      }
    }
    updateWidth()
    const ro = new ResizeObserver(updateWidth)
    ro.observe(trackRef.current)
    return () => ro.disconnect()
  }, [])

  const padding = 4
  const pillWidth = trackWidth > 0 ? (trackWidth - padding * 2) / 2 : 0

  return (
    <div
      ref={trackRef}
      role="tablist"
      aria-label="Authentication Mode"
      className="relative flex items-center rounded-lg bg-white/[0.04] p-1 border border-white/[0.08] select-none text-xs font-medium overflow-hidden touch-none"
    >
      {/* Background static slots for instant click targeting */}
      <button
        type="button"
        role="tab"
        aria-selected={!isSignUp}
        onClick={() => onChange('signin')}
        className={`w-1/2 py-1.5 text-center transition-colors duration-150 cursor-pointer ${!isSignUp ? 'text-transparent' : 'text-neutral-400 hover:text-white'
          }`}
      >
        Sign In
      </button>

      <button
        type="button"
        role="tab"
        aria-selected={isSignUp}
        onClick={() => onChange('signup')}
        className={`w-1/2 py-1.5 text-center transition-colors duration-150 cursor-pointer ${isSignUp ? 'text-transparent' : 'text-neutral-400 hover:text-white'
          }`}
      >
        Sign Up
      </button>

      {/* Draggable & Slideable Active Pill */}
      {pillWidth > 0 && (
        <motion.div
          drag="x"
          dragConstraints={{ left: 0, right: pillWidth }}
          dragElastic={0.12}
          dragMomentum={false}
          onDragEnd={(_, info) => {
            const threshold = pillWidth * 0.32
            const isFlickRight = info.velocity.x > 180
            const isFlickLeft = info.velocity.x < -180

            if (!isSignUp && (info.offset.x > threshold || isFlickRight)) {
              onChange('signup')
            } else if (isSignUp && (info.offset.x < -threshold || isFlickLeft)) {
              onChange('signin')
            }
          }}
          animate={{ x: isSignUp ? pillWidth : 0 }}
          transition={{ type: 'spring', stiffness: 480, damping: 36 }}
          whileTap={{ scale: 0.98 }}
          className="absolute top-1 bottom-1 rounded-md bg-white text-black font-semibold shadow-sm flex items-center justify-center cursor-grab active:cursor-grabbing z-10"
          style={{
            width: pillWidth,
            left: padding,
          }}
        >
          <span className="truncate pointer-events-none select-none">
            {isSignUp ? 'Sign Up' : 'Sign In'}
          </span>
        </motion.div>
      )}
    </div>
  )
}

export function AuthModal() {
  const navigate = useNavigate()
  const {
    isAuthModalOpen,
    authModalMode,
    closeAuthModal,
    setAuthModalMode,
    setSession,
    loginAsDemo,
  } = useAuthStore()

  // Shared form inputs that persist across mode toggles
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [accountNotFound, setAccountNotFound] = useState(false)

  // Synchronized phrase cycle
  const [activePhraseIdx, setActivePhraseIdx] = useState(0)

  // Preload both banner images
  useEffect(() => {
    const img1 = new Image()
    img1.src = '/images/welcometothecult.jpg'
    const img2 = new Image()
    img2.src = '/images/welcomeback.jpg'
  }, [])

  // Rotate phrases on a 3.2s interval
  useEffect(() => {
    if (!isAuthModalOpen) return
    const timer = setInterval(() => {
      setActivePhraseIdx((prev) => (prev + 1) % 3)
    }, 3200)
    return () => clearInterval(timer)
  }, [isAuthModalOpen, authModalMode])

  // Switch mode while retaining typed data
  const handleModeSwitch = (mode: 'signin' | 'signup') => {
    setAuthModalMode(mode)
    setErrorMsg(null)
    setSuccessMsg(null)
    setAccountNotFound(false)
    setActivePhraseIdx(0)
  }

  // Keyboard accessibility: Escape to close
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isAuthModalOpen) {
        closeAuthModal()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isAuthModalOpen, closeAuthModal])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setSuccessMsg(null)
    setAccountNotFound(false)
    setLoading(true)

    try {
      if (authModalMode === 'signup') {
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            data: {
              full_name: fullName.trim(),
              role: 'buyer',
            },
          },
        })

        if (error) throw error

        if (data.session) {
          setSession(data.user, data.session.access_token, {
            id: data.user!.id,
            email: data.user!.email || email,
            fullName: fullName.trim(),
            role: 'buyer',
            isDemo: false,
          })
          closeAuthModal()
        } else if (data.user) {
          setSuccessMsg('Account created successfully. You can now sign in.')
          setTimeout(() => handleModeSwitch('signin'), 1200)
        }
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        })

        if (error) {
          if (
            error.message.toLowerCase().includes('invalid login credentials') ||
            error.message.toLowerCase().includes('user not found')
          ) {
            setAccountNotFound(true)
          }
          throw error
        }

        if (data.user && data.session) {
          setSession(data.user, data.session.access_token)
          closeAuthModal()
          navigate({ to: '/app' })
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed'
      setErrorMsg(msg)
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthModalOpen) return null

  const isSignUp = authModalMode === 'signup'

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Authentication dialog"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 overflow-y-auto"
    >
      {/* Balanced Backdrop Blur */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        onClick={closeAuthModal}
        className="fixed inset-0 bg-black/75 backdrop-blur-md"
      />

      {/* Modal Surface */}
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97, y: 10 }}
        transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-[430px] overflow-hidden rounded-xl border border-white/[0.08] bg-[#08090c] shadow-[0_24px_64px_rgba(0,0,0,0.8)] z-10 my-auto text-white select-none"
      >
        {/* Minimal Glass Close Button */}
        <button
          type="button"
          onClick={closeAuthModal}
          aria-label="Close dialog"
          className="absolute top-3 right-3 z-30 flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-neutral-400 backdrop-blur-sm border border-white/[0.06] transition-all hover:bg-black/90 hover:text-white cursor-pointer"
        >
          <X className="h-3.5 w-3.5" />
        </button>

        {/* Top Banner Image */}
        <div className="relative h-44 sm:h-48 w-full overflow-hidden bg-black rounded-t-xl">
          <AnimatePresence mode="wait">
            <motion.img
              key={authModalMode}
              src={isSignUp ? '/images/welcometothecult.jpg' : '/images/welcomeback.jpg'}
              alt={isSignUp ? 'Welcome to the cult' : 'Welcome back'}
              initial={{ opacity: 0, scale: 1.03 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.99 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 h-full w-full object-cover object-center"
            />
          </AnimatePresence>

          {/* Vignette gradients into #08090c */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#08090c] via-[#08090c]/50 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#08090c]/80 via-transparent to-transparent" />

          {/* Hero-matched animated typography in bottom-left corner */}
          <div className="absolute bottom-3 left-4 right-4 z-20 font-labil select-none pointer-events-none">
            <p className="font-light text-base sm:text-lg tracking-tight text-white leading-snug">
              <span className="font-light inline align-baseline">{isSignUp ? 'Welcome to' : 'Welcome back'}</span>
              <DiaText
                text={isSignUp ? SIGNUP_PHRASES : SIGNIN_PHRASES}
                externalIndex={activePhraseIdx}
                triggerOnView={false}
                once={false}
                duration={1.1}
                textColor="#ffffff"
                className="ml-[0.25em] font-light text-inherit inline-block align-baseline"
              />
            </p>
          </div>
        </div>

        {/* Form Body */}
        <div className="p-5 sm:p-6 space-y-4">
          {/* Draggable & Slideable Segmented Mode Toggle */}
          <DraggableAuthToggle mode={authModalMode} onChange={handleModeSwitch} />

          {/* Feedback messages */}
          {errorMsg && (
            <div className="rounded-lg border border-red-500/30 bg-red-950/20 p-2.5 text-xs text-red-200">
              <p>{errorMsg}</p>
              {accountNotFound && (
                <button
                  type="button"
                  onClick={() => handleModeSwitch('signup')}
                  className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-semibold text-white/90 hover:underline cursor-pointer"
                >
                  Create an account with this email <ArrowRight className="h-3 w-3" />
                </button>
              )}
            </div>
          )}

          {successMsg && (
            <div className="rounded-lg border border-white/20 bg-white/[0.04] p-2.5 text-xs text-white/90">
              {successMsg}
            </div>
          )}

          {/* Main Credentials Form */}
          <form onSubmit={handleSubmit} className="space-y-3 font-sans">
            {isSignUp && (
              <div>
                <label className="block text-[11px] font-medium text-neutral-400 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ahmad Surti"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-lg border border-white/[0.08] bg-white/[0.02] px-3.5 py-2.5 text-sm text-white placeholder-neutral-500 outline-none transition focus:border-white/30 focus:bg-white/[0.04]"
                />
              </div>
            )}

            <div>
              <label className="block text-[11px] font-medium text-neutral-400 mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-white/[0.08] bg-white/[0.02] px-3.5 py-2.5 text-sm text-white placeholder-neutral-500 outline-none transition focus:border-white/30 focus:bg-white/[0.04]"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-[11px] font-medium text-neutral-400">
                  Password
                </label>
                {!isSignUp && (
                  <span className="text-[10px] text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer">
                    Forgot password?
                  </span>
                )}
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={6}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-white/[0.08] bg-white/[0.02] px-3.5 py-2.5 pr-10 text-sm text-white placeholder-neutral-500 outline-none transition focus:border-white/30 focus:bg-white/[0.04]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full flex items-center justify-center gap-2 rounded-lg bg-white py-2.5 text-sm font-medium text-black transition-all hover:bg-neutral-200 active:scale-[0.99] disabled:opacity-50 cursor-pointer shadow-sm"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>{isSignUp ? 'Create Account' : 'Sign In'}</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Clean Monochrome Demo Triggers (No AI-slop colors) */}
          <div className="pt-3 border-t border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between text-[10px] tracking-wider uppercase text-neutral-500 font-mono">
              <span>Demo Sandbox</span>
              <span>1-Click Access</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => {
                  loginAsDemo('admin')
                  navigate({ to: '/app' })
                }}
                className="flex items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.02] py-2 px-2 text-xs text-neutral-300 hover:bg-white/[0.06] hover:text-white hover:border-white/20 transition-all font-mono cursor-pointer"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => {
                  loginAsDemo('seller')
                  navigate({ to: '/app' })
                }}
                className="flex items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.02] py-2 px-2 text-xs text-neutral-300 hover:bg-white/[0.06] hover:text-white hover:border-white/20 transition-all font-mono cursor-pointer"
              >
                Seller
              </button>
              <button
                type="button"
                onClick={() => {
                  loginAsDemo('buyer')
                  navigate({ to: '/app' })
                }}
                className="flex items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.02] py-2 px-2 text-xs text-neutral-300 hover:bg-white/[0.06] hover:text-white hover:border-white/20 transition-all font-mono cursor-pointer"
              >
                Buyer
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
