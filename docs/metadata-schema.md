# Metadata and Persistence Schema

## Active Deliverable 1 schema

Deliverable 1 uses two simple Attribute mechanisms.

## 1. Custom component values

Attribute group:

```text
com.company.fusion_configurable_bom.fields
```

Each custom field has a stable internal `field_id`. The field ID is used as the Attribute name.

```text
Attribute name: <field_id>
Attribute value: <string>
```

Example:

```text
Attribute group: com.company.fusion_configurable_bom.fields
Attribute name: manufacturer_part_number
Attribute value: 3248100
```

The visible table header is not the persistence key. A view can display this same field as `Manufacturer Part Number`, `Mfr. P/N`, or another user-selected header without moving data.

Deliverable 1 supports string values only.

## 2. Design configuration

Store field definitions and table formats on the root component.

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
      "view_id": "purchasing_demo",
      "name": "Purchasing Demo",
      "columns": [
        {
          "source_type": "builtin",
          "source_id": "quantity",
          "header": "Qty",
          "visible": true,
          "width": 70
        },
        {
          "source_type": "attribute",
          "source_id": "manufacturer_part_number",
          "header": "Mfr. P/N",
          "visible": true,
          "width": 180
        }
      ]
    }
  ]
}
```

## 3. Deliverable 1 migration behavior

- Missing configuration: create defaults in memory and persist on first explicit save.
- Schema version 1: load normally.
- Unknown future version: open the BOM read-only and show a clear error.
- Corrupt JSON: preserve the raw Attribute, do not overwrite it automatically, and offer a reset-to-default action only after confirmation.

## 4. Deferred roadmap schema

The following are deliberately not part of Deliverable 1:

- Rich component metadata JSON
- Component UUIDs
- Internal part numbers as enterprise identity
- Assembly overrides
- Supplier offers
- Packaging definitions
- Quantity rules
- User or team view storage
- Custom Properties mirroring
- Metadata import/export
- Schema migration across the full procurement model

The previous procurement schema remains a roadmap concept and should be introduced only after the concept validator is accepted.
