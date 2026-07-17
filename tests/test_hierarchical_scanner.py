import unittest

from FusionConfigurableBOM.constants import FIELD_ATTRIBUTE_GROUP
from FusionConfigurableBOM.fusion import value_store
from FusionConfigurableBOM.fusion.assembly_scanner import scan_design, scan_design_hierarchical


class _Attribute:
    def __init__(self, value):
        self.value = value


class _Attributes:
    def __init__(self):
        self._store = {}

    def itemByName(self, group, name):
        return self._store.get((group, name))

    def add(self, group, name, value):
        attribute = _Attribute(value)
        self._store[(group, name)] = attribute
        return attribute


class _OccurrenceList:
    """Mimics a Fusion occurrence collection (count + item(index))."""

    def __init__(self, items):
        self._items = list(items)

    @property
    def count(self):
        return len(self._items)

    def item(self, index):
        return self._items[index]


class _Component:
    def __init__(self, name, token):
        self.name = name
        self.entityToken = token
        self.partNumber = ''
        self.description = ''
        self.material = None
        self.isReferencedComponent = False
        self.attributes = _Attributes()


class _Occurrence:
    def __init__(self, component, children=(), suppressed=False):
        self.component = component
        self.childOccurrences = _OccurrenceList(children)
        self.isSuppressed = suppressed


class _Root:
    def __init__(self, occurrences):
        self.occurrences = _OccurrenceList(occurrences)
        self.attributes = _Attributes()


class _Design:
    def __init__(self, occurrences):
        self.rootComponent = _Root(occurrences)


def _instances(component, count, children=()):
    return [_Occurrence(component, children=children) for _ in range(count)]


def _by_name(nodes):
    return {node.component_name: node for node in nodes}


