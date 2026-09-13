import { useRef, useEffect, useState } from 'react'
import { Navbar } from './components/Navbar'
import { HeroHeadline } from './components/HeroHeadline'
import { FeatureCards } from './components/FeatureCards'

export function LandingPage() {
  const [scrollProgress, setScrollProgress] = useState(0)
  const containerRef = useRef<HTMLElement>(null)

  useEffect(() => {
    let rafId: number
    const handleScroll = () => {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const scrollableDist = containerRef.current.offsetHeight - window.innerHeight
      if (scrollableDist <= 0) return
      const currentScroll = -rect.top
      const progress = Math.min(Math.max(currentScroll / scrollableDist, 0), 1)
      setScrollProgress(progress)
    }

    const onScroll = () => {
      cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(handleScroll)
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    handleScroll()

    return () => {
      window.removeEventListener('scroll', onScroll)
      cancelAnimationFrame(rafId)
    }
  }, [])

  // Exit transition into feature section (0.82 to 1.0)
  const exitProgress = Math.min(Math.max((scrollProgress - 0.92) / 0.08, 0), 1)
  const dimOpacity = 0.25 + exitProgress * 0.70
  const textOpacity = Math.max(1 - exitProgress * 1.4, 0)

  return (
    <main className="relative bg-black text-[var(--foreground)] antialiased selection:bg-[var(--primary)] selection:text-[var(--primary-foreground)]">
      {/* Pinned Hero Section with Scroll Track */}
      <section
        ref={containerRef}
        className="relative isolate h-[340vh] w-full"
      >
        <div className="sticky top-0 h-screen w-full overflow-hidden flex flex-col items-center justify-center">
          {/* Hero Background Image Layer */}
          <div className="absolute inset-0 z-0 pointer-events-none select-none bg-black">
            <img
              src="/images/hero.jpg"
              alt=""
              aria-hidden="true"
              className="absolute inset-0 h-full w-full object-cover object-center scale-110"
              style={{ filter: 'blur(6px)' }}
            />
            {/* Dynamic Atmosphere Tint into #08090c */}
            <div
              style={{ backgroundColor: `rgba(8, 9, 12, ${dimOpacity})` }}
              className="absolute inset-0 transition-colors duration-200"
            />
          </div>

          {/* Feathered Bottom Transition into Feature Section */}
          <div className="absolute inset-x-0 bottom-0 h-48 sm:h-64 pointer-events-none z-10 bg-gradient-to-b from-transparent via-[#08090c]/70 to-[#08090c]" />

          {/* Top-Left Navbar */}
          <Navbar />

          {/* Page Content Canvas */}
          <div
            style={{
              opacity: textOpacity,
              transform: `translateY(${-exitProgress * 24}px)`,
            }}
            className="relative z-10 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col items-center justify-center text-center transition-all duration-200 will-change-[opacity,transform]"
          >
            <HeroHeadline scrollProgress={scrollProgress} />
          </div>
        </div>
      </section>

      {/* Feature Cards Section */}
      <div className="relative z-20 bg-[#08090c]">
        <FeatureCards />
      </div>

      {/* Auth CTA Trigger */}
      <section className="relative z-20 bg-[#08090c] pb-32 pt-12 flex justify-center items-center">
        <button
          type="button"
          id="cta-sign-in-btn"
          className="rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-black transition-all duration-300 hover:bg-neutral-200 hover:scale-[1.03] active:scale-[0.98] shadow-2xl cursor-pointer"
        >
          Sign In
        </button>
      </section>
    </main>
  )
}
