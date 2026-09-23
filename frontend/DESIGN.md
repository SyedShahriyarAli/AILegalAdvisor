---
name: Cyber-Legal Executive System
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
  on-surface-variant: '#43474e'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#74777f'
  outline-variant: '#c4c6cf'
  surface-tint: '#455f88'
  primary: '#002045'
  on-primary: '#ffffff'
  primary-container: '#1a365d'
  on-primary-container: '#86a0cd'
  inverse-primary: '#adc7f7'
  secondary: '#28657a'
  on-secondary: '#ffffff'
  secondary-container: '#abe5fe'
  on-secondary-container: '#2b687d'
  tertiary: '#1b2127'
  on-tertiary: '#ffffff'
  tertiary-container: '#30363c'
  on-tertiary-container: '#989fa6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d6e3ff'
  primary-fixed-dim: '#adc7f7'
  on-primary-fixed: '#001b3c'
  on-primary-fixed-variant: '#2d476f'
  secondary-fixed: '#b9eaff'
  secondary-fixed-dim: '#95cfe7'
  on-secondary-fixed: '#001f29'
  on-secondary-fixed-variant: '#004d61'
  tertiary-fixed: '#dde3eb'
  tertiary-fixed-dim: '#c1c7cf'
  on-tertiary-fixed: '#161c22'
  on-tertiary-fixed-variant: '#41474e'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-xl:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.08em
  mono-technical:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.4'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-max: 1200px
  gutter: 24px
  margin-edge: 32px
  stepper-width: 280px
  stack-gap: 16px
  section-padding: 80px
---

## Brand & Style

The brand personality is authoritative yet approachable, positioning the service as the premier intersection of high-stakes litigation and deep technical forensics. The target audience includes C-suite executives, legal departments, and high-net-worth individuals facing digital threats. 

The visual style is **Corporate Modern with Glassmorphism accents**. It prioritizes a "high-definition" clarity that reflects precision and expert counsel. By using a light, airy aesthetic, the system counters the typically dark and chaotic imagery associated with cybercrime, offering instead a sense of calm, controlled resolution. Visual elements use precise 1px borders and layered transparency to suggest depth and a multi-dimensional understanding of complex digital law.

## Colors

The palette is anchored by **Legal Blue**, a deep, saturated navy that commands respect and establishes institutional trust. **Cyber Teal** serves as the technical bridge, used for interactive elements and data visualization to signify modern expertise. **Soft Slate** provides a sophisticated neutral foundation, moving away from harsh blacks to maintain an airy, high-end feel.

High contrast is maintained between text and backgrounds to ensure professional legibility. Glassmorphism effects utilize a semi-transparent white with a heavy background blur (20px+) to create "floating" surfaces without the weight of solid shadows.

## Typography

This design system utilizes a dual-font strategy. **Geist** is used for headlines, navigation, and technical labels to provide a precise, engineered feel. Its monospaced-adjacent geometry conveys the "cyber" aspect of the brand. **Inter** is used for all body copy and legal documentation, selected for its exceptional readability and neutral, professional tone.

Hierarchy is strictly enforced through weight and scale. Large display titles are tightly tracked for a premium editorial look, while body copy remains spacious to reduce the perceived density of legal information.

## Layout & Spacing

The layout follows a **Fixed Grid** model for desktop to maintain a prestigious, centered focus, transitioning to a flexible fluid model for mobile. A signature **Stepper-Lateral layout** is employed for complex workflows: a fixed left-hand vertical stepper guides the user through the legal process, while the right-hand content area remains airy and uncluttered.

Generous white space (80px+ between major sections) is non-negotiable to prevent cognitive overload. Padding within cards and modals is intentionally large (min 32px) to signify a "luxury of space" typical of high-end consulting services.

## Elevation & Depth

Depth is achieved through **Tonal Layering and Glassmorphism** rather than traditional heavy shadows. 

1.  **Base Layer:** Soft Slate 50 (Off-white).
2.  **Surface Layer:** Pure White cards with a subtle 1px border in `border-subtle`.
3.  **Raised Layer:** Glassmorphic panels with 70% opacity, 24px background blur, and a faint 1px white inner-stroke to simulate light hitting an edge.
4.  **Shadows:** When necessary, use "Ambient Light" shadows—extremely diffused (30px-40px blur) with very low opacity (3-5%) using the `legal-blue` tint.

This creates a sense of "layered intelligence," where information feels systematically organized in a clear, digital space.

## Shapes

The shape language is **Soft and Precise**. A base radius of 4px (`rounded-sm`) is used for technical elements like input fields and code blocks to maintain a sharp, professional edge. Larger components like cards and buttons use 8px (`rounded-lg`) to feel more modern and approachable. 

The "Path Traversal" loader uses circular geometry, while knowledge graph nodes are perfectly spherical to differentiate technical data visualizations from standard UI components. Interactive paths in the graph are 2px wide, using Cyber Teal with a glowing terminal point.

## Components

### Stepper Navigation
Vertical orientation. Completed steps use a Legal Blue checkmark; active steps feature a subtle Cyber Teal pulse. Text is Geist Semi-bold.

### Path Traversal Loader
A custom animation representing a data packet moving through a labyrinth. It uses a 3px stroke of Cyber Teal, animating along a geometric grid path. It should feel rhythmic and precise, not frantic.

### Knowledge Graph Nodes
Interactive points in a legal-technical web.
- **Default:** Legal Blue fill, 12px diameter.
- **Active/Hover:** Scale to 16px, Cyber Teal glow (5px blur).
- **Connections:** Light Slate 200 lines that thicken and turn Cyber Teal when the connecting nodes are relevant to the current case step.

### Buttons
- **Primary:** Legal Blue background, white Geist text, 8px radius. Subtle lift on hover.
- **Ghost:** Transparent background, 1px Legal Blue border.
- **Technical:** Cyber Teal background, used only for "Execute" or "Analyze" actions.

### Cards
Pure white background, 1px `border-subtle`, 8px radius. Floating effect is achieved via the Ambient Shadow defined in the Elevation section.