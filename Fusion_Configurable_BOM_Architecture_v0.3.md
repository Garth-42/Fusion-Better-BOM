# Fusion Configurable BOM Add-In

## Architecture and Implementation Specification v0.3

**Active scope:** Deliverable 1 - Configurable BOM Concept Validator  
**Future scope:** Procurement BOM roadmap retained but not authorized for implementation  
**Date:** July 16, 2026

---

# Deliverable 1: Configurable BOM Concept Validator

## 1. Objective

Build the smallest useful Autodesk Fusion add-in that validates these core assumptions:

1. A Fusion assembly can be scanned into a useful parts-only BOM.
2. Custom part-level values can be persisted using Fusion component Attributes.
3. Custom columns can be added to a BOM table, renamed, reordered, hidden, and edited.
4. More than one saved BOM table format can display the same underlying component data differently.

This deliverable is a concept-validation add-in. It is not yet a procurement, supplier, CSV-export, ERP, or full production BOM system.

## 2. Scope rule

Codex must implement only the functionality in this document unless explicitly instructed otherwise.

The broader procurement architecture remains the roadmap, but none of its supplier, quantity, override, validation, or export features belong in Deliverable 1.

## 3. User experience

The add-in adds one toolbar command:

```text
Open Configurable BOM
```

The command opens a dockable HTML palette containing:

- A table-format selector.
- A Refresh button.
- An Edit Table Formats button.
- A parts-only BOM table.
- Read-only built-in Fusion columns.
- Editable custom attribute columns.
- A small status area for save state and errors.

The add-in does not attempt to add columns to Fusion's native BOM window. The custom palette is the BOM UI for this deliverable.

## 4. Assembly scanning

The first deliverable uses intentionally simple scanning rules:

1. Scan the active Fusion design.
2. Traverse all assembly occurrences.
3. Count repeated occurrences of the same component definition.
4. Display leaf components only.
5. Exclude the root component.
6. Ignore suppressed occurrences when the API exposes that state reliably.
7. Show externally linked components, but treat their custom cells as read-only in the parent design.
8. Do not implement purchased assemblies, phantom assemblies, reference behavior, occurrence overrides, configurations, or multilevel BOM structure.

Rows are grouped by the resolved Fusion component object within the active design scan. The deliverable must not group by component display name.

This simple identity rule is sufficient for concept validation because metadata is stored directly on the component definition represented by each row. The full roadmap identity service is deferred.

## 5. Built-in columns

The first release should include these read-only columns:

- Quantity
- Component Name
- Fusion Part Number, when available
- Fusion Description, when available
- Material, when available
- Linked Status

Only Quantity and Component Name are required for the first functional build. The other built-in columns should be included when they are straightforward and documented in the Fusion API.

## 6. Custom fields and Attributes

### 6.1 Storage decision

Fusion component Attributes are the correct storage backend for this concept validator.

Each custom field has a stable internal `field_id`. The visible column header is separate and can be renamed without changing the stored field or losing values.

Recommended Attribute group:

```text
com.company.fusion_configurable_bom.fields
```

For each component and custom field:

```text
Attribute group: com.company.fusion_configurable_bom.fields
Attribute name: <field_id>
Attribute value: <string value>
```

Example:

```text
field_id: supplier_part_number
visible header in one view: Supplier SKU
visible header in another view: Order Number
```

Both columns read the same component Attribute even though their headers differ.

### 6.2 Supported field type

Deliverable 1 supports string values only.

Do not implement numeric, date, Boolean, dropdown, URL, formula, unit, or validation types yet. Blank values are represented by an absent Attribute or an empty string.

### 6.3 Editing behavior

- Built-in Fusion columns are read-only.
- Custom cells are editable for local components.
- Saving a custom cell writes or updates the corresponding component Attribute.
- Clearing a cell removes the Attribute when practical; otherwise it stores an empty string consistently.
- Repeated occurrences share one value because the value belongs to the component definition.
- Edits should use an explicit Apply/Save operation or a clear debounced save with visible status. Silent data loss is unacceptable.
- The add-in must mark the Fusion design as modified through normal Attribute writes so the user can save the design.

