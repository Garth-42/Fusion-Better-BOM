# Manual Fusion Test Plan

## Installation

1. In Fusion, open **Utilities > Add-Ins > Scripts and Add-Ins**.
2. Select **Add-Ins**, click the green `+`, and select the `FusionConfigurableBOM` directory.
3. Run **Fusion Configurable BOM**, then use **Utilities > Add-Ins > Open Configurable BOM**.

The add-in uses its own palette and does **not** modify Fusion's native BOM UI.

## Acceptance checklist

Create an assembly with one unique local leaf, three occurrences of another local leaf, one nested leaf, one externally linked leaf, and two distinct components sharing a display name.

- [ ] Palette opens, docks, refreshes, and reports an error instead of crashing with no active design.
- [ ] One row appears for each component definition; the repeated local component has quantity 3.
- [ ] Same-name components remain separate rows.
- [ ] Create a custom field, set a local value, save/close/reopen the design, and confirm the value persists.
- [ ] Confirm repeated occurrences share the component Attribute value.
- [ ] Confirm a linked component appears with a lock and cannot be edited in the parent design.
- [ ] Rename a field header in one format and confirm its data remains unchanged.
- [ ] Switch between General BOM and Purchasing Demo; confirm a shared field can use different headers.
- [ ] Duplicate, rename, reorder, hide/show, and delete a user-created format; save/reopen and confirm persistence.
- [ ] Stop and rerun the add-in twice; confirm only one toolbar control exists and no handler errors occur.

### Structured (hierarchical) BOM

Use an assembly with at least one sub-assembly that appears more than once, each containing several leaves.

- [ ] Select the **Structured BOM** format; the palette re-scans and shows sub-assemblies as parent rows with their children indented beneath.
- [ ] A repeated sub-assembly shows its per-parent quantity, and each child's **Total Qty** equals its per-parent count times the number of sub-assembly instances.
- [ ] Click a sub-assembly caret to collapse and expand it; descendants hide and reappear and the caret flips.
- [ ] Copy table and paste into a spreadsheet; tree order and the indented outline are preserved.
- [ ] Edit a custom cell on a component that appears in more than one place; after Refresh, every node for that component shows the same value.
- [ ] Switch back to General BOM and confirm the flat, sortable leaf table still works.
- [ ] "Save as" from the Structured BOM format and confirm the copy is still hierarchical.
