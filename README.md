# Fusion Configurable BOM Add-In

This repository defines a staged Autodesk Fusion add-in project.

## Active deliverable

The only current implementation scope is a small **Configurable BOM Concept Validator** that:

- Opens a custom dockable BOM palette.
- Scans the current assembly into a flattened leaf-component table.
- Counts repeated component definitions.
- Adds editable custom string columns backed by Fusion component Attributes.
- Lets column headers be renamed without changing stored data.
- Supports multiple persisted table formats with different column names, order, and visibility.

The add-in uses its own palette. It does **not** add columns to or modify Fusion's native BOM UI.

## Start here

1. Read `CODEX_START_HERE.md`.
2. Read `docs/deliverable-1-concept-validator.md`.
3. Implement Deliverable 1A through 1E from `docs/implementation-plan.md`.
4. Stop when Deliverable 1 acceptance criteria pass.

## Explicitly deferred

Supplier filtering, CSV exports, AutomationDirect, DigiKey, Mouser, McMaster-Carr, StepperOnline, order quantities, packaging, assembly overrides, advanced identity, validation, and audit snapshots remain on the future roadmap.

## Repository status

Architecture and scope baseline only. No production add-in code has been generated yet.

## Installation and validation

The `FusionConfigurableBOM` directory is a Fusion Python add-in. Install it from Fusion's **Scripts and Add-Ins** dialog by adding that directory, then run the add-in and choose **Open Configurable BOM** from the Add-Ins panel. See `docs/manual-fusion-test-plan.md` for the required manual acceptance checks.

### Known concept-validator limitations

- The BOM is a flattened, leaf-only custom palette; Fusion's native BOM UI is not changed.
- Configuration and values persist only through Fusion component Attributes after the design is saved.
- Linked components are deliberately read-only in their parent assembly.
- Supplier workflows, CSV, purchasing quantities, overrides, and all roadmap features remain excluded.
