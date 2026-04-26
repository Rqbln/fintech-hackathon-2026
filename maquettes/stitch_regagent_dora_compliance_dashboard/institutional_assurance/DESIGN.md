---
name: Institutional Assurance
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#2a1700'
  on-tertiary-container: '#b87500'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h1:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  h2:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  h3:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 20px
  container-max: 1440px
---

## Brand & Style

This design system is engineered for high-stakes regulatory environments where precision is paramount. The aesthetic follows a **Modern Corporate** movement—marrying the density requirements of financial data with the sophisticated air of a premium SaaS platform. 

The visual language communicates authority and meticulousness. It avoids unnecessary decoration, opting instead for structural clarity and "white-glove" professional finishes. The user should feel a sense of absolute control and systematic organization, achieved through a rigorous grid, deliberate use of semantic color, and a refined tactile quality.

## Colors

The palette is anchored by **Deep Navy (#0F172A)**, evoking the stability of traditional institutional finance. The background utilizes **Slate-50**, providing a cooler, more professional canvas than pure white, which reduces eye strain during long periods of data auditing.

Semantic colors are the primary vehicles for communication:
- **Emerald Green (#10B981):** Signals "Compliant" or "Low Risk." Used for positive trend lines and success states.
- **Amber (#F59E0B):** Signals "Warning" or "Action Required." Used for pending reviews and medium-risk flags.
- **Rose Red (#E11D48):** Signals "Critical" or "Non-Compliant." Used for immediate blockers and high-risk alerts.

## Typography

The design system utilizes **Inter** exclusively to ensure a utilitarian and neutral tone. The typographic scale is optimized for high information density without sacrificing legibility. 

Systematic use of font-weight creates hierarchy: Bold headers for section titles, Medium weights for data labels, and Regular weights for tabular data entries. For data-heavy tables, `body-sm` is the standard to allow more rows per viewport, while `label-sm` with uppercase tracking is reserved for metadata and column headers to provide distinct visual separation from the content.

## Layout & Spacing

This design system employs a **Fixed Grid** philosophy for dashboard views and a fluid approach for internal workspace modules. The primary layout uses a 12-column grid with a 20px gutter.

A 4px baseline grid ensures tight vertical rhythm, essential for the "high-density" requirement. Padding within components (like table cells or card headers) should remain compact—typically using `md` (16px) for external card padding and `sm` (8px) for internal element grouping. This maximizes the visible data area while maintaining a clean, breathable structure.

## Elevation & Depth

To maintain a crisp, professional look, elevation is used sparingly. This design system avoids heavy shadows in favor of **Tonal Layering** and **Subtle Outlines**.

- **Surface Level 0:** The Slate-50 background.
- **Surface Level 1:** Pure White (#FFFFFF) cards and containers.
- **Shadows:** Use a "Shadow-sm" approach for cards: a 1px border (#E2E8F0) combined with a very soft, diffused drop shadow (Offset 0, 1px; Blur 3px; Opacity 5% Black).
- **Interactive Depth:** On hover, buttons and interactive cards may lift slightly with a more pronounced but still subtle shadow to provide tactile feedback without breaking the institutional aesthetic.

## Shapes

The shape language balances modern software trends with corporate discipline. 
- **Standard UI Elements:** Buttons, inputs, and small containers use a 0.5rem (8px) radius.
- **Dashboard Cards:** Use the `rounded-xl` specification (1.5rem / 24px) to create a soft, distinct container for high-level data clusters.
- **Badges:** Use a "Pill" shape (full radius) to distinguish them from interactive buttons.
- **Tables:** Maintain sharp corners or very minimal 4px radius on the outer container to preserve the "grid-like" integrity of complex data sets.

## Components

### Buttons
Primary buttons use the Deep Navy (#0F172A) background with white text. Secondary buttons use a white background with a subtle slate border. Buttons should have a height of 36px or 40px to remain compact.

### Risk Scoring Badges
Badges are the most critical visual indicator. They use a "Subtle Solid" style: a light tinted background of the semantic color (e.g., 10% Emerald) with high-contrast text of the same color (e.g., 100% Emerald). This ensures readability without overwhelming the user's vision with saturated blocks.

### Tables
Tables are the workhorse of this system. They must feature:
- Sticky headers for long audits.
- Zebra striping using Slate-50 on alternate rows.
- Condensed vertical padding (8px to 12px) to support high-density viewing.
- Border-bottom only on rows to emphasize the horizontal flow of data.

### Sleek Cards
Cards serve as the primary organizational unit. Every card features a white background, `rounded-xl` corners, and a `shadow-sm` border. Section headers within cards should be separated by a fine 1px slate divider.

### Form Inputs
Inputs use a white background with a 1px Slate-200 border. On focus, the border transitions to Primary Navy with a subtle 2px glow of the same color at 10% opacity. Labels are always positioned above the input in `label-md` style.