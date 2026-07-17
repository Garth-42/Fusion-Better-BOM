# Implementation Plan and Acceptance Criteria

## Active scope: Deliverable 1 only

The current implementation assignment is the Configurable BOM Concept Validator described in `deliverable-1-concept-validator.md`.

The broader procurement roadmap is retained below only for sequencing. Do not begin it without explicit instruction.

## Deliverable 1A: Add-in shell and API spike

Deliver:

- Fusion manifest and add-in entry point.
- One toolbar command.
- Dockable palette shell.
- Clean startup and shutdown.
- No-active-document handling.
- Small API spike confirming component Attribute persistence.
- Small API spike confirming assembly traversal and repeated occurrence counting.

Exit criteria:

- The palette opens and closes.
- Attribute data persists after save and reopen.
- The scanner produces expected counts for a small test assembly.
- Linked components are detected or conservatively treated as read-only.

## Deliverable 1B: Minimal BOM table

Deliver:

- Flattened leaf-component scanner.
- Quantity and Component Name columns.
- Optional straightforward built-in columns.
- Plain JSON table payload sent to the palette.
- Refresh button.
- Basic error and status display.

Exit criteria:

- A nested test assembly renders correctly.
- Repeated component definitions aggregate to one row.
- No grouping is performed by display name.

## Deliverable 1C: Attribute-backed custom columns

Deliver:

- Custom-field definitions with stable IDs.
- Per-component string Attributes.
- Editable custom cells for local components.
- Read-only custom cells for linked components.
- Visible save state.
- Persistence tests and manual save/reopen test.

Exit criteria:

- A user can add a field, enter values, save the design, reopen it, and see the values.
- Repeated occurrences share one value.
- Editing a linked component from the parent is prevented.

## Deliverable 1D: Multiple table formats

Deliver:

- Design-level versioned configuration Attribute.
- At least two default formats.
- Format selector.
- Duplicate, rename, and delete user format.
- Rename column header.
- Reorder columns.
- Hide/show columns.
- Add an existing or newly created custom field to a format.

Exit criteria:

- The same custom field appears under different headers in two formats.
- Format changes persist after save and reopen.
- Renaming a header does not alter component data.

## Deliverable 1E: Validation and handoff

Deliver:

- Pure-Python tests.
- Manual Fusion test checklist.
- Installation instructions.
- README with explicit scope and native-BOM limitation.
- Known limitations list.
- Clean repository suitable for review.

Exit criteria:

- All acceptance criteria in `deliverable-1-concept-validator.md` pass.
- Codex stops and reports results.

# Future roadmap - not currently authorized

## Roadmap Phase 2: Metadata and identity

- Rich component metadata schema
- Assembly overrides
- Effective-value provenance
- Strong identity and conflict validation
- Multiple supplier offers

## Roadmap Phase 3: Procurement BOM engine

- Purchased, phantom, reference, and exclude behaviors
- Unit-aware quantities
- Packaging, minimum orders, multiples, and spares
- Advanced validation

## Roadmap Phase 4: Full BOM manager

- Filters, sorting, grouping, computed columns
- User, design, and team view scopes
- Bulk editing
- Validation panel

## Roadmap Phase 5: Supplier exports

- AutomationDirect
- DigiKey
- Mouser
- McMaster-Carr worksheet
- StepperOnline worksheet
- CSV preview and versioned profiles

## Roadmap Phase 6: Hardening and release

- Large assemblies
- Metadata import/export
- Cross-platform validation
- Export snapshots
- Recovery and migration workflows

## Codex implementation instructions

1. Read `CODEX_START_HERE.md` and `docs/deliverable-1-concept-validator.md` before editing.
2. Implement Deliverable 1A through 1E only.
3. Maintain an implementation checklist in `docs/implementation-status.md`.
4. Confirm uncertain Fusion API behavior with isolated spikes.
5. Keep table/configuration logic testable without Fusion.
6. Do not add supplier, CSV, procurement quantity, override, or roadmap code.
7. Prefer the smallest dependency-free implementation.
8. Do not invent undocumented Fusion API calls.
9. Run all available automated tests.
10. Document manual Fusion tests.
11. Stop when Deliverable 1 acceptance criteria pass.
