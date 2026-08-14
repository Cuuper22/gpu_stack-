---
name: gpu_stack
description: CuperOS project-window language for a visual-first symbolic GPU training-stack model.
colors:
  desktop-bg: "oklch(0.45 0.10 195)"
  desktop-dot: "oklch(0.50 0.12 195)"
  window-chrome: "oklch(0.85 0.005 250)"
  window-body: "oklch(0.97 0.002 90)"
  title-bar: "oklch(0.40 0.15 260)"
  title-bar-end: "oklch(0.45 0.15 260)"
  text-dark: "oklch(0.15 0.005 250)"
  text-light: "oklch(0.95 0.003 90)"
  accent-cyan: "oklch(0.50 0.10 195)"
  accent-gold: "oklch(0.82 0.15 88)"
typography:
  display:
    fontFamily: "Pixelify Sans, monospace"
    fontSize: "clamp(48px, 8vw, 98px)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "0"
  body:
    fontFamily: "Pixelify Sans, IBM Plex Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.6
    letterSpacing: "0"
  reading:
    fontFamily: "Pixelify Sans, IBM Plex Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.62
    letterSpacing: "0"
  mono:
    fontFamily: "IBM Plex Mono, Courier New, monospace"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.55
    letterSpacing: "0"
rounded:
  none: "0"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "22px"
  xl: "28px"
components:
  window:
    backgroundColor: "{colors.window-chrome}"
    textColor: "{colors.text-dark}"
    rounded: "{rounded.none}"
    padding: "4px"
  title-bar:
    backgroundColor: "{colors.title-bar}"
    textColor: "{colors.text-light}"
    rounded: "{rounded.none}"
    padding: "5px 7px"
  retro-button:
    backgroundColor: "{colors.window-chrome}"
    textColor: "{colors.text-dark}"
    rounded: "{rounded.none}"
    padding: "5px 10px"
---

# Design System: gpu_stack

## 1. Overview

**Creative North Star: "A project window inside CuperOS"**

The idea is simple. Cuper's portfolio site is styled as a retro operating system called CuperOS. The GitHub Pages site for this project must look like one window inside that OS, not like a separate AI-generated landing page. That means a teal dotted desktop, zero-radius window chrome, indigo title bars, pixel icons, inset content panes, a taskbar, and project copy that sounds human, technical, and slightly amused.

The README stays a GitHub-rendered article. But any browser page for the project inherits the CuperOS design language. The page can be visual and interactive, as long as it behaves like an OS control surface and never like a full-bleed marketing hero.

**Key Characteristics:**
- Pixel OS chrome first, modern landing-page composition never.
- Display type uses Pixelify Sans. Reading copy uses IBM Plex Sans. Commands use IBM Plex Mono.
- Border radius is zero. Depth comes from outset, inset, and 2px pixel shadows.
- The site teaches the stack by making files, windows, controls, and dependency panes inspectable.

## 2. Colors

The palette comes straight from the portfolio OS: teal desktop, gray chrome, indigo title bars, off-white document panes, and small utility accents. Nothing here is new.

### Primary
- **CuperOS Indigo** (`title-bar`, `title-bar-end`): title bars, selected controls, primary project identity.

### Secondary
- **Desktop Teal** (`desktop-bg`, `desktop-dot`): the surrounding operating-system surface.
- **Attention Gold** (`accent-gold`): warnings, active output rows, small status emphasis.

### Neutral
- **Window Chrome** (`window-chrome`): OS frames, controls, and button faces.
- **Document Body** (`window-body`): readable panes and article surfaces.
- **Console Ink** (`text-dark`, `text-light`): body text and title-bar text.

### Named Rules

**The No New Brand Rule.** Do not invent a separate gpu_stack palette. The project page is a child window inside CuperOS, so it uses the parent's colors.

**The Small Accent Rule.** Gold, green, and red are status lights, not brand washes. Use them as signals, never as backgrounds.

## 3. Typography

**The Font Law (portfolio-wide, per Cuper):** every rendered glyph, at every size and in every role, comes from the approved pixel set: DotGothic16, Pixelify Sans, VT323, Handjet, or Silkscreen. No other typeface ever renders. No exceptions for paragraphs, tables, code, or fine print.

