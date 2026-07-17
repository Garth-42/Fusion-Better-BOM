# Roadmap

The shipping add-in is the **Configurable BOM Concept Validator** described in the
[README](../README.md). Everything below is future scope: it is intentionally
**not** implemented today and is recorded here so the README can stay focused on
what the tool actually does.

## Deferred features

These capabilities are planned but out of scope for the current concept validator:

- **Supplier profiles and export targets** — AutomationDirect, DigiKey, Mouser,
  McMaster-Carr, StepperOnline, and similar vendors.
- **Supplier filtering** across a design's parts.
- **CSV and spreadsheet exports** / ordering worksheets (direct upload, mapped
  BOM upload, RFQ worksheets).
- **Procurement quantities** — order quantities, packaging, and units.
- **Assembly overrides** — per-assembly values that differ from the component
  default, and multiple supplier offers per part.
- **Advanced identity, validation, and audit snapshots.**
- **Native Fusion BOM customization** (the add-in deliberately uses its own
  palette instead of modifying Fusion's built-in BOM).
- **ERP, PLM, cloud, or API integrations**, and bulk import/export.

## Reference designs

The broader procurement vision is captured in these documents. They describe the
target architecture, not current behavior:

- `Fusion_Configurable_BOM_Architecture_v0.3.md` — full architecture and
  implementation specification.
- `docs/supplier-profiles.md` — supplier export profiles and ordering exports.
- `docs/metadata-schema.md` — persistence schema, including future fields.
- `docs/domain-model.md` — domain model beyond the concept validator.

## Recently delivered

Items that were previously on the roadmap and have since shipped:

- **Structured (hierarchical) BOM** — sub-assemblies as collapsible parent rows
  with indented children, per-parent quantity, and a rolled-up total. Available
  as the **Structured BOM** format. See `docs/hierarchical-bom-plan.md`.
