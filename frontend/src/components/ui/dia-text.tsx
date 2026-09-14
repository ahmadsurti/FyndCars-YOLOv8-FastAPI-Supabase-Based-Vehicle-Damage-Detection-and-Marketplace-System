import {
  type AnimationPlaybackControls,
  animate,
  motion,
  useInView,
  useMotionValue,
  useTransform,
} from "motion/react";
import {
  type ComponentPropsWithoutRef,
  type CSSProperties,
  forwardRef,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;

import { cn } from "@/lib/utils";

const DEFAULT_COLORS = ["#c679c4", "#fa3d1d", "#ffb005", "#e1e1fe", "#0358f7"];
const BAND_HALF = 17;
const SWEEP_START = -BAND_HALF;
const SWEEP_END = 100 + BAND_HALF;
const TEXT_SWAP_EASE = [0.22, 1, 0.36, 1] as const;

type DiaTextMotionProps = ComponentPropsWithoutRef<typeof motion.span>;

export type DiaTextRevealProps = Omit<
  DiaTextMotionProps,
  "children" | "style" | "animate" | "transition" | "color" | "className"
> & {
  text: string | string[];
  colors?: string[];
  textColor?: string;
  duration?: number;
  delay?: number;
  repeat?: boolean;
  repeatDelay?: number;
  triggerOnView?: boolean;
  once?: boolean;
  className?: string;
  fixedWidth?: boolean;
  externalIndex?: number;
  onIndexChange?: (index: number) => void;
};

const sweepEase = (t: number) =>
  t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2;

function buildGradient(pos: number, colors: string[], textColor: string) {
  const resolvedColor = textColor === "currentColor" || !textColor ? "#ffffff" : textColor;
  const bandStart = pos - BAND_HALF;
  const bandEnd = pos + BAND_HALF;

  if (bandStart >= 100) {
    return `linear-gradient(90deg, ${resolvedColor}, ${resolvedColor})`;
  }

  const count = colors.length;
  const parts: string[] = [];

  if (bandStart > 0) {
    parts.push(`${resolvedColor} 0%`, `${resolvedColor} ${bandStart.toFixed(2)}%`);
  }

  colors.forEach((color, index) => {
    const pct =
      count === 1 ? pos : bandStart + (index / (count - 1)) * BAND_HALF * 2;
    parts.push(`${color} ${pct.toFixed(2)}%`);
  });

  if (bandEnd < 100) {
    parts.push(`transparent ${bandEnd.toFixed(2)}%`, "transparent 100%");
  }

  return `linear-gradient(90deg, ${parts.join(", ")})`;
}

function measureWidths(element: HTMLElement, texts: string[]) {
  const ghost = document.createElement("span");
  const computed = window.getComputedStyle(element);

  ghost.style.font = computed.font;
  ghost.style.fontFamily = computed.fontFamily;
  ghost.style.fontSize = computed.fontSize;
  ghost.style.fontWeight = computed.fontWeight;
  ghost.style.letterSpacing = computed.letterSpacing;
  ghost.style.textTransform = computed.textTransform;
  ghost.style.position = "absolute";
  ghost.style.visibility = "hidden";
  ghost.style.pointerEvents = "none";
  ghost.style.whiteSpace = "nowrap";

  document.body.appendChild(ghost);

  const widths = texts.map((entry) => {
    ghost.textContent = entry;
    return Math.ceil(ghost.getBoundingClientRect().width) + 6;
  });

  ghost.remove();
  return widths;
}

const DiaTextReveal = forwardRef<HTMLSpanElement, DiaTextRevealProps>(
  (
    {
      text,
      colors = DEFAULT_COLORS,
      textColor = "#ffffff",
      duration = 1.5,
      delay = 0,
      repeat = false,
      repeatDelay = 0.5,
      triggerOnView = true,
      once = true,
      className,
      fixedWidth = false,
      externalIndex,
      onIndexChange,
      ...props
    },
    ref
  ) => {
    const spanRef = useRef<HTMLSpanElement | null>(null);
    const isControlled = externalIndex !== undefined;

    const [internalActiveIndex, setInternalActiveIndex] = useState(0);
    const activeIndex = isControlled ? externalIndex! : internalActiveIndex;

    const [measuredWidths, setMeasuredWidths] = useState<number[]>([]);

    const indexRef = useRef(0);
    const hasPlayedRef = useRef(false);
    const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
    const controlsRef = useRef<AnimationPlaybackControls | undefined>(undefined);
    const previousTextKeyRef = useRef("");

    const sweepPos = useMotionValue(SWEEP_START);
    const textOpacity = useMotionValue(1);
    const textBlur = useMotionValue(0);
    const textShift = useMotionValue(0);
    const inView = useInView(spanRef, { once, amount: 0.1 });
    const previousActiveIndexRef = useRef(0);

    const texts = useMemo(() => (Array.isArray(text) ? text : [text]), [text]);
    const textKey = useMemo(() => texts.join("\0"), [texts]);
    const isMulti = texts.length > 1;
    const isVisible = triggerOnView ? inView : true;

    const backgroundImage = useTransform(sweepPos, (pos) =>
      buildGradient(pos, colors, textColor)
    );
    const contentFilter = useTransform(
      textBlur,
      (blur) => `blur(${blur.toFixed(2)}px)`
    );
    const contentTransform = useTransform(
      textShift,
      (shift) => (shift === 0 ? "none" : `translateY(${shift.toFixed(2)}px)`)
    );

    const fixedW = useMemo(
      () =>
        isMulti && fixedWidth && measuredWidths.length > 0
          ? Math.max(...measuredWidths)
          : undefined,
      [fixedWidth, isMulti, measuredWidths]
    );

    const animatedW = useMemo(
      () =>
        isMulti && !fixedWidth && measuredWidths[activeIndex] != null
          ? measuredWidths[activeIndex]
          : undefined,
      [activeIndex, fixedWidth, isMulti, measuredWidths]
    );

    const containerStyle = useMemo(
      (): NonNullable<DiaTextMotionProps["style"]> => ({
        ...(isMulti && {
          display: "inline-block",
          verticalAlign: "baseline",
          whiteSpace: "nowrap",
          ...(fixedW != null && { width: fixedW }),
        }),
      }),
      [fixedW, isMulti]
    );

    const contentStyle = useMemo(
      (): NonNullable<DiaTextMotionProps["style"]> => ({
        display: "inline-block",
        verticalAlign: "baseline",
        fontFamily: "inherit",
        fontSize: "inherit",
        fontWeight: "inherit",
        fontStyle: "normal",
        color: "transparent",
        backgroundClip: "text",
        WebkitBackgroundClip: "text",
        backgroundSize: "100% 100%",
        backgroundImage,
        opacity: textOpacity,
        filter: contentFilter,
        transform: contentTransform,
        willChange: "filter, opacity, transform",
      }),
      [backgroundImage, contentFilter, contentTransform, textOpacity]
    );

    const clearCycle = useCallback(() => {
      controlsRef.current?.stop();
      controlsRef.current = undefined;
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = undefined;
    }, []);

    const playRef = useRef<() => void>(() => undefined);

    playRef.current = () => {
      clearCycle();
      sweepPos.set(SWEEP_START);

      controlsRef.current = animate(sweepPos, SWEEP_END, {
        duration,
        delay,
        ease: sweepEase,
        onComplete() {
          if (isControlled || !repeat || texts.length === 0) return;

          timerRef.current = setTimeout(() => {
            const next = (indexRef.current + 1) % texts.length;
            indexRef.current = next;
            setInternalActiveIndex(next);
            onIndexChange?.(next);
            playRef.current();
          }, repeatDelay * 1000);
        },
      });
    };

    useEffect(() => {
      if (textKey === previousTextKeyRef.current) return;
      previousTextKeyRef.current = textKey;
      indexRef.current = 0;
      setInternalActiveIndex(0);
      hasPlayedRef.current = false;
      clearCycle();
      sweepPos.set(SWEEP_START);
      if (isVisible) {
        hasPlayedRef.current = true;
        playRef.current();
      }
    }, [clearCycle, isVisible, sweepPos, textKey]);

    useEffect(() => {
      const element = spanRef.current;
      if (!(element && isMulti)) {
        setMeasuredWidths([]);
        return;
      }

      const updateWidths = () => {
        if (spanRef.current) {
          setMeasuredWidths(measureWidths(spanRef.current, texts));
        }
      };

      updateWidths();

      if (typeof document !== "undefined" && document.fonts) {
        document.fonts.ready.then(updateWidths);
      }
    }, [isMulti, texts]);

    useEffect(() => {
      if (!isVisible) {
        if (!once) hasPlayedRef.current = false;
        return;
      }
      if (once && hasPlayedRef.current) return;
      hasPlayedRef.current = true;
      playRef.current();
      return clearCycle;
    }, [clearCycle, isVisible, once]);

    useIsomorphicLayoutEffect(() => {
      if (!isMulti) {
        textOpacity.set(1);
        textBlur.set(0);
        textShift.set(0);
        previousActiveIndexRef.current = activeIndex;
        return;
      }

      if (previousActiveIndexRef.current === activeIndex) return;
      previousActiveIndexRef.current = activeIndex;

      // SYNCHRONOUSLY reset BEFORE paint to ensure the new word starts invisible and sweeps in with zero flicker
      sweepPos.set(SWEEP_START);
      textOpacity.set(0);
      textBlur.set(6);
      textShift.set(4);

      const opacityControls = animate(textOpacity, 1, { duration: 0.35, ease: TEXT_SWAP_EASE });
      const blurControls = animate(textBlur, 0, { duration: 0.35, ease: TEXT_SWAP_EASE });
      const shiftControls = animate(textShift, 0, { duration: 0.35, ease: TEXT_SWAP_EASE });

      playRef.current();

      return () => {
        opacityControls.stop();
        blurControls.stop();
        shiftControls.stop();
      };
    }, [activeIndex, isMulti, textBlur, textOpacity, textShift, sweepPos]);

    useEffect(() => clearCycle, [clearCycle]);

    const setRefs = (node: HTMLSpanElement | null) => {
      spanRef.current = node;
      if (typeof ref === "function") ref(node);
      else if (ref) ref.current = node;
    };

    return (
      <motion.span
        animate={animatedW != null ? { width: animatedW } : undefined}
        className={cn("inline-block align-baseline text-inherit leading-inherit", className)}
        ref={setRefs}
        style={containerStyle}
        transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
        {...props}
      >
        <motion.span
          aria-hidden
          className="inline-block align-baseline text-inherit leading-inherit"
          style={contentStyle}
        >
          {texts[activeIndex]}
        </motion.span>
        <span className="sr-only">{texts[activeIndex]}</span>
      </motion.span>
    );
  }
);

DiaTextReveal.displayName = "DiaTextReveal";

const DiaText = DiaTextReveal;

export { DiaText, DiaTextReveal };
