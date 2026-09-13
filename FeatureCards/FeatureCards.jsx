import { GlowingEffect } from './GlowingEffect.jsx';
import './FeatureCards.css';

export const DEFAULT_CARDS = [
  {
    area: 'card-a',
    tag: '01',
    title: 'AI Loan Approval',
    description:
      'Submit once. Our model reads your full financial fingerprint and returns an eligibility verdict in seconds — no branch visit, no paperwork pile.',
  },
  {
    area: 'card-b',
    tag: '02',
    title: 'Smart Credit Card Picks',
    description:
      'Ranked recommendations built from your spending DNA. Cashback, travel miles, or low APR — matched to how you actually spend.',
  },
  {
    area: 'card-c',
    tag: '03',
    title: 'Loan Application Manager',
    description:
      'Every application, every lender, every status update — unified in a single live dashboard so nothing slips through the cracks.',
  },
  {
    area: 'card-d',
    tag: '04',
    title: 'AI Assistance',
    description:
      'Ask anything. Your personal finance co-pilot answers in plain language, flags risks before they cost you, and guides every decision.',
  },
];

/**
 * Single Feature Card with interactive GlowingEffect border.
 */
export function FeatureCard({
  tag,
  title,
  description,
  glowProps = { spread: 40, glow: true, proximity: 64, inactiveZone: 0.01, borderWidth: 3 },
  className = '',
  children,
}) {
  return (
    <div className={`features-outer ${className}`}>
      <GlowingEffect {...glowProps} />
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

/**
 * Bento Grid Feature Section.
 */
export function FeatureCards({
  eyebrow = 'WHAT CREDENCE DOES',
  title = (
    <>
      Four tools.<br />One financial edge.
    </>
  ),
  cards = DEFAULT_CARDS,
  glowProps = { spread: 40, glow: true, proximity: 64, inactiveZone: 0.01, borderWidth: 3 },
  className = '',
}) {
  return (
    <section className={`features-section ${className}`} aria-labelledby="features-heading">
      {(eyebrow || title) && (
        <div className="features-header">
          {eyebrow && <p className="features-eyebrow">{eyebrow}</p>}
          {title && (
            <h2 className="features-heading" id="features-heading">
              {title}
            </h2>
          )}
        </div>
      )}

      <ul className="features-grid">
        {cards.map((card, index) => {
          const areaClass = card.area ? `features-item--${card.area}` : '';
          const key = card.id || card.area || index;

          return (
            <li
              key={key}
              className={`features-item ${areaClass}`}
              style={card.colSpan ? { gridColumn: `span ${card.colSpan}` } : undefined}
            >
              <FeatureCard
                tag={card.tag}
                title={card.title}
                description={card.description}
                glowProps={glowProps}
              >
                {card.content}
              </FeatureCard>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default FeatureCards;
