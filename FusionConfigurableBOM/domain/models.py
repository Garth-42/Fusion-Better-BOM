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

def configuration_to_dict(config):
    return {'schema_version': config.schema_version, 'fields': [asdict(f) for f in config.fields],
            'views': [{'view_id': v.view_id, 'name': v.name, 'columns': [asdict(c) for c in v.columns]} for v in config.views]}
