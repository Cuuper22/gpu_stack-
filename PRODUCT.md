# Product

## Register

brand

## Users

`gpu_stack` is for builders, students, researchers, and curious technical readers who want to understand frontier training infrastructure without treating it as a sealed industrial magic box. The reader may know Python, ML, physics, GPUs, or none of those deeply yet. The README should state the project's real scale and track record first, then let the equations become less intimidating.

## Product Purpose

`gpu_stack` is an equation graph of the AI training stack plus a small event
simulator and experiment program. The goal is a causal, uncertainty-aware virtual
datacenter. It is not there. The graph is not a validated predictor: as shipped it
was about 3x too fast against published runs, and with a utilization prior it only
matches plain 6ND arithmetic.
Nothing in the engine is fitted to a measurement. The main README says what the
experiments showed.

The same project has three jobs:

1. Be inspectable: trace any number to its equations, units, sources and assumptions.
2. Explain results at several depths, from a plain question to raw observations.
3. Screen hypotheses cheaply, with frozen gates that can fail, and report both wins and losses.

Predicting real outcomes well enough to support decisions is the aim, not a current
claim. A simulation result is a hypothesis. It becomes evidence about a real
datacenter only after measurements validate it. A deeper lithography or particle
relation counts as progress only when it improves an externally evaluated prediction
or explains a residual. The sensitivity study found those layers have no numeric effect today.

## Brand Personality

Curious, rigorous, visual, slightly allergic to fake polish. It should feel like Cuper wrote a technical Medium article after falling into a physics rabbit hole with an AI collaborator and deciding the right response was to build the rabbit hole.

## Anti-references

Do not make it sound like a SaaS landing page, a package index stub, or a generic AI-generated README. Avoid empty hype, feature-card grids, "passionate about", "game changer", inflated claims, and trophy-stat chest beating. No em dashes.

## Design Principles

1. Show the stack, and say how much of it is evidence.
2. Treat root inputs honestly as visible modeling debt, not embarrassing gaps.
3. Keep the human origin in frame: this started as a learning project, not a product committee.
4. Let equations feel spatial and inspectable.
5. Preserve factual claims by tying them to commands or generated registry stats.
6. Rank work by predictive error, uncertainty, and scientific leverage, not equation or root counts.
7. Keep observations, calibration data, assumptions, predictions, and interventions as distinct types.
8. Evaluate decisions on held-out systems. Never grade the engine on the data used to tune it.
9. Use semantic zoom: every visual claim must open into its mechanism, evidence, caveats, and equations.
10. Design experiments with explicit falsifiers, check that the gates can pass and fail, and freeze them before the run.

## Accessibility & Inclusion

The README should be readable in plain GitHub Markdown, work without JavaScript, use alt text for every image, keep diagrams understandable in grayscale, and avoid assuming the reader already knows GPU infrastructure jargon. Define shorthand near first use when practical.
