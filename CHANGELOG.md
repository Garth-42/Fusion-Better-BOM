# Changelog

## Unreleased

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
