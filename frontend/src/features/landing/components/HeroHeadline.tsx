import { useEffect, useState } from "react";
import { DiaText } from "@/components/ui/dia-text";

const SUBJECTS = ["photograph", "document", "number"];
const OBJECTS = ["a dent", "an owner", "the mileage"];
const CYCLE_MS = 4500;

// Segment groups: array of segment-index arrays. Pairs share a space-y wrapper.
const GROUPS = [[0], [1], [2], [3, 4], [5, 6]];

// Precompute word start offsets
const SEGMENTS = (() => {
  const texts = [
    "But none of them tell the whole story alone",
    "A vehicle has to be seen from every angle, checked against its records, understood through its condition, and judged against everything the evidence reveals",
    "That is how fynd(cars) approaches every vehicle",
    "Every signal matters",
    "Images, documents, 360° coverage, mileage, registration, and visible damage come together to build a clearer picture of the vehicle",
    "Not just detecting damage",
    "Understanding the vehicle before it enters the market",
  ];
  let offset = 0;
  return texts.map((text) => {
    const words = text.split(" ");
    const start = offset;
    offset += words.length;
    return { words, start };
  });
})();

const TOTAL_WORDS = SEGMENTS.reduce((n, s) => n + s.words.length, 0);

const P_CLS = "font-light text-base sm:text-lg md:text-xl lg:text-2xl tracking-tight leading-snug text-balance w-full";

function SegWords({ idx, revealed }: { idx: number; revealed: number }) {
  const seg = SEGMENTS[idx]!;
  return (
    <>
      {seg.words.map((w, i) => {
        const gi = seg.start + i;
        return (
          <span key={gi} className={`transition-colors duration-200 ${gi < revealed ? "text-white" : "text-white/25"}`}>
            {w}{" "}
          </span>
        );
      })}
    </>
  );
}

export function HeroHeadline({ scrollProgress = 0 }: { scrollProgress?: number }) {
  const [activeIdx, setActiveIdx] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setActiveIdx((p) => (p + 1) % SUBJECTS.length), CYCLE_MS);
    return () => clearInterval(id);
  }, []);

  const reveal = Math.min(Math.max(scrollProgress / 0.28, 0), 1);
  const revealed = Math.floor(Math.min(Math.max((scrollProgress - 0.28) / 0.64, 0), 1) * TOTAL_WORDS);

  return (
    <div className="font-labil flex flex-col items-center justify-center text-center max-w-4xl mx-auto px-4 sm:px-6 select-none w-full">
      <div className="space-y-1.5 sm:space-y-2.5">
        <p className="font-light text-lg sm:text-xl md:text-2xl lg:text-3xl tracking-tight text-white leading-snug">
          A car is more than a listing
        </p>
        <p className="font-light text-lg sm:text-xl md:text-2xl lg:text-3xl tracking-tight text-white leading-snug">
          <span className="font-light inline align-baseline">A</span>
          <DiaText
            text={SUBJECTS}
            externalIndex={activeIdx}
            triggerOnView={false}
            once={false}
            duration={1.1}
            textColor="#ffffff"
            className="mx-[0.25em] font-light text-inherit inline-block align-baseline"
          />
          <span className="font-light inline align-baseline">can show</span>
          <DiaText
            text={OBJECTS}
            externalIndex={activeIdx}
            triggerOnView={false}
            once={false}
            duration={1.1}
            textColor="#ffffff"
            className="ml-[0.25em] font-light text-inherit inline-block align-baseline"
          />
        </p>
      </div>

      <div
        style={{ maxHeight: `${reveal * 700}px`, opacity: reveal, filter: `blur(${(1 - reveal) * 12}px)`, pointerEvents: reveal > 0.4 ? "auto" : "none" }}
        className="overflow-hidden transition-all duration-300 ease-out will-change-[opacity,filter,max-height] w-full"
      >
        <div className="pt-5 sm:pt-6 flex flex-col items-center gap-3.5 sm:gap-4 max-w-2xl mx-auto w-full">
          {GROUPS.map((group, gi) =>
            group.length === 1 ? (
              <p key={gi} className={P_CLS}><SegWords idx={group[0]!} revealed={revealed} /></p>
            ) : (
              <div key={gi} className="space-y-1 sm:space-y-1.5 text-balance w-full">
                {group.map((idx) => <p key={idx} className={P_CLS}><SegWords idx={idx} revealed={revealed} /></p>)}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
