import { type ReactNode } from 'react';
import { GlowingEffect } from './GlowingEffect';
import './FeatureCards.css';

// ponytail: glowProps duplicated in two component defaults → one constant
const GLOW = { spread: 40, glow: true, proximity: 64, inactiveZone: 0.01, borderWidth: 3 };

const CARDS = [
  { area: 'card-a', tag: '01', title: 'YOLOv8 Damage Detection', description: 'Sub-millimeter visual assessment trained on over 50,000 multi-angle damage vectors. Instantly detects dents, scratches, panel misalignments, and structural compromises across any vehicle.' },
  { area: 'card-b', tag: '02', title: 'Docling RC Extraction', description: 'Automated registration certificate and documentation parsing. Extracts chassis numbers, ownership history, tax validity, and fitness certificates with zero manual transcription errors.' },
  { area: 'card-c', tag: '03', title: 'Multimodal VLM Telemetry', description: 'Vision-language models synthesize high-resolution imagery, 360° coverage, and historical service records into a unified inspection report before the vehicle ever enters the marketplace.' },
  { area: 'card-d', tag: '04', title: 'Algorithmic Valuation', description: 'Fair-market pricing calculated in real time against live market comparables, adjusting instantly for detected damage severity, odometer verification, and mechanical condition.' },
];

function FeatureCard({ tag, title, description, children }: { tag?: string; title?: string; description?: string; children?: ReactNode }) {
  return (
    <div className="features-outer">
      <GlowingEffect {...GLOW} />
      <div className="features-inner">
        {tag && <div className="features-tag">{tag}</div>}
        <div className="features-body">
          {title && <h3 className="features-title">{title}</h3>}
          {description && <p className="features-desc">{description}</p>}
          {children}
        </div>
        <div className="features-corner-mark" aria-hidden="true" />
      </div>
    </div>
  );
}

export function FeatureCards() {
  return (
    <section className="features-section" aria-labelledby="features-heading">
      <div className="features-header">
        <p className="features-eyebrow">INTELLIGENCE ENGINE</p>
        <h2 className="features-heading" id="features-heading">Four models.<br />One transparent truth.</h2>
      </div>
      <ul className="features-grid">
        {CARDS.map((card) => (
          <li key={card.area} className={`features-item features-item--${card.area}`}>
            <FeatureCard tag={card.tag} title={card.title} description={card.description} />
          </li>
        ))}
      </ul>
    </section>
  );
}

export default FeatureCards;
