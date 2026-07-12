# GPUSTACK causal observatory design system

Status: accepted implementation specification, July 12, 2026.

## Accepted references

- `observatory-desktop-v1.png`, native 1586 by 992: complete desktop surface.
- `observatory-mobile-v1.png`, native 853 by 1844: responsive reading order.
- `observatory-evidence-detail-v1.png`, native 1536 by 1024: dense evidence,
  falsifier, decision-ledger, and timeline anatomy.
- `causal-observatory-brief.md`: authoritative product behavior and copy
  boundary.

The PNGs specify composition, hierarchy, palette, density, and component
geometry. They are not production assets and must never be embedded as UI.
HTML, CSS, SVG, and live experiment artifacts remain authoritative.

## Truth overrides for generated concepts

Image generation introduced three text errors. Implementation must correct
them even where this creates an intentional visual-reference deviation:

1. Published three-decimal losses use a rounding interval of plus or minus
   `0.0005`, not plus or minus `0.001`.
2. The current E001 controller adapts cadence from a completed communication
   cycle. It does not observe an active outage or issue a failure-response
   membership decision. Omit the generated `after failure detected` row.
3. The controlled validation requirement is `30B to 100B-plus`, not `160B`.

Artifact values override all values visible in a generated concept. If an
experiment artifact does not exist or does not report a field, the UI says
`not run`, `unmeasured`, or `unresolved`.

## Visual idea

The observatory is a scientific field notebook crossed with a precise mission
control instrument. It is one continuous evidence surface, not a collection of
dashboard cards. Fine rules, direct labels, aligned tables, and restrained
registration marks carry density. Evidence class is visible through shape,
line style, color, and text.

## Tokens

### Color

```css
--obs-paper: #f3f0e7;
--obs-paper-raised: #f8f5ed;
--obs-paper-deep: #e8e3d8;
--obs-ink: #1e292b;
--obs-ink-soft: #596162;
--obs-rule: #777b76;
--obs-rule-soft: rgba(55, 63, 62, 0.24);
--obs-grid: rgba(51, 83, 79, 0.055);
--obs-teal: #087580;
--obs-teal-dark: #075560;
--obs-orange: #c64d13;
--obs-cobalt: #2456c4;
--obs-red: #b52720;
--obs-focus: #f0a92f;
```

`--obs-paper` is intentionally warm paper, not white. There are no gradients,
glass surfaces, neon glows, or elevated card shadows.

### Typography

- Identity: `Pixelify Sans`, used only for the GPUSTACK mark and restrained
  CuperOS continuity.
- Reading: `IBM Plex Sans`, 15 to 17 pixels, line-height 1.45 to 1.6.
- Values and controls: `IBM Plex Mono`, 12 to 15 pixels.
- Desktop H1: `clamp(2rem, 3vw, 3.25rem)`, weight 600, compact line-height.
- Mobile H1: `clamp(1.85rem, 8vw, 2.55rem)`, never below two readable lines.
- Evidence labels: 0.7 to 0.78rem, uppercase, weight 700, letter spacing 0.04em.

### Spacing and geometry

- Base spacing: 4 pixels.
- Scale: 4, 8, 12, 16, 24, 32, 48, 64.
- Page gutter: 20 pixels desktop, 16 pixels tablet, 14 pixels mobile.
- Control height: 32 pixels compact, 42 pixels touch.
- Rule: 1 pixel; selected evidence can use 2 pixels.
- Radius: 2 pixels for tables and rails, 6 pixels for controls and causal
  nodes, 18 pixels only for the mobile evidence sheet top corners.
- Shadow: none. Separation comes from rules, paper tone, and whitespace.

## Evidence grammar

| Class | Shape | Line | Color | Required label |
|---|---|---|---|---|
| Observed | hatched square | solid | cobalt | `OBSERVED` |
| Modeled | circle | solid | teal | `MODELED` |
| Assumed | ring or warning diamond | dashed | graphite or orange | `ASSUMED` |
| Prior | hexagon | solid | cobalt | `PRIOR · NOT FITTED` |
| Unmeasured | diamond | dashed | red | `UNMEASURED` |

Color is never the sole carrier. Every evidence-bearing component exposes an
accessible text label and a screen-reader description.

## Desktop layout

The desktop surface uses five contiguous bands:

1. Quiet 52-pixel header: identity, three navigation links, experiment
   selector, share state.
