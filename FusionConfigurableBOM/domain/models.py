from dataclasses import dataclass, field, asdict
from typing import Optional

@dataclass(frozen=True)
class CustomFieldDefinition:
    field_id: str
    default_label: str

@dataclass(frozen=True)
class ColumnDefinition:
    source_type: str
    source_id: str
    header: str
    visible: bool = True
    width: Optional[int] = None

@dataclass
class BomTableFormat:
    view_id: str
    name: str
    columns: list[ColumnDefinition]
    structure: str = 'flat'  # 'flat' (leaf-only) or 'hierarchical' (structured tree)
    # How flat rows are consolidated. Hierarchical rows are always scoped to
    # their immediate parent, so this setting only changes flat views.
    rollup_by: str = 'component'  # 'component', 'part_number', or 'subassembly'

@dataclass
class BomConfiguration:
    schema_version: int
    fields: list[CustomFieldDefinition] = field(default_factory=list)
    views: list[BomTableFormat] = field(default_factory=list)

@dataclass
class ConceptBomRow:
    row_id: str
    component_name: str
    quantity: int
    fusion_part_number: Optional[str] = None
    fusion_description: Optional[str] = None
    material: Optional[str] = None
    linked: bool = False
    custom_values: dict[str, str] = field(default_factory=dict)
    parent_assembly: Optional[str] = None

@dataclass
class HierarchicalBomNode:
    # One row in a structured (hierarchical) BOM. Unlike ConceptBomRow, the same
    # component definition can produce several nodes because it can sit in more
    # than one place in the assembly tree. `quantity` is the structured count
    # directly under this node's immediate parent; `total_quantity` is the
    # rolled-up number of this item in the whole design reached through this
    # path (structured quantity multiplied up the parent chain). Custom values
    # stay keyed by component definition, so every node for the same definition
    # shows the same values.
    row_id: str
    component_name: str
    level: int
    parent_id: Optional[str]
    quantity: int
    total_quantity: int
    is_assembly: bool
    fusion_part_number: Optional[str] = None
    fusion_description: Optional[str] = None
    material: Optional[str] = None
    linked: bool = False
    custom_values: dict[str, str] = field(default_factory=dict)

def configuration_to_dict(config):
    return {'schema_version': config.schema_version, 'fields': [asdict(f) for f in config.fields],
            'views': [{'view_id': v.view_id, 'name': v.name, 'structure': v.structure, 'rollup_by': v.rollup_by, 'columns': [asdict(c) for c in v.columns]} for v in config.views]}
