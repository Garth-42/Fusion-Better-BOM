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

def _component_property(component, name, default=None):
    """Read an optional Fusion property without failing the whole BOM scan.

    Some imported/referenced component proxies reject an individual metadata
    fetch (for example `partNumber`) even though the occurrence itself is valid.
    A missing display value should render as blank, not prevent every row from
    being shown.
    """
    try:
        return getattr(component, name, default)
    except Exception:
        return default

def _material_name(component):
    material = _component_property(component, 'material')
    return _component_property(material, 'name') if material else None

def _component_key(component):
    """Use Fusion's persistent entity identity; Python proxy objects may differ per occurrence."""
    token = getattr(component, 'entityToken', None)
    return ('entity_token', token) if token else ('object_id', id(component))

def _flat_occurrences(root, include_parent=False):
    """Return visible occurrences with their immediate parent context.

    Most flat scans use Fusion's `allOccurrences`, which is the established and
    most reliable API traversal for a flattened BOM. Only the subassembly
    roll-up needs parent context, so only that mode walks `occurrences`.
    """
    if not include_parent:
        found = [(occurrence, None) for occurrence in _visible(getattr(root, 'allOccurrences', None))]
        if found:
            return found
        return [(occurrence, None) for occurrence in _visible(_root_descendants(root))]
    found = []
    def walk(occurrences, parent_component=None):
        for occurrence in _visible(occurrences):
            found.append((occurrence, parent_component))
            walk(getattr(occurrence, 'childOccurrences', None), occurrence.component)
    walk(getattr(root, 'occurrences', None))
    if not found:
        found = [(occurrence, None) for occurrence in _visible(_root_descendants(root))]
    return found

def _rollup_key(component, parent_component, values, rollup_by):
    # Attribute values are deliberately included in every roll-up signature.
    # Thus two parts with the same part number but different configured metadata
    # remain separate rows and every value can be truthfully shown in its column.
    attributes = tuple(sorted(values.items()))
    component_key = _component_key(component)
    if rollup_by == 'part_number':
        part_number = (_component_property(component, 'partNumber') or '').strip()
        identity = ('part_number', part_number) if part_number else component_key
    elif rollup_by == 'subassembly':
        identity = ('subassembly', _component_key(parent_component) if parent_component else None, component_key)
    else:
        identity = component_key
    return identity, attributes

def scan_design(design, field_ids, rollup_by='component'):
    grouped = {}
    root = design.rootComponent
    occurrence_contexts = _flat_occurrences(root, rollup_by == 'subassembly')
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
            _component_property(component, 'partNumber'), _component_property(component, 'description'),
            _material_name(component),
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

def _tree_signature(occurrence):
    """Return a stable shape signature for an occurrence and its descendants.

    Repeated sibling assemblies can only be represented by one rolled-up tree
    node when their contents are identical. Grouping solely by component
    definition loses the children that only occur in the second or third
    instance of an assembly. The signature keeps equivalent subtrees together
    while preserving distinct assemblies and all of their assigned parts.
    """
    children = _visible(getattr(occurrence, 'childOccurrences', None))
    return (_component_key(occurrence.component),
            tuple(sorted((_tree_signature(child) for child in children), key=repr)))

def _hierarchical_root_occurrences(root):
    """Use the root tree when available, with a visible-data fallback.

    `root.occurrences` is normally authoritative. Some imported designs expose
    their occurrences only through `allOccurrences`; retaining those rows at
    level zero is preferable to returning an empty hierarchical BOM.
    """
    occurrences = _visible(getattr(root, 'occurrences', None))
    if occurrences:
        return occurrences
    return _visible(getattr(root, 'allOccurrences', None))

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
        # Aggregate equivalent sibling subtrees only. Fusion can hand back a new
        # proxy per occurrence, so entityToken keeps same definitions together,
        # but child signatures prevent parts from a non-identical assembly
        # instance being silently omitted.
        grouped = {}
        for occurrence in occurrences:
            component = occurrence.component
            key = _tree_signature(occurrence)
            entry = grouped.setdefault(key,
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
                _component_property(component, 'partNumber'), _component_property(component, 'description'),
                _material_name(component),
                _is_linked(component), _shared_values(root, component, field_ids)))
            components[row_id] = component
            if children:
                walk(children, row_id, level + 1, rollup)
    walk(_hierarchical_root_occurrences(root), None, 0, 1)
    return nodes, components
