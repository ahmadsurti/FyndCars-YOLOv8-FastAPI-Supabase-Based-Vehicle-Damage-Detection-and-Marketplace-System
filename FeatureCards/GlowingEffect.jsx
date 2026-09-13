import { memo, useCallback, useEffect, useRef } from 'react';

const GRADIENTS = {
  white: `repeating-conic-gradient(from 236.84deg at 50% 50%, var(--black, #000), var(--black, #000) calc(25% / var(--repeating-conic-gradient-times)))`,
  default: `radial-gradient(circle, #dd7bbb 10%, #dd7bbb00 20%),
    radial-gradient(circle at 40% 40%, #d79f1e 5%, #d79f1e00 15%),
    radial-gradient(circle at 60% 60%, #5a922c 10%, #5a922c00 20%),
    radial-gradient(circle at 40% 60%, #4c7894 10%, #4c789400 20%),
    repeating-conic-gradient(from 236.84deg at 50% 50%,
      #dd7bbb 0%, #d79f1e calc(25% / var(--repeating-conic-gradient-times)),
      #5a922c calc(50% / var(--repeating-conic-gradient-times)),
      #4c7894 calc(75% / var(--repeating-conic-gradient-times)),
      #dd7bbb calc(100% / var(--repeating-conic-gradient-times)))`,
};

/**
 * GlowingEffect — Hardware-accelerated mouse-following glow border.
 * Uses CSS custom properties and a single rAF angle lerp loop.
 */
export const GlowingEffect = memo(function GlowingEffect({
  blur = 0,
  inactiveZone = 0.7,
  proximity = 64,
  spread = 20,
  variant = 'default',
  glow = false,
  className = '',
  movementDuration = 2,
  borderWidth = 1,
  disabled = false,
}) {
  const containerRef = useRef(null);
  const lastPos = useRef({ x: 0, y: 0 });
  const rafRef = useRef(0);
  const angleRafRef = useRef(0);

  const animateAngle = useCallback((from, to, duration) => {
    cancelAnimationFrame(angleRafRef.current);
    const start = performance.now();
    const el = containerRef.current;
    if (!el) return;

    const tick = (now) => {
      const t = Math.min((now - start) / (duration * 1000), 1);
      const eased = 1 - Math.pow(1 - t, 3); // cubic ease-out
      el.style.setProperty('--start', String(from + (to - from) * eased));
      if (t < 1) angleRafRef.current = requestAnimationFrame(tick);
    };

    angleRafRef.current = requestAnimationFrame(tick);
  }, []);

  const handleMove = useCallback(
    (e) => {
      if (!containerRef.current) return;
      cancelAnimationFrame(rafRef.current);

      rafRef.current = requestAnimationFrame(() => {
        const el = containerRef.current;
        if (!el) return;

        const { left, top, width, height } = el.getBoundingClientRect();
        const mouseX = e?.clientX ?? lastPos.current.x;
        const mouseY = e?.clientY ?? lastPos.current.y;
        if (e) lastPos.current = { x: mouseX, y: mouseY };

        const centerX = left + width * 0.5;
        const centerY = top + height * 0.5;
        const distFromCenter = Math.hypot(mouseX - centerX, mouseY - centerY);
        const inactiveRadius = 0.5 * Math.min(width, height) * inactiveZone;

        if (distFromCenter < inactiveRadius) {
          el.style.setProperty('--active', '0');
          return;
        }

        const isActive =
          mouseX > left - proximity &&
          mouseX < left + width + proximity &&
          mouseY > top - proximity &&
          mouseY < top + height + proximity;

        el.style.setProperty('--active', isActive ? '1' : '0');
        if (!isActive) return;

        const currentAngle = parseFloat(el.style.getPropertyValue('--start')) || 0;
        const targetAngle = (180 * Math.atan2(mouseY - centerY, mouseX - centerX)) / Math.PI + 90;
        const diff = ((targetAngle - currentAngle + 180) % 360) - 180;

        animateAngle(currentAngle, currentAngle + diff, movementDuration);
      });
    },
    [inactiveZone, proximity, movementDuration, animateAngle]
  );

  useEffect(() => {
    if (disabled) return;
    const onScroll = () => handleMove();
    const onPointer = (e) => handleMove(e);

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pointermove', onPointer, { passive: true });

    return () => {
      cancelAnimationFrame(rafRef.current);
      cancelAnimationFrame(angleRafRef.current);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('pointermove', onPointer);
    };
  }, [handleMove, disabled]);

  if (disabled) {
    return <div className={`ge-static-border ${glow ? 'ge-glow' : ''} ${variant === 'white' ? 'ge-white' : ''}`} />;
  }

  return (
    <div
      ref={containerRef}
      style={{
        '--blur': `${blur}px`,
        '--spread': spread,
        '--start': '0',
        '--active': '0',
        '--glowingeffect-border-width': `${borderWidth}px`,
        '--repeating-conic-gradient-times': '5',
        '--gradient': GRADIENTS[variant] || GRADIENTS.default,
      }}
      className={`ge-glow-container ${glow ? 'ge-glow-active' : ''} ${blur > 0 ? 'ge-blur' : ''} ${className}`}
    >
      <div className="glow ge-inner" />
    </div>
  );
});

export default GlowingEffect;
