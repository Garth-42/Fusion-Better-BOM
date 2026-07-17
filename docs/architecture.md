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

A hierarchical (structured) scan is also available as a per-view option. It walks the assembly tree, keeps sub-assemblies as parent rows, and reports both a per-parent quantity and a rolled-up total for the whole design. Custom values stay shared by component definition. See `docs/hierarchical-bom-plan.md`.

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

The first deliverable excludes supplier information, CSV exports, pricing, stock, packaging, unit conversion, build quantities, filters, procurement calculations, assembly overrides, Custom Properties, native BOM modification, and cloud integrations.

Structured/hierarchical BOM, originally deferred here, is now available as a per-view option — see `docs/hierarchical-bom-plan.md`. Per-location (assembly) overrides remain deferred; values are still shared by component definition.

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
