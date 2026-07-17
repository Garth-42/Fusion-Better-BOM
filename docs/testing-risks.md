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
