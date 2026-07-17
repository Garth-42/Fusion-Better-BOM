# Domain Model

## Active Deliverable 1 model

The first deliverable intentionally uses a minimal model.

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

## Row identity and aggregation

For one active scan:

- Traverse assembly occurrences.
- Resolve each leaf occurrence to its Fusion component definition.
- Aggregate repeated occurrences of that same resolved component definition.
- Never aggregate solely because display names match.

The row ID may be an in-memory scan identifier. Deliverable 1 does not need an enterprise persistent identity model because values are written directly to the component represented by the row.

## Attribute-backed values

`custom_values` maps stable field IDs to strings.

```python
{
    "manufacturer": "Phoenix Contact",
    "manufacturer_part_number": "3248100"
}
```

The visible header is defined by the selected table format and is not part of the component data.

## Linked components

Rows include a `linked` flag. The UI shows linked rows but prevents Attribute edits in the parent design.

## Hierarchical BOM nodes

The structured BOM option produces `HierarchicalBomNode` rows. The flat model above is unchanged and still backs flat views.

```python
@dataclass
class HierarchicalBomNode:
    row_id: str
    component_name: str
    level: int              # 0-based depth
    parent_id: str | None
    quantity: int           # count directly under the immediate parent
    total_quantity: int     # rolled-up occurrences in the whole design via this path
    is_assembly: bool
    fusion_part_number: str | None
    fusion_description: str | None
    material: str | None
    linked: bool
    custom_values: dict[str, str]
```

One component definition can produce several nodes — one for each place it sits in the tree — but `custom_values` stays keyed by the component definition, so every node for a definition shows the same values. `total_quantity` equals `quantity` multiplied up the parent chain. See `docs/hierarchical-bom-plan.md`.

## Explicitly deferred roadmap types

Do not add these to Deliverable 1 production code:

- ComponentIdentity
- MetadataOverride
- EffectiveMetadata
- SupplierOffer
- PackagingDefinition
- Quantity and unit models
- OrderCalculation
- ValidationMessage framework
- ExportSnapshot
- FilterDefinition
- GroupingDefinition
- Procurement BOM behaviors

These types remain appropriate for the future procurement roadmap after concept validation.
