# FeatureCards Component (Portable)

A self-contained, hardware-accelerated interactive Feature Cards section with dynamic mouse-following glow borders and responsive bento grid layout.

## 📦 What's Included

```
FeatureCards/
├── FeatureCards.jsx    # Main component + individual FeatureCard component
├── GlowingEffect.jsx   # Mouse-following conic gradient glow border (rAF-driven)
├── FeatureCards.css    # Complete responsive styles with fallback fonts and CSS variables
├── index.js            # Barrel export
└── README.md           # Usage guide
```

## 🚀 How to Use in Another Project

### 1. Copy the folder
Copy the entire `FeatureCards/` folder into your new project's `components/` directory (e.g. `src/components/FeatureCards`).

### 2. Fonts (Optional for exact typography)
Add Google Fonts to your HTML `<head>` (or CSS `@import`):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400..700&family=JetBrains+Mono:wght@400..800&family=Lora:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet">
```
*Note: If fonts are not added, the component falls back cleanly to system fonts.*

### 3. Basic Usage (Drop-in)
```jsx
import FeatureCards from './components/FeatureCards';

export default function Page() {
  return (
    <main style={{ backgroundColor: '#08090c', minHeight: '100vh' }}>
      <FeatureCards />
    </main>
  );
}
```

### 4. Custom Cards & Props
```jsx
import { FeatureCards } from './components/FeatureCards';

const myCustomCards = [
  {
    area: 'card-a',
    tag: '01',
    title: 'Custom Feature One',
    description: 'Describe what this feature does.',
    colSpan: 6, // Optional grid column span override
  },
  {
    area: 'card-b',
    tag: '02',
    title: 'Custom Feature Two',
    description: 'Describe what this feature does.',
    colSpan: 6,
  },
];

export default function CustomPage() {
  return (
    <FeatureCards
      eyebrow="PRODUCT FEATURES"
      title="Engineered for Performance"
      cards={myCustomCards}
    />
  );
}
```

### 5. Individual Card Usage
You can also use `<FeatureCard />` anywhere in your own custom layout:
```jsx
import { FeatureCard } from './components/FeatureCards';

export function MyGrid() {
  return (
    <div style={{ maxWidth: '400px' }}>
      <FeatureCard
        tag="PRO"
        title="Standalone Card"
        description="Works inside any custom container or layout."
      />
    </div>
  );
}
```