class HierarchicalScannerTests(unittest.TestCase):
    def test_part_number_rollup_keeps_unique_custom_values_in_separate_rows(self):
        first = _Component('Screw A', 'screw_a')
        second = _Component('Screw B', 'screw_b')
        first.partNumber = second.partNumber = 'M3-10'
        design = _Design([_Occurrence(first), _Occurrence(second)])
        value_store.write_value(design.rootComponent, first, 'finish', 'Zinc')
        value_store.write_value(design.rootComponent, second, 'finish', 'Black oxide')

        rows, _ = scan_design(design, ['finish'], 'part_number')

        self.assertEqual(2, len(rows))
        self.assertEqual({'Zinc', 'Black oxide'}, {row.custom_values['finish'] for row in rows})

    def test_part_number_rollup_combines_matching_custom_values(self):
        first = _Component('Screw A', 'screw_a')
        second = _Component('Screw B', 'screw_b')
        first.partNumber = second.partNumber = 'M3-10'
        design = _Design([_Occurrence(first), _Occurrence(second)])
        for component in (first, second):
            value_store.write_value(design.rootComponent, component, 'finish', 'Zinc')

        rows, _ = scan_design(design, ['finish'], 'part_number')

        self.assertEqual(1, len(rows))
        self.assertEqual(2, rows[0].quantity)

    def test_subassembly_rollup_keeps_identical_parts_in_their_parent_rows(self):
        screw = _Component('Screw', 'screw')
        left = _Component('Left assembly', 'left')
        right = _Component('Right assembly', 'right')
        design = _Design([_Occurrence(left, [_Occurrence(screw)]), _Occurrence(right, [_Occurrence(screw)])])

        rows, _ = scan_design(design, [], 'subassembly')

        screws = [row for row in rows if row.component_name == 'Screw']
        self.assertEqual(2, len(screws))
        self.assertEqual({'Left assembly', 'Right assembly'}, {row.parent_assembly for row in screws})

    def _nested_design(self):
        # Root
        #   Gearbox  (x2 identical sub-assemblies)
        #     Screw   (x4 in each Gearbox)
        #     Housing (x1 in each Gearbox)
        #   Bracket  (x1 leaf)
        gearbox = _Component('Gearbox', 'gearbox')
        screw = _Component('Screw', 'screw')
        housing = _Component('Housing', 'housing')
        bracket = _Component('Bracket', 'bracket')
        gearbox_children = _instances(screw, 4) + _instances(housing, 1)
        gearbox_instances = _instances(gearbox, 2, children=gearbox_children)
        return _Design(gearbox_instances + _instances(bracket, 1))

    def test_tree_is_flattened_parent_before_child_with_levels(self):
        nodes, _ = scan_design_hierarchical(self._nested_design(), [])
        self.assertEqual(
            [(node.component_name, node.level) for node in nodes],
            [('Gearbox', 0), ('Screw', 1), ('Housing', 1), ('Bracket', 0)])

    def test_structured_quantity_counts_identical_siblings(self):
        nodes = _by_name(scan_design_hierarchical(self._nested_design(), [])[0])
        self.assertEqual(nodes['Gearbox'].quantity, 2)
        self.assertEqual(nodes['Screw'].quantity, 4)
        self.assertEqual(nodes['Bracket'].quantity, 1)

    def test_total_quantity_rolls_up_through_the_parent_chain(self):
        nodes = _by_name(scan_design_hierarchical(self._nested_design(), [])[0])
        # Screw: 4 per Gearbox * 2 Gearboxes = 8 in the whole design.
        self.assertEqual(nodes['Screw'].total_quantity, 8)
        self.assertEqual(nodes['Housing'].total_quantity, 2)
        self.assertEqual(nodes['Gearbox'].total_quantity, 2)
        self.assertEqual(nodes['Bracket'].total_quantity, 1)

    def test_assembly_flag_and_parent_links(self):
        nodes, _ = scan_design_hierarchical(self._nested_design(), [])
        by_name = _by_name(nodes)
        self.assertTrue(by_name['Gearbox'].is_assembly)
        self.assertFalse(by_name['Screw'].is_assembly)
        self.assertIsNone(by_name['Gearbox'].parent_id)
        self.assertEqual(by_name['Screw'].parent_id, by_name['Gearbox'].row_id)

    def test_components_map_targets_each_row(self):
        nodes, components = scan_design_hierarchical(self._nested_design(), [])
        self.assertEqual(set(components), {node.row_id for node in nodes})
        self.assertEqual(components[_by_name(nodes)['Screw'].row_id].name, 'Screw')

    def test_suppressed_occurrences_are_excluded(self):
        keeper = _Component('Keeper', 'keeper')
        skipped = _Component('Skipped', 'skipped')
        design = _Design([_Occurrence(keeper), _Occurrence(skipped, suppressed=True)])
        nodes, _ = scan_design_hierarchical(design, [])
        self.assertEqual([node.component_name for node in nodes], ['Keeper'])

    def test_same_definition_under_two_parents_makes_two_nodes(self):
        # A screw definition reused in two sub-assemblies is two tree nodes, each
        # with its own path-scoped quantities, but one shared set of values.
        screw = _Component('Screw', 'screw')
        assembly_a = _Component('Assembly A', 'assembly_a')
        assembly_b = _Component('Assembly B', 'assembly_b')
        design = _Design([
            _Occurrence(assembly_a, children=_instances(screw, 2)),
            _Occurrence(assembly_b, children=_instances(screw, 3)),
        ])
        value_store.write_value(design.rootComponent, screw, 'manufacturer', 'Acme')

        nodes, _ = scan_design_hierarchical(design, ['manufacturer'])
        screws = [node for node in nodes if node.component_name == 'Screw']
        self.assertEqual(sorted(node.quantity for node in screws), [2, 3])
        self.assertTrue(all(node.custom_values['manufacturer'] == 'Acme' for node in screws))

    def test_reads_legacy_component_values(self):
        component = _Component('Bracket', 'bracket')
        component.attributes.add(FIELD_ATTRIBUTE_GROUP, 'manufacturer', 'LegacyCo')
        nodes, _ = scan_design_hierarchical(_Design([_Occurrence(component)]), ['manufacturer'])
        self.assertEqual(nodes[0].custom_values['manufacturer'], 'LegacyCo')

    def test_empty_design_returns_no_nodes(self):
        nodes, components = scan_design_hierarchical(_Design([]), [])
        self.assertEqual(nodes, [])
        self.assertEqual(components, {})


if __name__ == '__main__':
    unittest.main()
