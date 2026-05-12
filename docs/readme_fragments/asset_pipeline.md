## Visual-first demos and future 3D assets

`gpu_stack` is already a dependency graph, but the next demo layer should make that graph inspectable before it asks anyone to read a wall of equations. Future visual-first demos should treat scopes as spatial systems: lithography source physics, MOSFET geometry, memory hierarchy, rack topology, thermal plant, and economics should each have a small interactive view that can load scenario data, highlight dependency cones, and show which root inputs still carry modeling debt.

For browser 3D, the runtime contract should be GLB or glTF 2.0, optimized after export and checked before landing in the repo. Source files may live elsewhere, but README-facing assets should be predictable: stable names, normalized transforms, known units, explicit pivots, reused materials, compressed geometry where useful, and texture sizes tied to actual screen use.

The equations should feel like space: every symbol is a coordinate in a causal machine, and every dependency edge is a visible path through silicon, memory, cooling, and cost.

### Asset naming and budgets

- Use lowercase kebab-case names with the scope first: `physical-lithography-source.glb`, `gpu-sm-tile-budget.glb`, `cluster-rack-bisection.glb`, `thermal-cdu-loop.glb`.
- Pair every shipped asset with a small metadata note using the same stem: `physical-lithography-source.md` or `physical-lithography-source.json`.
- Keep README demo assets lightweight: target `<= 1 MB` compressed GLB for inline demos, `<= 3 MB` for detailed explainer scenes, and split anything larger into lazy-loaded scope packs.
- Keep triangle counts proportional to purpose: `<= 20k` triangles for small symbolic props, `<= 75k` for full explainer scenes, with LODs or simplified alternates for repeated rack, GPU, or node elements.
- Keep material count low: prefer shared materials per scope family, avoid one-off glossy exports, and cap texture resolution at `1024px` unless the asset is inspected close-up.
- Prefer Meshopt compression for general web delivery. Use Draco only when decode cost and runtime compatibility are acceptable. Use KTX2/BasisU textures when the chosen runtime supports them.

### Future 3D explainer checklist

- [ ] The asset has a named scope, target concept, and scenario data source.
- [ ] GLB or glTF 2.0 is the shipped format, not FBX, OBJ, Blend, or raw DCC output.
- [ ] Units, orientation, transforms, pivots, and scale are normalized before export.
- [ ] Node hierarchy and mesh names are meaningful enough for runtime highlighting.
- [ ] Materials are reused, textures are compressed, and unused data is pruned with glTF Transform.
- [ ] Any clickable, animated, or physics-relevant geometry has explicit interaction or collision proxies.
- [ ] Large repeated structures have an instancing or LOD plan.
- [ ] The asset can load in the target web runtime without console errors, missing textures, or layout-dependent camera hacks.
- [ ] The README fallback remains useful when WebGL is unavailable: static image, short caption, or exported graph slice.
