from ..domain.models import ConceptBomRow
from .attribute_store import read_values

def _is_leaf(occurrence):
    return occurrence.childOccurrences.count == 0

def _is_linked(component):
    # Document references are the conservative public indicator for externally linked definitions.
    return bool(getattr(component, 'isReferencedComponent', False))

def scan_design(design, field_ids):
    grouped = {}
    for occurrence in design.rootComponent.allOccurrences:
        if getattr(occurrence, 'isSuppressed', False) or not _is_leaf(occurrence):
            continue
        component = occurrence.component
        key = id(component)  # Stable for this scan; never aggregate by display name.
        entry = grouped.setdefault(key, {'component': component, 'quantity': 0})
        entry['quantity'] += 1
    rows = []
    for index, entry in enumerate(grouped.values(), 1):
        component = entry['component']
        rows.append(ConceptBomRow(f'row_{index}', component.name, entry['quantity'],
            getattr(component, 'partNumber', None), getattr(component, 'description', None),
            getattr(component, 'material', None).name if getattr(component, 'material', None) else None,
            _is_linked(component), read_values(component, field_ids)))
    return rows, {f'row_{i}': entry['component'] for i, entry in enumerate(grouped.values(), 1)}