2. Question band: semantic-depth control, H1, stage, and immediate answer.
3. Research band: 200-pixel causal reading rail, flexible causal canvas, and
   350 to 380-pixel fixed evidence inspector.
4. Timeline band: three aligned policy tracks and direct legend.
5. Comparison band: open table plus compact timeline controls.

The research band must remain the visual center. The inspector is fixed on
wide screens and never floats as a decorative card.

## Mobile layout

At 760 pixels and below, the order becomes:

1. Sticky compact header with GPUSTACK, experiment selector, and share state.
2. Question, status, answer, and three equal depth tabs.
3. Explicitly pannable site strip with position indicator.
4. Vertical causal path with expandable nodes.
5. Selected evidence sheet in document flow; it may become a bottom sheet only
   while a user has actively selected an event.
6. Numbered causal reading narrative.
7. Stacked or horizontally scrollable comparison table with a visible header.
8. Pannable aligned policy timeline and legend.
9. Full-trace disclosure.

Only the site strip, comparison table, and timeline may scroll horizontally.
The page itself must not overflow.

## Component families

### `obs-header`

Quiet application header. Desktop shows the complete nav. Mobile retains only
identity, experiment control, and share. Current location uses a 2-pixel teal
underline, not a pill.

### `depth-control`

Three real buttons with `aria-pressed`. The selected state uses teal fill and
paper text. Depth changes explanatory density and URL state, never values or
conclusions.

### `site-rail`

Three sites connected by directly labeled WAN links. Site racks use a small
code-native SVG with consistent 1.5-pixel strokes. The selected site receives
an orange 2-pixel border. Link assumptions remain visible at every depth.

### `causal-node`

One reusable anatomy: evidence glyph, label, evidence-class text, disclosure
chevron, selected state. Desktop nodes form a central causal graph. Mobile
nodes form a vertical causal chain using the same data and state.

### `evidence-inspector`

Fixed desktop pane and mobile sheet. Sections are divided by simple rules:
plain meaning, exact value/unit, evidence class, source, uncertainty semantics,
mechanism, transfer boundary, and falsifier. Copy-observation-ID is a real
button with an accessible label.

### `policy-timeline`

SVG rendered from artifact events. It has direct policy labels, top time axis,
visible event legend, selected interval, and an accessible event list fallback.
Essential start/end values are visible without hover. Pointer, keyboard, and
tap selection update the inspector and URL.

### `policy-comparison`

An open table, not score cards. Every cell includes the evidence class.
Learning stays `PRIOR ONLY`; unsupported falsifiers stay `UNRESOLVED`.

### `empty-residual`

An honest ruled plot frame with axes and the message `No held-out multi-site
learning observation`. It contains no synthetic points, curve, residual, or
confidence band.

## Icon inventory

- Share state: three-node share glyph, 1.5-pixel `currentColor` stroke.
- Close inspector: simple X.
- Copy observation ID: overlapping rectangles.
- Site rack: five rack bays with small status lines; no brand logo.
- Site availability: dashed ring.
- Membership: three-person/network glyph.
- Sync cadence: clock.
- Collective payload: four-node network.
- Mechanical elapsed time / learning prior: hourglass variants.
- Unmeasured: diamond.
- Assumed event: warning diamond with exclamation.
- Disclosure: down/right chevron.
- Full trace locked state: small lock.

All icons are inline SVG with a clean `viewBox`, optical centering,
`currentColor`, round line caps where appropriate, and no emoji or text glyph
substitutes.

## Interaction and state

- URL parameters: `experiment`, `policy`, `node`, `event`, `time`, `depth`, and
  `uncertainty`.
- Browser back/forward restores the same observable state.
- Timeline arrow keys move between events. Enter selects. Escape closes a
  transient mobile sheet.
- Site and causal nodes are buttons, not clickable `div` elements.
- Every canvas view has a structured list/table fallback in the DOM.
- `prefers-reduced-motion` disables interpolated timeline and inspector motion.
- Motion is limited to 120 to 180ms selection transitions and scrubber movement.

## Copy lock

Above the fold may contain only the identity, nav, experiment selector,
semantic-depth control, question, stage boundary, immediate answer, causal
labels, site/link facts, selected evidence, and share control defined in the
brief or live artifact. Do not add marketing claims, generic helper badges,
decorative stats, or a CTA.