## 7. Table formats

Deliverable 1 supports multiple saved table formats with deliberately limited behavior.

Each table format contains:

- Stable `view_id`
- Display name
- Ordered list of columns
- Per-column visible header
- Per-column visibility
- Optional stored width

A table format does not contain:

- Filters
- Supplier selection
- Grouping rules
- Computed columns
- Sorting rules beyond optional simple click-to-sort UI state
- Quantity multipliers
- Export settings

### 7.1 Required format operations

The user can:

- Switch between at least two formats.
- Create a format by duplicating an existing format.
- Rename a format.
- Reorder columns.
- Hide or show columns.
- Rename a column header within a format.
- Add an existing custom field to a format.
- Create a new custom field and add it to a format.
- Delete a user-created format.

The first installation should include two simple examples:

### General BOM

- Quantity
- Component Name
- Fusion Part Number
- Description

### Purchasing Demo

- Quantity
- Component Name
- Manufacturer
- Manufacturer Part Number
- Supplier
- Supplier Part Number

The Purchasing Demo is only a column-layout example. It does not filter by supplier and does not export orders.

## 8. Configuration persistence

Store field definitions and design-specific table formats as one versioned JSON document on the root component.

Recommended Attribute:

```text
Attribute group: com.company.fusion_configurable_bom
Attribute name: configuration
```

Example:

```json
{
  "schema_version": 1,
  "fields": [
    {
      "field_id": "manufacturer",
      "default_label": "Manufacturer"
    },
    {
      "field_id": "manufacturer_part_number",
      "default_label": "Manufacturer Part Number"
    }
  ],
  "views": [
    {
      "view_id": "general",
      "name": "General BOM",
      "columns": [
        {
          "source_type": "builtin",
          "source_id": "quantity",
          "header": "Qty",
          "visible": true,
          "width": 70
        },
        {
          "source_type": "builtin",
          "source_id": "component_name",
          "header": "Component",
          "visible": true,
          "width": 220
        }
      ]
    }
  ]
}
```

Design-level persistence is preferred for Deliverable 1 because the formats travel with the assembly and do not require a separate settings system.

Global templates, team-shared formats, import/export, and local user overrides are deferred.

## 9. Minimal internal model

```python
@dataclass(frozen=True)
class CustomFieldDefinition:
    field_id: str
    default_label: str

@dataclass(frozen=True)
class ColumnDefinition:
    source_type: str  # builtin or attribute
    source_id: str
    header: str
    visible: bool = True
    width: int | None = None

@dataclass
class BomTableFormat:
    view_id: str
    name: str
    columns: list[ColumnDefinition]

@dataclass
class ConceptBomRow:
    row_id: str
    component_name: str
    quantity: int
    fusion_part_number: str | None
    fusion_description: str | None
    material: str | None
    linked: bool
    custom_values: dict[str, str]
```

Do not introduce supplier offers, packaging, assembly overrides, order calculations, export snapshots, or enterprise identity types into Deliverable 1 production code.

## 10. UI implementation

Use a small HTML/CSS/JavaScript palette with no front-end framework.

The palette should receive plain JSON from Python and return small commands such as:

```json
{
  "action": "save_cell",
  "row_id": "...",
  "field_id": "manufacturer",
  "value": "Phoenix Contact"
}
```

Required UI capabilities:

- Render the current format.
- Edit custom cells.
- Switch formats.
- Open a compact format editor.
- Show save success or error.
- Refresh from Fusion.

Avoid advanced grid libraries, drag-and-drop dependencies, React, Vue, build tooling, or bundled package managers. Simple buttons for moving a column left/right are acceptable and preferable to complex drag-and-drop for this deliverable.

## 11. Linked components

Externally linked components are displayed but their custom cells are read-only in the parent assembly for Deliverable 1.

