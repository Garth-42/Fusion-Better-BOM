# Codex Start Here

You are implementing **Deliverable 1: Configurable BOM Concept Validator** for Autodesk Fusion.

## Read in this order

1. `docs/deliverable-1-concept-validator.md`
2. `docs/architecture.md`
3. `docs/implementation-plan.md`
4. `docs/testing-risks.md`

The remaining metadata, domain, and supplier documents describe the future roadmap. They are not part of the current implementation assignment.

## Current assignment

Implement Deliverable 1A through Deliverable 1E only.

The result should be a small Fusion Python add-in that:

- Opens its own dockable BOM palette.
- Displays a flattened leaf-component BOM.
- Counts repeated component definitions.
- Allows custom string columns backed by component Attributes.
- Allows column headers to be renamed without changing stored data.
- Supports at least two persisted table formats.
- Allows columns to be reordered and hidden.
- Keeps linked components read-only in the parent assembly.

## Non-negotiable scope limits

Do not implement:

- Supplier filtering
- CSV export
- Supplier profiles
- Procurement quantities
- Packaging or units
- Assembly overrides
- Multiple supplier offers
- Native Fusion BOM customization
- Structured BOMs
- ERP, PLM, cloud, or API integrations
- Advanced identity services
- Bulk import/export

## Implementation rules

- Use a custom HTML palette; do not depend on Fusion's native BOM UI.
- Use stable custom `field_id` values as Attribute names.
- Keep the visible header separate from the field ID.
- Store field/view configuration in a versioned root-component Attribute.
- Use string custom-field values only.
- Do not group rows by display name.
- Use plain HTML/CSS/JavaScript without a front-end framework.
- Keep pure table and configuration logic independent of `adsk`.
- Create `docs/implementation-status.md` before production work.
- Run automated tests and document manual Fusion tests.
- Stop after Deliverable 1 acceptance criteria pass.
