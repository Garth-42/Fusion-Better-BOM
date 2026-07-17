from ..domain.models import ConceptBomRow
from .attribute_store import read_values

def _is_leaf(occurrence):
    return occurrence.childOccurrences.count == 0

def _has_bodies(component):
    bodies = getattr(component, 'bRepBodies', None)
    return bool(bodies and bodies.count > 0)

def _items(collection):
    """Read Fusion API collections by index, with iterable support for tests."""
    if hasattr(collection, 'count') and hasattr(collection, 'item'):
        return [collection.item(index) for index in range(collection.count)]
    if getattr(collection, 'count', None) == 0:
        return []
    return list(collection or [])

def _root_descendants(root):
    """Fallback traversal for designs where allOccurrences is unexpectedly empty."""
    descendants, pending = [], _items(getattr(root, 'occurrences', None))
    while pending:
        occurrence = pending.pop()
        descendants.append(occurrence)
        pending.extend(_items(getattr(occurrence, 'childOccurrences', None)))
    return descendants

def _is_linked(component):
    # Document references are the conservative public indicator for externally linked definitions.
    return bool(getattr(component, 'isReferencedComponent', False))

def scan_design(design, field_ids):
    grouped = {}
    root = design.rootComponent
    occurrences = [occurrence for occurrence in _items(root.allOccurrences)
                   if not getattr(occurrence, 'isSuppressed', False)]
    if not occurrences:
        occurrences = [occurrence for occurrence in _root_descendants(root)
                       if not getattr(occurrence, 'isSuppressed', False)]
    # A strict leaf scan is the normal BOM behavior. Some Fusion designs use
    # components that contain both bodies and child occurrences, which means
    # there are no strict leaves even though the browser visibly contains parts.
    # In that case prefer physical components, then provide a final useful
    # fallback rather than returning an unexplained empty BOM.
    bom_occurrences = [occurrence for occurrence in occurrences if _is_leaf(occurrence)]
    if not bom_occurrences:
        bom_occurrences = [occurrence for occurrence in occurrences if _has_bodies(occurrence.component)]
    if not bom_occurrences:
        bom_occurrences = occurrences
    if not bom_occurrences and _has_bodies(root):
        # A single-part design can put bodies directly under the root component.
        bom_occurrences = [type('RootOccurrence', (), {'component': root})()]
    for occurrence in bom_occurrences:
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
