# Visual README Fragments

Use these snippets near the top of `README.md` when the README is ready to move from registry summary into visual explanation. The intent is to show the stack before naming every subsystem.

## Opening Visual

Suggested placement: directly under the `# gpu_stack` heading, before the first long package description.

```markdown
![Dependency cone from datacenter economics down through GPU systems, transistor physics, lithography, atoms, nucleons, quarks, and equations.](docs/assets/readme-equation-cone.svg)

`gpu_stack` treats the training stack like one inspectable dependency cone. Start with a question such as "what sets cost per token?" or "why did throughput move?", then walk downward: datacenter, rack, GPU, memory, kernel, model math, thermal plant, lithography, atoms, and finally the primitive roots the model still asks you to supply.
```

Alt text:

```text
Dependency cone from datacenter economics down through GPU systems, transistor physics, lithography, atoms, nucleons, quarks, and equations.
```

Caption option:

```markdown
Each box is not a slide-deck layer. It is a registered symbolic neighborhood. Variables know what defines them, equations know what they depend on, and unresolved roots stay visible instead of being hidden behind fake defaults.
```

## 3Blue1Brown-Style Intuition, With Cuper's Spin

Suggested placement: after the first paragraph or after "Design rules."

```markdown
The mental picture is a cone of explanations.

At the wide end are questions humans actually ask: how expensive is this run, how fast do tokens move, how much site power disappears into cooling? At the narrow end are things the model refuses to pretend away: pulse fluence, gate geometry, medium composition, proton and neutron counts, valence quark roots, and universal constants.

Most tooling stops at the first satisfying number. `gpu_stack` is built to keep asking "what is that number made of?" until the answer is either an equation, a cited scenario value, a universal constant, or an exposed root input.
```

## Tiny Dependency-Cone Demo

Suggested placement: before the existing "Export a graph slice" section, or as a replacement for the first purely textual registry demo.

````markdown
### See one output as a cone

```python
import gpu_stack
from gpu_stack import Registry, subgraph

target = Registry.variables["econ.cost.per_token"]
cone = subgraph(target, direction="dependencies")

print(target.name)
print(f"{len(cone)} variables upstream")
print("first few roots:")

for var in sorted(v for v in cone if v.is_root_input)[:12]:
    print("  ", var.name, f"[{var.units}]")
```

The important part is not the exact count. It is the posture: every cost number has an ancestry, and every unresolved ancestor is named.
````

Note for integration: the nested Python fence above needs escaping if pasted into another fenced block. In normal README Markdown, paste it exactly as shown with the outer prose removed.

## Visual Status Table Snippet

Suggested placement: near "Current snapshot."

```markdown
| What the visual cone means | Current registry evidence |
|---|---:|
| Named symbolic quantities | 1517 variables |
| Relations between quantities | 959 equations |
| Exposed primitive assumptions | 619 root inputs |
| Graph loops hiding in the model | 0 cycles |
| Equations with unit checks | 799 |
```

This keeps the stats attached to the visual claim: the README is not saying "a big system" in the abstract. It is saying "a directed symbolic graph you can inspect."

## Future Visual Demos

Suggested placement: near the end, after limitations.

```markdown
## Next visual demos

- A live dependency-cone browser for `econ.cost.per_token`, `training.tokens_per_second`, and `thermal.dc.pue`.
- A root-debt heatmap where unresolved assumptions glow by downstream blast radius.
- A layer slider that walks from quark-count roots to lithography to transistor delay to GPU peak FLOPs to training step time.
- A scenario trace view that shows which equations fired, which constraints were checked, and which roots stayed missing.
```

## Tone Notes

- Prefer "what is this number made of?" over "end-to-end modeling platform."
- Define shorthand near first use: MFU means Model FLOPs Utilization, PUE means Power Usage Effectiveness, HBM means High Bandwidth Memory.
- Keep root inputs honest. They are not failure. They are visible modeling debt.
- Do not let the README become only a stats trophy case. The numbers are evidence for the visual story.