Display a clear indicator such as:

```text
Linked - open source design to edit
```

Do not implement parent-assembly overrides yet. This preserves the roadmap's safety rule without introducing the override system into the proof of concept.

## 12. Explicit non-goals

Do not implement any of the following in Deliverable 1:

- Supplier filtering
- CSV export
- AutomationDirect, DigiKey, Mouser, McMaster-Carr, or StepperOnline formats
- Supplier profiles
- Multiple supplier offers
- Pricing or stock
- Order quantities or packaging
- Unit conversion
- Build quantities or spare factors
- Assembly metadata overrides
- Occurrence-specific metadata
- Custom Properties mirroring
- Native Fusion BOM modification
- Multilevel or structured BOMs
- Purchased, phantom, reference, or exclude behaviors
- Bulk metadata import/export
- Team-shared views
- Cloud services
- Authentication
- ERP, PLM, or API integration
- Automatic part matching
- Advanced validation framework
- Export snapshots

## 13. Repository structure for Deliverable 1

```text
fusion-configurable-bom/
├── FusionConfigurableBOM/
│   ├── FusionConfigurableBOM.py
│   ├── FusionConfigurableBOM.manifest
│   ├── app.py
│   ├── constants.py
│   ├── commands/
│   │   └── open_bom.py
│   ├── fusion/
│   │   ├── assembly_scanner.py
│   │   ├── attribute_store.py
│   │   └── event_handlers.py
│   ├── domain/
│   │   ├── models.py
│   │   └── table_builder.py
│   ├── persistence/
│   │   └── configuration_store.py
│   ├── ui/
│   │   ├── palette_controller.py
│   │   └── web/
│   │       ├── index.html
│   │       ├── app.js
│   │       └── styles.css
│   └── resources/
├── tests/
│   ├── test_configuration.py
│   ├── test_table_builder.py
│   └── fixtures/
├── docs/
├── README.md
├── CHANGELOG.md
└── LICENSE
```

The directory may keep the existing project name if preferred, but the code should remain this small.

## 14. Tests

### Pure-Python tests

- Default configuration creation.
- Configuration JSON round-trip.
- Unknown schema version handling.
- Two views displaying the same field with different headers.
- Column reordering.
- Column visibility.
- Field deletion behavior.
- Table-row construction from mocked components.
- Repeated component count aggregation.

### Manual Fusion tests

Create an assembly containing:

- One unique local component.
- Three occurrences of another local component.
- One nested leaf component.
- One externally linked component.

Verify:

1. Quantities are 1, 3, 1, and the expected linked quantity.
2. A custom value is shared by repeated occurrences.
3. The value persists after save, close, and reopen.
4. Renaming a column header does not change or lose stored values.
5. Two formats show the same field under different headers.
6. Hidden and reordered columns persist.
7. The linked component is visible and read-only.
8. Starting and stopping the add-in does not create duplicate controls.

## 15. Acceptance criteria

Deliverable 1 is complete only when:

1. The add-in installs and loads in Fusion.
2. One toolbar command opens a dockable BOM palette.
3. The palette scans the active assembly into a flattened leaf-component table.
4. Repeated occurrences of a component are represented by one row with the correct count.
5. The table includes Quantity and Component Name.
6. A user can create a custom string field.
7. A user can edit that custom field directly in the BOM table for a local component.
8. The value persists after saving and reopening the Fusion design.
9. A user can rename the displayed column header without losing data.
10. A user can reorder and hide columns.
11. A user can switch between at least two persisted table formats.
12. The same custom field may have a different header in each format.
13. Externally linked components do not cause crashes and are read-only in the parent design.
14. The add-in stops cleanly and does not duplicate toolbar controls when reloaded.
15. The README clearly states that the add-in uses its own palette and does not modify Fusion's native BOM UI.
16. No supplier, CSV, procurement-quantity, override, or advanced roadmap feature is implemented.

## 16. Stop condition for Codex

