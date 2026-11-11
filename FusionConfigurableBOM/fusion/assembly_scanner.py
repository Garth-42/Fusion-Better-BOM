from dataclasses import dataclass, field

from ..domain.models import ConceptBomRow, HierarchicalBomNode
from .attribute_store import read_values as read_component_values
from .identity import component_key
from .value_store import load_map
from .value_store import read_values as read_root_values


def _items(collection):
    if hasattr(collection, 'count') and hasattr(collection, 'item'):
        return [collection.item(index) for index in range(collection.count)]
    if isinstance(getattr(collection, 'count', None), int):
        # Minimal test doubles and a few malformed API collections advertise a
        # count without indexed access; they cannot provide child occurrences.
        return []
    if getattr(collection, 'count', None) == 0:
        return []
    return list(collection or [])


def _visible(occurrences):
    return [
        occurrence for occurrence in _items(occurrences) if not getattr(occurrence, 'isSuppressed', False)
    ]


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


def _has_bodies(component):
    bodies = _component_property(component, 'bRepBodies')
    return bool(bodies and bodies.count > 0)


@dataclass
class ParsedComponent:
    component: object
    key: tuple
    name: str
    part_number: str | None
    description: str | None
    material: str | None
    linked: bool
    custom_values: dict[str, str]


@dataclass
class ParsedOccurrence:
    component: ParsedComponent
    children: list = field(default_factory=list)


@dataclass
class BomSnapshot:
    root: object
    roots: list[ParsedOccurrence]
    # `all_nodes` is parent-before-child and is reused by every flat roll-up.
    all_nodes: list[tuple[ParsedOccurrence, ParsedOccurrence | None]]


def _top_level(occurrences):
    # allOccurrences lists nested occurrences too; `parse` already recurses into
    # children, so only start from the ones with no parent assembly. If none
    # report a context (test doubles, odd imports) keep them all.
    top = [
        occurrence for occurrence in occurrences if _component_property(occurrence, 'assemblyContext') is None
    ]
    return top or occurrences


def scan_design_snapshot(design, field_ids):
    """Read Fusion occurrence/component data once into a pure-Python snapshot.

    Format changes must only aggregate this snapshot; they must not invoke Fusion
    collections or component properties again. The snapshot is scoped to one
    configured field set; cell edits patch `ParsedComponent.custom_values` in
    place so it stays current without another walk.
    """
    root = design.rootComponent
    components, all_nodes = {}, []
    stored_values = load_map(root)  # Parsed once, not once per component.

    def parsed_component(component):
        key = component_key(component)
        if key not in components:
            values = read_component_values(component, field_ids)
            values.update(read_root_values(root, component, field_ids, stored_values))
            components[key] = ParsedComponent(
                component,
                key,
                _component_property(component, 'name', ''),
                _component_property(component, 'partNumber'),
                _component_property(component, 'description'),
                _material_name(component),
                bool(_component_property(component, 'isReferencedComponent', False)),
                values,
            )
        return components[key]

    def parse(occurrence, parent=None):
        node = ParsedOccurrence(parsed_component(occurrence.component))
        all_nodes.append((node, parent))
        node.children = [
            parse(child, node) for child in _visible(getattr(occurrence, 'childOccurrences', None))
        ]
        return node

    root_occurrences = _visible(getattr(root, 'occurrences', None))
    if not root_occurrences:
        # Imported designs sometimes only expose allOccurrences.
        root_occurrences = _top_level(_visible(getattr(root, 'allOccurrences', None)))
    roots = [parse(occurrence) for occurrence in root_occurrences]
    if not roots and _has_bodies(root):
        # A single-part design has no occurrences: the root itself is the part.
        # It goes through parsed_component so its saved values are read back.
        node = ParsedOccurrence(parsed_component(root))
        roots, all_nodes = [node], [(node, None)]
    return BomSnapshot(root, roots, all_nodes)


def _rollup_key(node, parent, rollup_by):
    component = node.component
    attributes = tuple(sorted(component.custom_values.items()))
    if rollup_by == 'part_number' and component.part_number:
        identity = ('part_number', component.part_number)
    elif rollup_by == 'subassembly':
        identity = ('subassembly', parent.component.key if parent else None, component.key)
    else:
        identity = component.key
    return identity, attributes


def scan_design_from_snapshot(snapshot, rollup_by='component'):
    """Build a flat table from a previously parsed snapshot without Fusion IO."""
    # Every non-empty tree has leaves, so this is empty only for an empty design.
    candidates = [(node, parent) for node, parent in snapshot.all_nodes if not node.children]

    grouped = {}
    for node, parent in candidates:
        key = _rollup_key(node, parent, rollup_by)
        entry = grouped.setdefault(key, {'node': node, 'parent': parent, 'quantity': 0, 'members': {}})
        entry['quantity'] += 1
        # A part-number roll-up can merge several definitions into one row; keep
        # them all so an edit to the row reaches every one of them.
        entry['members'].setdefault(node.component.key, node.component)
    rows, components = [], {}
    for index, entry in enumerate(grouped.values(), 1):
        item, parent = entry['node'].component, entry['parent']
        row_id = f'row_{index}'
        rows.append(
            ConceptBomRow(
                row_id,
                item.name,
                entry['quantity'],
                item.part_number,
                item.description,
                item.material,
                item.linked,
                dict(item.custom_values),
                parent.component.name if parent else None,
                list(entry['members'].values()),
            )
        )
        components[row_id] = item.component
    return rows, components


def _tree_signature(node, cache):
    node_id = id(node)
    if node_id not in cache:
        cache[node_id] = (
            node.component.key,
            tuple(sorted((_tree_signature(child, cache) for child in node.children), key=repr)),
        )
    return cache[node_id]


def scan_design_hierarchical_from_snapshot(snapshot):
    """Build the structured BOM from a snapshot without another Fusion walk."""
    nodes, components, counter, signature_cache = [], {}, [0], {}

    def walk(siblings, parent_id, level, parent_rollup):
        grouped = {}
        for node in siblings:
            entry = grouped.setdefault(_tree_signature(node, signature_cache), {'node': node, 'quantity': 0})
            entry['quantity'] += 1
        for entry in grouped.values():
            source, quantity = entry['node'], entry['quantity']
            item, total = source.component, quantity * parent_rollup
            counter[0] += 1
            row_id = f'row_{counter[0]}'
            nodes.append(
                HierarchicalBomNode(
                    row_id,
                    item.name,
                    level,
                    parent_id,
                    quantity,
                    total,
                    bool(source.children),
                    item.part_number,
                    item.description,
                    item.material,
                    item.linked,
                    dict(item.custom_values),
                    [item],
                )
            )
            components[row_id] = item.component
            if source.children:
                walk(source.children, row_id, level + 1, total)

    walk(snapshot.roots, None, 0, 1)
    return nodes, components


# Compatibility wrappers for callers outside the palette controller.
def scan_design(design, field_ids, rollup_by='component'):
    return scan_design_from_snapshot(scan_design_snapshot(design, field_ids), rollup_by)


def scan_design_hierarchical(design, field_ids):
    return scan_design_hierarchical_from_snapshot(scan_design_snapshot(design, field_ids))
