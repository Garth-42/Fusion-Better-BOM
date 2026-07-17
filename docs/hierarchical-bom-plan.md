# Hierarchical (Structured) BOM Plan

## Status

Planned scope expansion beyond Deliverable 1. Adds a hierarchical, tree-structured
BOM as a **per-view option** alongside the existing flat, leaf-only BOM. Flat mode
stays the default and is unchanged. `docs/architecture.md` currently lists
"structured BOMs" as a Deliverable 1 non-goal; this plan is the deliberate
decision to lift that gate.

## Decisions (locked)

- **Per-view option.** Each saved table format carries a `structure` mode:
  `flat` (current behavior) or `hierarchical`. One design can hold both a flat
  "General BOM" and a "Structured BOM" view. There is no separate global toggle;
  the selected view decides the mode.
- **Both quantities.** Every hierarchical node exposes a *structured* quantity
  (count directly under its immediate parent) and a *rolled-up total* quantity
  (occurrences in the whole design reached through that path).
- **Shared values.** Custom values stay keyed by component definition
  (`entityToken`). The same part shows the same values everywhere it appears in
  the tree. Per-location overrides remain a deferred roadmap item (assembly
  overrides), so no per-node value storage is introduced here.

## Quantity semantics

For one node, `total_quantity = structured_quantity x parent_total_quantity`,
with the (virtual) root at 1. Example:

```
Root
  Gearbox   x2         structured 2, total 2
    Screw   x4         structured 4, total 8   (4 per gearbox x 2 gearboxes)
    Housing x1         structured 1, total 2
  Bracket   x1         structured 1, total 1
```

A definition reused under two different parents becomes two nodes, each with its
own path-scoped quantities. A leaf's flat-BOM total equals the sum of its
per-node rolled-up totals across the tree.

## Data model

`HierarchicalBomNode` is added; flat `ConceptBomRow` is untouched.

```python
@dataclass
class HierarchicalBomNode:
    row_id: str
    component_name: str
    level: int              # 0-based depth
    parent_id: str | None
    quantity: int           # structured: count under immediate parent
    total_quantity: int     # rolled-up: occurrences in the whole design via this path
    is_assembly: bool
    fusion_part_number: str | None
    fusion_description: str | None
    material: str | None
    linked: bool
    custom_values: dict[str, str]
```

## Work plan

### 1. Scanner + model + tests  — DONE (proof of concept)

- `HierarchicalBomNode` in `domain/models.py`.
- `scan_design_hierarchical(design, field_ids)` in `fusion/assembly_scanner.py`:
  walks `root.occurrences -> childOccurrences` depth-first, aggregates identical
  siblings per parent, computes structured + rolled-up quantities, skips
  suppressed occurrences, reads shared values by definition, and returns
  `(nodes, components)` with the same contract as `scan_design`.
- `tests/test_hierarchical_scanner.py` covers tree flattening/levels, structured
  vs rolled-up quantities, assembly flags/parent links, the components map,
  suppressed exclusion, a definition reused under two parents, legacy values, and
  the empty design.

### 2. Configuration + schema migration

- Add `structure: 'flat' | 'hierarchical'` to `BomTableFormat` (default `flat`).
- Bump `SCHEMA_VERSION` 1 -> 2. In `FusionConfigurationStore.load`, migrate a v1
  document to v2 by defaulting every view to `flat` (no data loss).
- Update `from_dict`, `configuration_to_dict`, and `validate` to carry and check
  the new field.
- Add a default "Structured BOM" view to `default_configuration` (hierarchical;
  columns: Qty, Total Qty, Component, Part Number, Description).

### 3. Table builder passthrough

- Extend `build_table` so a hierarchical view also emits `level`, `parent_id`,
  `is_assembly`, and `total_quantity` per row.
- Expose `total_quantity` as a selectable builtin column.

### 4. Controller routing + edit propagation

- `refresh` chooses `scan_design` vs `scan_design_hierarchical` from the active
  view's `structure`.
- `save_cell` propagates an edit to every cached row sharing the same component,
  since a definition can now appear as several nodes.

### 5. UI

- Render tree rows indented by `level` with expand/collapse per assembly node.
- Sorting: sibling-scoped or disabled in hierarchical mode (a global sort would
  break the tree). Flat mode keeps today's global sort.
- TSV copy: include an indent/level marker so pasted structure stays meaningful.
- View picker reflects the mode; no separate control.

### 6. Docs

- `architecture.md` (remove structured BOM from non-goals; add the per-view mode).
- `domain-model.md` (add `HierarchicalBomNode`).
- `README.md` (update known limitations).
- `manual-fusion-test-plan.md` (hierarchical acceptance checks).

## Deferred robustness (documented, not yet handled)

- Single-part designs with bodies directly under the root component (the flat
  scanner has a fallback; the hierarchical scan currently returns an empty tree
  for a design with no occurrences).
- Designs where `root.occurrences` is unexpectedly empty but `allOccurrences` is
  populated (the flat scanner's `_root_descendants` fallback has no hierarchical
  equivalent yet).
- Components carrying both child occurrences and their own bodies are treated as
  assembly nodes; their own bodies are not emitted as separate leaf rows.

## Estimate

Roughly 3-5 focused days for the full, tested, per-view feature. Step 1 (this
change) is the proof-of-concept core; steps 2-6 are the remaining increments.