After all Deliverable 1 acceptance criteria pass, Codex must stop.

Codex should report:

- Files added or changed.
- Automated tests run and results.
- Manual Fusion tests still required.
- Any API behavior that differed from the architecture.
- A short list of recommended next roadmap items.

Codex must not begin supplier export, procurement metadata, assembly overrides, or the full roadmap without a new explicit instruction.

---

# Staged Architecture and Future Roadmap

# Staged Architecture

## 1. Purpose

Create a configurable BOM add-in for Autodesk Fusion and validate the core concept before building the broader procurement workflow.

The project is intentionally split into two scopes:

1. **Deliverable 1 - Configurable BOM Concept Validator**: a small add-in with a custom BOM palette, editable Attribute-backed columns, renameable headers, and a few saved table formats.
2. **Future Roadmap - Procurement BOM Platform**: supplier records, supplier filtering, CSV exports, quantity/package logic, linked-component overrides, stronger identity handling, validation, and audit snapshots.

Deliverable 1 is the only currently authorized implementation scope.

## 2. Scope gate

Codex must read `docs/deliverable-1-concept-validator.md` first and implement only that document.

The remaining architecture files preserve the future design direction. They are not permission to implement roadmap features.

## 3. Deliverable 1 architecture

### 3.1 BOM ownership

The add-in displays its own dockable HTML BOM palette. It does not attempt to modify Fusion's native BOM window or add columns to the native BOM table.

### 3.2 Metadata storage

Custom values are stored as Fusion component Attributes. Each custom field uses a stable `field_id`, while each table format stores a renameable display header.

This separation allows:

- One underlying value to appear under different headers in different formats.
- Column renaming without data migration.
- Simple part-level persistence.
- Shared values across repeated occurrences of the same component definition.

### 3.3 View storage

Custom-field definitions and table-format definitions are stored as one versioned JSON Attribute on the root component of the design.

The first version supports only:

- View name
- Column order
- Column visibility
- Column header
- Optional width

### 3.4 Assembly model

The scanner creates a flattened leaf-component list and counts repeated component definitions. It excludes the root component. It does not implement procurement BOM behaviors, configuration logic, or enterprise identity resolution.

### 3.5 Linked components

Linked components are shown but custom cells are read-only in the parent assembly. Parent-assembly metadata overrides are a roadmap feature.

### 3.6 Technology

- Fusion Python add-in
- Fusion Attributes
- Dockable HTML/CSS/JavaScript palette
- No front-end framework
- Standard Python library where practical
- Pure-Python tests for configuration and table construction

## 4. Deliverable 1 components

- **Add-In Shell**: manifest, startup, shutdown, toolbar command.
- **Assembly Scanner**: flattened leaf components and occurrence counts.
- **Attribute Store**: read and write custom field values.
- **Configuration Store**: root-component JSON for fields and formats.
- **Table Builder**: convert scan results and selected format into plain row data.
- **Palette Controller**: Python/JavaScript messages.
- **Minimal Web UI**: table, format selector, custom-cell editing, format editor.

## 5. Deliverable 1 non-goals

The first deliverable excludes supplier information, CSV exports, pricing, stock, packaging, unit conversion, build quantities, filters, procurement calculations, assembly overrides, Custom Properties, native BOM modification, structured BOMs, and cloud integrations.

## 6. Future roadmap architecture

After Deliverable 1 is validated, the project may evolve into the procurement architecture already documented in this repository.

The future design retains these principles:

- Component source metadata with assembly-level overrides.
- Linked source documents are never silently modified.
- Identity is a dedicated service and never based on display name.
- Required quantities and supplier order units are explicit.
- Metadata and BOM sources are replaceable interfaces.
- Supplier formats are versioned configuration.
- Exports are auditable snapshots.
- Domain logic remains testable without Fusion.

Future system components may include:

- Metadata resolution and provenance
- Enterprise component identity
- BOM behaviors such as purchased, phantom, reference, and exclude
- Supplier offer management
- Quantity and packaging calculations
- Filters, sorting, grouping, and computed columns
- Supplier profile registry
- CSV export and preview
- Validation framework
- Export snapshots
- User, design, and team view scopes

These are roadmap concepts, not Deliverable 1 requirements.

## 7. Architectural decisions

### AD-001: Use a custom BOM palette

The project does not depend on modifying Fusion's native BOM UI.

### AD-002: Use component Attributes for concept validation

Attribute values are tied to component definitions, which matches the desired part-level behavior for repeated occurrences.

### AD-003: Separate field identity from visible header

A stable `field_id` is the persistence key. Headers belong to table formats and may be renamed freely.

### AD-004: Store first-deliverable formats in the design

Field and format configuration travels with the assembly through a versioned root-component Attribute.

### AD-005: Keep linked components read-only in Deliverable 1

This avoids unsafe source edits and defers assembly overrides.

### AD-006: Keep the UI dependency-free

Use plain HTML, CSS, and JavaScript. Prefer simple move-left/move-right controls over drag-and-drop libraries.

### AD-007: Stop after concept validation

Supplier, export, quantity, and advanced metadata code must not be added until Deliverable 1 is accepted.

---

# Implementation Plan

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

---

# Testing and Risk Register

# Testing and Risks

## Deliverable 1 risk register

| Risk | Impact | Deliverable 1 mitigation |
|---|---|---|
| Fusion does not expose supported native BOM column customization | High | Use the add-in's own HTML BOM palette and state this clearly. |
| Column rename accidentally disconnects stored data | High | Persist by stable field ID; store the visible header only in the table format. |
| Repeated occurrences show inconsistent metadata | High | Store values on the component definition so all occurrences share the same part-level value. |
| Two different components share the same display name | High | Aggregate by resolved component definition, never by name. |
| Editing a linked component changes a source design unexpectedly | High | Show linked components read-only in the parent assembly. |
| Configuration JSON becomes corrupt | Medium | Preserve raw data, open read-only, and require confirmation before reset. |
| Cell edits are lost or saved ambiguously | Medium | Use explicit Apply/Save or clear debounced save status and report errors. |
| Palette becomes unnecessarily complex | Medium | Use plain JavaScript and simple column move buttons; avoid frameworks and drag libraries. |
| Large assemblies freeze the UI | Medium | Keep the first target modest, aggregate before sending JSON, and document observed scan time. |
| Copy/paste or Save As duplicates Attribute values | Low for concept validation | Document observed behavior; defer enterprise identity repair to the roadmap. |

## Mandatory API spikes

Before implementing the full table, confirm:

1. A string Attribute can be written to a local component, saved, closed, and recovered.
2. A versioned JSON Attribute can be written to the root component and recovered.
3. Nested occurrences can be traversed and repeated component definitions counted.
4. Externally linked components can be detected reliably enough to disable edits, or conservatively treated as read-only.
5. The palette can exchange JSON messages with Python.
6. Add-in controls and handlers are removed cleanly on stop.

## Pure-Python tests

- Default configuration creation
- JSON round-trip
- Unknown schema handling
- Corrupt configuration handling without overwrite
- Field ID validation and uniqueness
- View ID validation and uniqueness
- Two views using one field with different headers
- Column reorder
- Hide/show
- View duplicate and rename
- Mocked BOM aggregation
- Table serialization

## Manual Fusion test assembly

Use:

- One unique local component
- Three occurrences of a second local component
- One nested local leaf component
- One linked component
- Two different components with the same display name

Verify quantities, independent rows for same-name components, value persistence, view persistence, renamed headers, hidden/reordered columns, linked read-only behavior, and clean add-in reload.

## Scope-creep risk

The largest project risk is accidentally treating roadmap functionality as part of the concept validator.

Any code related to suppliers, CSV export, order quantities, packaging, assembly overrides, advanced identity, validation frameworks, ERP, or web APIs must be rejected from Deliverable 1 unless a new explicit instruction changes scope.