**Current mapping:** Pixelify Sans carries the interface and all prose (headings, buttons, labels, status lines, paragraphs). VT323, the terminal face, carries commands, identifiers, numeric values, intervals, tables, and console output. The other three approved faces are available but unused here.

**Legibility floor:** pixel faces break down under about 11px, so nothing renders smaller. Dense instrument fine print sits at 0.7rem minimum, chart ticks at 11px.

**Character:** The pixel face IS the voice of the OS, everywhere, at every size.

### Hierarchy
- **Display** (700, `clamp(48px, 8vw, 98px)`, 1.05): page title and very large OS labels only.
- **Headline** (700, `clamp(30px, 4vw, 50px)`, 1.05): window-section titles.
- **Title** (700, `20px`, 1.05): pane titles and dialog headings.
- **Body** (500, `15px`, 1.62): explanatory prose, capped near 65-75 characters when possible.
- **Label** (700, `13px`, 1.2): file paths, status labels, tabs, window title text.

### Named Rules

**The Pixel Display Rule.** Pixelify Sans carries chrome, titles, buttons, labels, and all interface copy, exactly like the portfolio. Only two things escape it: multi-sentence reading paragraphs (Plex Sans) and data values, commands, and identifiers (Plex Mono).

**The No Negative Tracking Rule.** Letter spacing stays at `0`.

## 4. Elevation

Depth here is not blur, glass, or soft shadow. It is the physical model of a retro OS: `2px outset` for buttons and frames, `2px inset` for content wells, and a crisp `2px 2px 0` shadow behind windows. A surface looks raised or sunken because its border says so.

### Shadow Vocabulary
- **Pixel Window Shadow** (`2px 2px 0 oklch(0.08 0.004 250)`): top-level windows only.
- **Inset Pane** (`border: 2px inset var(--window-chrome)`): documents, consoles, diagrams, stats, and visual wells.
- **Outset Control** (`border: 2px outset var(--button-face)`): buttons, tabs, and fake OS controls.

### Named Rules

**The Chrome Is Structure Rule.** If an element needs hierarchy, give it a real OS affordance: a title bar, an inset pane, a status light, or a taskbar entry. Do not fake hierarchy with decorative cards.

## 5. Components

### Windows
- **Shape:** square corners (`0` radius).
- **Frame:** `2px outset` gray chrome with a crisp 2px pixel shadow.
- **Title bar:** indigo gradient, Pixelify Sans, icon plus filename.
- **Content:** off-white document body inset into the frame.

### Buttons
- **Shape:** square corners (`0` radius), minimum 36px high.
- **Primary:** selected state uses the indigo title bar color with light text.
- **Hover / Focus:** hover slightly lightens chrome; focus uses a gold outline.
- **Active:** border switches to inset.

### Navigation
- **Style:** file-tree buttons in a left OS pane on desktop, stacked above content on mobile.
- **Labels:** concrete file/app names such as `CLI.exe`, `layers.sys`, `README.md`.

### Diagrams and Visual Panes
- **Style:** diagrams live inside inset document wells, never as a full-bleed hero background.
- **Caption:** one short IBM Plex Sans sentence under the visual.

### Console
- **Style:** dark terminal inset with green mono text.
- **Purpose:** runnable commands and output-like examples only.

## 6. Do's and Don'ts

### Do:
- **Do** preserve the CuperOS desktop metaphor from the portfolio.
- **Do** use Pixelify Sans for OS chrome and IBM Plex Sans for readable explanation.
- **Do** show the stack before explaining the stack.
- **Do** expose root inputs as visible modeling debt.
- **Do** make interactive controls look like OS controls, not SaaS pills.
- **Do** keep diagrams inspectable inside panes with real alt text.

### Don't:
- **Don't** make the GitHub.io page look like a standalone SaaS landing page.
- **Don't** use full-bleed datacenter hero imagery as the primary identity.
- **Don't** use feature-card grids, hero metrics, glassmorphism, gradient text, or purple-blue AI gradients.
- **Don't** use rounded cards inside rounded cards.
- **Don't** use em dashes in page copy.
- **Don't** introduce a new design system when the portfolio already has one.
