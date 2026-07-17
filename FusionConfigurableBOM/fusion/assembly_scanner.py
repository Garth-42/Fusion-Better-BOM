from ..domain.models import ConceptBomRow, HierarchicalBomNode
from .attribute_store import read_values as read_component_values
from .value_store import read_values as read_root_values

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

def _visible(occurrences):
    """Occurrences that count toward a BOM: present in the tree and not suppressed."""
    return [occurrence for occurrence in _items(occurrences)
            if not getattr(occurrence, 'isSuppressed', False)]

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

def _component_key(component):
    """Use Fusion's persistent entity identity; Python proxy objects may differ per occurrence."""
    token = getattr(component, 'entityToken', None)
    return ('entity_token', token) if token else ('object_id', id(component))

def _flat_occurrences(root):
    """Return visible occurrences with their immediate parent context.

    `allOccurrences` does not retain the parent relationship needed for the
    subassembly roll-up, so use the occurrence tree for every flat mode.
    """
    found = []
    def walk(occurrences, parent_component=None):
        for occurrence in _visible(occurrences):
            found.append((occurrence, parent_component))
            walk(getattr(occurrence, 'childOccurrences', None), occurrence.component)
    walk(getattr(root, 'occurrences', None))
    if not found:
        found = [(occurrence, None) for occurrence in _visible(_root_descendants(root))]
    if not found:
        found = [(occurrence, None) for occurrence in _visible(getattr(root, 'allOccurrences', None))]
    return found

def _rollup_key(component, parent_component, values, rollup_by):
    # Attribute values are deliberately included in every roll-up signature.
    # Thus two parts with the same part number but different configured metadata
    # remain separate rows and every value can be truthfully shown in its column.
    attributes = tuple(sorted(values.items()))
    component_key = _component_key(component)
    if rollup_by == 'part_number':
        part_number = (getattr(component, 'partNumber', None) or '').strip()
        identity = ('part_number', part_number) if part_number else component_key
    elif rollup_by == 'subassembly':
        identity = ('subassembly', _component_key(parent_component) if parent_component else None, component_key)
    else:
        identity = component_key
    return identity, attributes

def scan_design(design, field_ids, rollup_by='component'):
    grouped = {}
    root = design.rootComponent
    occurrence_contexts = _flat_occurrences(root)
    occurrences = [occurrence for occurrence, _parent in occurrence_contexts]
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
        bom_contexts = [(type('RootOccurrence', (), {'component': root})(), None)]
    else:
        bom_contexts = [(occurrence, parent) for occurrence, parent in occurrence_contexts if occurrence in bom_occurrences]
    for occurrence, parent_component in bom_contexts:
        component = occurrence.component
        # Fusion can hand back a new Python proxy for the same component definition
        # on each occurrence. entityToken keeps those occurrences in one BOM row.
        values = _shared_values(root, component, field_ids)
        key = _rollup_key(component, parent_component, values, rollup_by)
        entry = grouped.setdefault(key, {'component': component, 'parent_component': parent_component,
                                         'values': values, 'quantity': 0})
        entry['quantity'] += 1
    rows = []
    for index, entry in enumerate(grouped.values(), 1):
        component = entry['component']
        # Root-stored values are authoritative (they persist with the active
        # design); fall back to any legacy value written on the component itself.
        values = entry['values']
        rows.append(ConceptBomRow(f'row_{index}', component.name, entry['quantity'],
            getattr(component, 'partNumber', None), getattr(component, 'description', None),
            getattr(component, 'material', None).name if getattr(component, 'material', None) else None,
            _is_linked(component), values,
            getattr(entry['parent_component'], 'name', None)))
    return rows, {f'row_{i}': entry['component'] for i, entry in enumerate(grouped.values(), 1)}

def _shared_values(root, component, field_ids):
    # Values are keyed by component definition, so every node for the same
    # definition reads the same values. Root-stored values win over any legacy
    # value written on the component itself, matching the flat scan.
    values = read_component_values(component, field_ids)
    values.update(read_root_values(root, component, field_ids))
    return values

def scan_design_hierarchical(design, field_ids):
    """Walk the assembly tree into structured BOM nodes.

    Returns (nodes, components) with the same contract as scan_design: nodes are
    ordered parent-before-child (depth first, preserving browser order) and the
    components map lets the controller write edits back by row. Identical sibling
    occurrences under one parent collapse into a single node whose `quantity` is
    the count; `total_quantity` rolls that up through the parent chain so a leaf
    reports how many exist in the whole design along that path.
    """
    root = design.rootComponent
    nodes, components, counter = [], {}, [0]
    def walk(occurrences, parent_id, level, parent_rollup):
        # Aggregate by component definition among these siblings only. Fusion can
        # hand back a new proxy per occurrence, so entityToken (via _component_key)
        # keeps repeated instances of one definition on a single node.
        grouped = {}
        for occurrence in occurrences:
            component = occurrence.component
            entry = grouped.setdefault(_component_key(component),
                {'occurrence': occurrence, 'component': component, 'quantity': 0})
            entry['quantity'] += 1
        for entry in grouped.values():
            component, quantity = entry['component'], entry['quantity']
            rollup = quantity * parent_rollup
            counter[0] += 1
            row_id = f'row_{counter[0]}'
            children = _visible(getattr(entry['occurrence'], 'childOccurrences', None))
            nodes.append(HierarchicalBomNode(row_id, component.name, level, parent_id,
                quantity, rollup, bool(children),
                getattr(component, 'partNumber', None), getattr(component, 'description', None),
                getattr(component, 'material', None).name if getattr(component, 'material', None) else None,
                _is_linked(component), _shared_values(root, component, field_ids)))
            components[row_id] = component
            if children:
                walk(children, row_id, level + 1, rollup)
    walk(_visible(getattr(root, 'occurrences', None)), None, 0, 1)
    return nodes, components
