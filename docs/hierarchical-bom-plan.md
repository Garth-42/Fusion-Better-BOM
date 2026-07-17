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

### 2. Configuration + schema migration  — DONE

- `structure: 'flat' | 'hierarchical'` added to `BomTableFormat` (default `flat`),
  emitted by `configuration_to_dict` and validated against `STRUCTURES`.
- `SCHEMA_VERSION` bumped 1 -> 2. `_migrate` (called by `from_dict`, so every
  load and every UI round-trip goes through it) upgrades a v1 document by bumping
  the version; `from_dict` then defaults each existing view to `flat`, so no
  stored field or column data is lost. Unknown versions are still rejected.
- Default "Structured BOM" view added to `default_configuration` (hierarchical;
  columns: Qty, Total Qty, Component, Part Number, Description) and protected from
  deletion alongside the other default views.
- `tests/test_configuration.py` covers v1 -> v2 migration, the hierarchical
  default view, structure round-trip, and rejection of an invalid structure.

Note: until step 4 routes the scan by mode, selecting "Structured BOM" renders
flat scan data (no tree, blank Total Qty). The schema and storage are ready.

### 3. Table builder passthrough  — DONE

- `build_table` tags every table with the view's `structure`, and for a
  hierarchical view emits `level`, `parent_id`, and `is_assembly` per row.
  `total_quantity` rides the normal builtin-column path (default '' for flat
  rows) and is a column in the default Structured BOM view.
- Tests: flat views report `structure: flat` and carry no tree metadata;
  hierarchical views emit levels, parent links, assembly flags, and total qty.

### 4. Controller routing + edit propagation  — DONE

- `refresh(view_id)` resolves the active view and scans with `scan_design` or
  `scan_design_hierarchical` from its `structure`; state is sent for that view.
- The web view picker re-scans when the selected view's structure differs from
  the rendered one (flat leaves vs tree nodes are differently shaped), instead
  of only re-filtering columns.
- `save_cell` propagates the edit to every cached row that resolves to the same
  component (`_same_component` matches by entityToken, identity fallback), so all
  nodes for one definition stay in sync; a flat scan matches exactly one row.
- Tests: a hierarchical view routes to the tree scan; one cell edit updates every
  row sharing a component.

Remaining for the tree to render as a tree: step 5 (indentation, expand/collapse).
Until then a hierarchical view lists all nodes flat, with correct quantities.

### 5. UI  — DONE

- Tree rows indent by `level`; the expand/collapse caret sits on the Component
  column (first column if a view omits Component). Assembly rows are tinted and
  bold. Collapsing hides descendants via a parent-chain walk.
- Sorting is suppressed in hierarchical mode (a global sort would break nesting);
  flat mode keeps today's per-column sort. Sibling-scoped sort is a future option.
- TSV copy walks the visible rows in tree order and indents the Component value
  two spaces per level, so the pasted outline keeps its shape.
- The view picker re-scans when switching between flat and hierarchical views.
  The format editor also carries a **Structure** selector so any format can be
  flipped between flat and hierarchical; changing the on-screen format's
  structure re-scans so the table redraws in the new shape. Duplicating/"Save as"
  from a hierarchical view keeps its structure.
- A design configured before the hierarchical "Structured BOM" default shipped
  gains it on load: `_ensure_default_views` restores any missing built-in format
  (migration alone only bumps the schema version), so the option always appears.
- Verified headless (DOM-stubbed): expand/collapse, caret placement and flip,
  descendant hiding, indented TSV, and no change to flat rendering.

Deferred UI polish: live-updating sibling cells for a shared definition on cell
edit (values are already correct on the next render/refresh); sibling-scoped
column sort.

### 6. Docs  — DONE

- `architecture.md`: structured BOM removed from Deliverable 1 non-goals; the
  per-view hierarchical scan documented in the assembly model.
- `domain-model.md`: `HierarchicalBomNode` documented alongside the flat model.
- `README.md`: scan description and known limitations updated for the tree view.
- `manual-fusion-test-plan.md`: a Structured BOM acceptance checklist added.
- `CHANGELOG.md`: unreleased entry for the feature and the schema v2 migration.

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
