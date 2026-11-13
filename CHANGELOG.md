# Changelog

## Unreleased

Code-review fixes:

- Fixed stored custom values showing as blank after switching between formats with the same structure (for example General BOM → Purchasing Demo). The palette swapped columns locally, but each row only carried values for the previous format's columns; typing into the blank cell then overwrote the real value. Format switches now always redraw from the controller's cached snapshot.
- Fixed typed cell values reverting on screen (and in **Copy table**) after sorting, collapsing a tree row, or any other redraw.
- Fixed values on a single-part design (a root component with bodies and no occurrences) disappearing on Refresh. Such a design now also shows its one line in the Structured BOM.
- Fixed edits being written into the wrong design after switching Fusion document tabs. The controller refuses edits when the active design is not the one that was scanned, and the palette re-scans when a document is activated.
- Fixed the format editor breaking after a rejected attribute-key rename, and **Cancel** not discarding column reordering. The editor now works on a private copy of the configuration; **Save changes** closes the editor on success and shows the error inside it on failure.
- Fixed editing a part-number roll-up row only updating the first of the merged components, which split the row on the next Refresh.
- Replaced empty or cryptic error messages (unknown format, stale row, no design in the Manufacture workspace, unknown action).
- **Behaviour change:** auto-save is now opt-in via an **Auto-save** checkbox (remembered per machine). Previously every pause in typing saved the whole document, creating a new design version each time. **Save design** shows a • while BOM changes are unsaved.
- Cell values are now keyed by the component's persistent `Component.id` rather than its `entityToken`, which Autodesk says must not be compared. Values stored under a token are still read and are migrated the next time that component is edited.
- Cell edits are sent after a 300 ms pause instead of on every keystroke, rewrite the stored value map once, and patch the scan snapshot instead of discarding it.
- The `allOccurrences` fallback no longer double-counts nested parts.
- Configuration validation now rejects columns that reference a missing custom field or unknown source type (a stored configuration with such a column still loads, minus the column). New custom-field names that start with a digit get a valid key; duplicate keys are reported clearly. Deleting a format asks for confirmation.
- macOS clipboard copy sends UTF-8 explicitly so non-ASCII text is not mangled.
- Renamed the add-in namespace from the template placeholder `com.company.fusion_configurable_bom` to `fusion_configurable_bom` (manifest `id` and all three attribute groups). Existing designs keep their formats and values: the old groups are read as a fallback and data moves to the new groups the next time it is written.
- Removed dead code (duplicate scanner helpers, unreachable fallbacks, the unused `duplicate_view` action), formatted the Python with `ruff`, and added a GitHub Actions workflow that runs lint and the unit tests.

- Fixed switching between BOM table formats re-walking the whole assembly every time, which made Fusion "think for a while" on each switch. The add-in already parsed the design once into an in-memory snapshot and rebuilt each format from it, but the cache was keyed on `id(rootComponent)`. Fusion hands back a fresh Python proxy on every `rootComponent` access, so that id changed on every call and the snapshot was discarded and re-parsed each switch. The cache now keys on the root component's persistent `entityToken` (falling back to object identity only when no token exists), so the assembly is walked once per Refresh and format switches redraw from the cached snapshot.
- Surfaced the flat-vs-hierarchical choice in the format editor: **Edit formats** now has a **Structure** selector (Flat or Hierarchical) for the format being edited, so any format can be switched between a flat leaf list and a structured tree. Switching the on-screen format's structure re-scans the assembly so the table redraws in the new shape. The **Format** dropdown remains the way to switch structure while viewing; there is still no separate global toggle.
- Fixed the **Structured BOM** format not appearing for designs configured before it shipped. The schema migration only bumped the version and never added the new default format, so existing designs never gained the hierarchical option. Missing built-in formats are now restored whenever a configuration loads, without touching the user's own formats or customizations.
- Added a hierarchical (structured) BOM as a per-view option. A new **Structured BOM** format walks the assembly tree, showing sub-assemblies as collapsible parent rows with their children indented beneath. Each line reports a per-parent quantity and a rolled-up total for the whole design. Flat leaf views are unchanged and remain the default. Custom values stay shared by component definition, so a part shows the same values everywhere it appears. Copying a structured view preserves the indented outline. See `docs/hierarchical-bom-plan.md`.
- Bumped the configuration schema to v2 (per-view structure). Existing v1 designs migrate automatically with every view defaulting to a flat BOM; no stored fields, columns, or values are lost.
- Fixed BOM cell values disappearing after closing and reopening a design: values are now stored in one map on the active design's root component (keyed by each part's persistent id) instead of on the individual components. Component-level values were not saved when a part was referenced from another file, so the active design's save never captured them. Existing values written on components are still read as a fallback.
- Persisted BOM attribute and format edits automatically by debounce-saving the Fusion document a moment after editing stops, so values survive closing and reopening Fusion without a manual save.
- Kept the Save design button for an immediate save and made saves best-effort on documents that have not been saved to a project yet.
- Added a Copy Table button that copies the active view as tab-separated rows for clean pasting into Sheets/Excel.
- Scoped palette text selection to the table so manual copy no longer grabs the toolbar and status chrome.

## 0.3.0 - 2026-07-16

- Reined the first implementation scope into a Configurable BOM Concept Validator.
- Added a dedicated Deliverable 1 specification and scope gate.
- Limited custom fields to Attribute-backed strings.
- Limited table formats to column header, order, visibility, and width.
- Deferred supplier, CSV, procurement quantity, override, and advanced identity features.
- Changed Codex instructions to stop after the concept validator passes acceptance tests.

## 0.2.0 - 2026-07-16

- Added procurement architecture, supplier profiles, risk analysis, and roadmap.
