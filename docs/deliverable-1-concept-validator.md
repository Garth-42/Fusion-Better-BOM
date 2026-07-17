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

