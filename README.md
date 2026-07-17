# Fusion Configurable BOM Add-In

A custom Autodesk Fusion add-in that turns the active design into an editable,
configurable Bill of Materials. It opens its own dockable palette, scans the
assembly into a parts table, and lets you add your own columns (manufacturer,
supplier, part numbers, notes, …) that are saved right in the Fusion design.

The add-in uses its **own palette** and never modifies Fusion's native BOM UI.

## Features

- **Automatic parts table** — scans the active design into a BOM. Identical
  components are aggregated into a single row with a quantity count, and two
  parts that merely share a display name stay on separate rows.
- **Flat or structured views** — show a flat leaf-part list, or a **Structured
  BOM** that walks the assembly tree with sub-assemblies as collapsible parent
  rows, indented children, a per-parent quantity, and a rolled-up total quantity
  for the whole design.
- **Accurate roll-ups** — flat formats can consolidate by component definition,
  part number, or immediate subassembly. Parts with different custom attribute
  values are kept in separate rows, so a roll-up never hides a unique value.
- **Editable custom columns** — add your own string fields (Manufacturer,
  Supplier, part numbers, or anything else) and edit them inline. Editable cells
  are marked with a ✎.
- **Values follow the component** — a value you enter for a part shows up
  everywhere that part appears, because values are keyed to the component itself.
- **Multiple saved formats** — keep several table layouts (for example a general
  BOM and a purchasing sheet) that present the same components differently. You
  can add, hide, reorder, and rename columns, and duplicate or delete formats.
- **Rename without losing data** — renaming a column header updates its display
  name everywhere it is used without changing the stored values behind it.
- **Sorting** — sort any column ascending or descending in the flat views.
- **Saved with your design** — configuration and cell values persist in the
  Fusion design via component Attributes, so they survive closing and reopening.
- **Copy to spreadsheet** — copy the current view as tab-separated rows for clean
  pasting into Google Sheets or Excel (the indented outline is preserved for
  structured views).
- **Linked parts stay safe** — components linked from another design are shown
  read-only (🔒); edit them by opening their source design.

## Requirements

- Autodesk Fusion (desktop) on macOS or Windows.
- No external dependencies — the add-in is self-contained Python plus a small
  HTML/CSS/JavaScript palette.

## Installation

1. Download or clone this repository.
2. In Fusion, open **Utilities ▸ Add-Ins ▸ Scripts and Add-Ins**.
3. Select the **Add-Ins** tab, click the green **+**, and choose the
   `FusionConfigurableBOM` directory from this repository.
4. Select **Fusion Configurable BOM** and click **Run** (optionally enable
   *Run on Startup*).

## Usage

1. Open a Fusion design with an assembly.
2. Run **Utilities ▸ Add-Ins ▸ Open Configurable BOM** to show the palette.
3. Click **Refresh** to scan the active design into the table.
4. Use the **Format** dropdown to switch between saved layouts, including the
   **Structured BOM** tree view. The dropdown *is* the flat-vs-hierarchical
   switch: each format is either flat or hierarchical, so picking a format
   chooses the structure — there is no separate toggle.
5. Click any cell marked with a ✎ to edit it. Edits save to the Fusion design
   automatically a moment after you stop typing; click **Save design** to save
   immediately.
6. Click **Edit formats** to set a format's **Structure** (flat or
   hierarchical) and its flat **Roll-up** (component, part number, or immediate
   subassembly), add fields, add/hide/reorder columns, rename headers, or
   **Save as…** a new format.
7. Click **Copy table** to copy the current view for pasting into a spreadsheet.

### Built-in formats

| Format | Structure | Columns |
| --- | --- | --- |
| **General BOM** | Flat | Qty, Component, Part Number, Description |
| **Purchasing Demo** | Flat | Qty, Component, Manufacturer, Manufacturer Part Number, Supplier, Supplier Part Number |
| **Part Number Roll-up** | Flat, by part number | Qty, Part Number, Component, Description |
| **Subassembly Roll-up** | Flat, by immediate subassembly | Qty, Subassembly, Component, Part Number |
| **Structured BOM** | Hierarchical | Qty, Total Qty, Component, Part Number, Description |

## How data is stored

Custom columns and cell values are stored as Fusion **component Attributes** on
the active design's root component and reach disk when the design is saved. The
add-in debounce-saves the document for you after edits and also offers a manual
**Save design** button. Values entered on a part that is linked from another
file are read-only in the parent design.

## Project status

This is the **Configurable BOM Concept Validator** — a focused, working add-in
that validates the core BOM workflow (scan, custom columns, saved formats, and
persistence). Please run the checks in
[`docs/manual-fusion-test-plan.md`](docs/manual-fusion-test-plan.md) after
installing, and see [`CHANGELOG.md`](CHANGELOG.md) for recent changes.

## Documentation

- [`docs/manual-fusion-test-plan.md`](docs/manual-fusion-test-plan.md) — install
  and acceptance checklist.
- [`docs/architecture.md`](docs/architecture.md) — how the add-in is structured.
- [`docs/hierarchical-bom-plan.md`](docs/hierarchical-bom-plan.md) — the
  structured BOM design.
- [`docs/roadmap.md`](docs/roadmap.md) — planned and out-of-scope features.

## License

See [`LICENSE`](LICENSE).
