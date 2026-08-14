# README Voice Direction

## 1. Compact Diagnosis

The current README is technically credible and brutally complete, but it reads like the registry exported its own autobiography. The useful signal is all there: 16 systems, 1517 variables, 959 equations, 0 cycles, unit checks, scenario tooling, graph consistency, real tests. The problem is simpler: the human entry point arrives too late.

The opening should not begin by proving the package is serious. It should begin with the question that made the project inevitable: what actually happens between "I trained a model" and the physics bill arriving? The current text has the rigor but buries the curiosity under a wall of implementation detail. The fix is ordering: a visual-first mental model, then the graph, then the audit numbers.

The best version should feel like Cuper writing a Medium article for technical people: reflective, specific, a little dry, allergic to hype, and willing to admit that modeling the GPU stack from quarks to cost per token is a deeply unreasonable thing to do. Not impossible. Just the kind of unreasonable that becomes useful once it is made explicit.

## 2. CuperVoice Style Guide For This README

- Lead with the itch, not the package. Start from the conceptual frustration: AI training is discussed as tokens, FLOPs, GPUs, money, and vibes, but those are all connected by equations.
- Make the first screen visual. Give the reader a shape: quarks to nuclei, nuclei to lithography, lithography to transistors, transistors to memory and compute, compute to kernels, kernels to collectives, collectives to training throughput, throughput to dollars.
- Use professional reflective voice. Full sentences, precise claims, no casual abbreviations, no internet persona. This is public technical writing, not a DM.
- Let dry humor come from the absurdity of the object. The joke is that the model keeps walking downward until "GPU training stack" includes valence quarks. Do not add punchlines.
- Be rigorous without front-loading the dump truck. Keep the verification numbers, but introduce them as proof after the reader understands the shape.
- Prefer diagnostic sentences. "This is not a simulator yet. It is a symbolic map of the assumptions a simulator would need to stop hiding."
- Name concrete systems instead of gesturing. Use `MFU`, `HBM`, `NVLink`, `AllReduce`, `PUE`, `cost_per_token`, and `root-debt` when they matter, and define acronyms on first use where the README can do so gracefully.
- Keep root inputs philosophically interesting. A root is not an embarrassment. It is exposed modeling debt, which is much better than hidden modeling debt wearing a lab coat.
- Preserve the current factual backbone. Do not soften the numbers, test counts, cycle status, or limitations. The voice can become human without becoming less exact.
- Use section titles that sound like a person thinking: "The Shape Of The Stack", "What The Graph Knows", "What Is Still Debt", "Try It Without Believing Me".

## 3. Candidate Opening Paragraphs

### Option A

`gpu_stack` started as a question I could not leave alone: if frontier training is supposedly just "more GPUs, more data, more money," where does that sentence actually bottom out? Not rhetorically. Physically. A token goes through model architecture, kernels, collectives, memory bandwidth, transistor switching, lithography, materials, thermals, power delivery, and eventually a cost line item that someone has to pay. The stack is usually explained in slices. I wanted the uncomfortable version where the slices have to talk to each other.

### Option B

This is a symbolic map of the GPU training stack, from the parts people argue about on Twitter to the parts that quietly decide whether the argument can exist. `gpu_stack` connects semiconductor physics, memory hierarchy, arithmetic units, kernels, collectives, transformer training, cluster topology, cooling, facility power, and run economics in one graph. It also goes lower than a normal person would choose to go, which is how a GPU package ended up with valence quarks in it. I promise there was a path. It just kept descending.

### Option C

Most AI infrastructure writing starts in the middle. It talks about model flops utilization, HBM bandwidth, all-reduce latency, GPU count, dollars per token, or power constraints as if those are separate weather systems. They are not. They are different faces of one stack. `gpu_stack` is my attempt to make that stack explicit: a SymPy-backed graph where equations can be inspected, dependencies can be walked, units can complain, and missing assumptions cannot politely hide behind a benchmark chart.

## 4. Never-Write List For This README

- "Democratizing GPU infrastructure"
- "Unlocking insights"
- "End-to-end solution"
- "Game-changing"
- "Production-ready simulator"
- "Seamlessly bridges"
- "Powerful yet intuitive"
- "Designed for researchers, engineers, and enthusiasts"
- "Whether you're..."
- "Dive in"
- "The future of AI infrastructure"
- "Just"
- "Simply"
- "Magic"
- Any claim that implies calibrated hardware truth when the README really means symbolic substrate.
- Any joke that sounds like it was added because the style guide requested humor.
