> **Roadmap only:** Supplier profiles are not part of Deliverable 1 and must not be implemented without explicit authorization.

# Supplier Profiles and Ordering Exports

## 1. Capability levels

Every supplier export profile declares one capability:

- `direct_upload`: verified file intended for direct cart upload.
- `mapped_bom_upload`: supplier imports spreadsheets and maps fields.
- `ordering_worksheet`: structured file for manual ordering, copy/paste, or RFQ.
- `api_integration`: authenticated integration; future scope.

Every profile includes verification status, date, source, and notes:

- `verified`
- `sample_verified`
- `user_verified`
- `unverified`
- `deprecated`

## 2. Common profile schema

```json
{
  "schema_version": 1,
  "profile_id": "supplier_profile_id",
  "profile_version": "1.0.0",
  "supplier_id": "supplier_id",
  "display_name": "Display Name",
  "capability": "ordering_worksheet",
  "file_extension": ".csv",
  "encoding": "utf-8-sig",
  "delimiter": ",",
  "line_ending": "crlf",
  "include_header": true,
  "columns": [],
  "verification": {
    "status": "unverified",
    "verified_date": null,
    "source": null,
    "notes": ""
  }
}
```

## 3. AutomationDirect

Capability: `direct_upload`  
Verification: `verified`

Official workflow uses two columns: item code and quantity. The default export has no header.

```csv
P2-550,2
EA9-T7CL-R,1
7000-12241-2150300,4
```

Validation:

- Exact AutomationDirect item code required.
- Positive integral order quantity required.
- Duplicate item codes aggregate.
- Supplier part numbers remain text.
- The export summary warns the user to review the cart before checkout.

## 4. DigiKey

Capability: `mapped_bom_upload`  
Verification: `verified` for the myLists/import workflow; exact column mapping remains profile-versioned.

Default columns:

```csv
DigiKey Part Number,Manufacturer Part Number,Quantity,Customer Reference,Description
1234-5678-ND,ABC123,10,PCB-001-R1,Connector
```

Rules:

- Exact DigiKey part number is preferred because packaging variants matter.
- Manufacturer part number may be used as a fallback and triggers an ambiguity warning.
- Store packaging type such as cut tape, tape and reel, Digi-Reel, tray, tube, bulk, or unknown.
- Allow duplicate rows to remain separate when customer references must be preserved; otherwise aggregate exact supplier SKUs.

## 5. Mouser

Capability: `mapped_bom_upload`  
Verification: `verified` for the FORTE spreadsheet import workflow.

Mouser FORTE accepts spreadsheet uploads and maps or remembers columns. The profile therefore supplies predictable headers without claiming a single rigid file layout.

```csv
Mouser Part Number,Manufacturer Part Number,Quantity,Customer Part Number,Description
595-LM358DR,LM358DR,25,PCB-001-U4,Dual operational amplifier
```

Rules:

- Mouser part number or manufacturer part number required.
- Exact Mouser number preferred when packaging matters.
- Positive integral order quantity for ordinary parts.
- Warn on manufacturer-only matching and ambiguous packaging.

## 6. McMaster-Carr

Capability: `ordering_worksheet` for MVP  
Verification: `unverified` as a public website CSV upload format.

McMaster-Carr provides account-dependent eProcurement, Punchout, document transmission, and an approved-customer product information API. Those are future adapters and are not the MVP export.

Default worksheet:

```csv
McMaster Part Number,Order Units,Required Individual Units,Units Per Order Unit,Customer Reference,Description,Product URL
91251A540,4,100,25,FRAME-001-FST-01,Socket head screw,
```

Also provide a copy format:

```text
91251A540    4
47065T101    2
```

Rules:

- McMaster part number required.
- Export order units, not ambiguous individual quantity.
- Show package quantity and overbuy.
- Preserve alphanumeric part numbers exactly.
- Future API and Punchout work must be separately authorized and configured.

## 7. StepperOnline

Capability: `ordering_worksheet` for MVP  
Verification: `unverified` as a site upload format.

Default worksheet:

```csv
StepperOnline SKU,Quantity,Customer Reference,Description,Product URL,Variant Summary,Notes
DM542T,4,MOTION-001-DRV-01,Digital stepper driver,,48 VDC,
23HS45-4204S,4,MOTION-001-MTR-01,NEMA 23 stepper motor,,8 mm shaft,
```

Rules:

- Official store SKU required.
- Product URL recommended.
- Store variant options such as voltage, shaft, encoder, brake, gearbox, cable, and warehouse.
- Warn when selectable options are not captured in the SKU or variant metadata.

## 8. CSV safety

- Use Python's `csv` module.
- Preserve all part numbers as strings.
- Preserve leading zeros.
- Support configurable delimiter, encoding, BOM, quote policy, and line ending.
- Guard against spreadsheet formula injection for fields beginning with `=`, `+`, `-`, or `@` when exporting user-entered descriptions or references.
- Preview raw text before export.
- Test commas, quotes, newlines, Unicode, empty fields, and large quantities.

## 9. Export workflow

1. Scan or refresh assembly.
2. Select a saved view and build quantity.
3. Select supplier and offer-selection policy.
4. Resolve validation errors.
5. Review required quantities and supplier order units.
6. Preview exact output text.
7. Export CSV or worksheet.
8. Save optional snapshot JSON.
9. Display line count, exclusions, warnings, and file hash.
