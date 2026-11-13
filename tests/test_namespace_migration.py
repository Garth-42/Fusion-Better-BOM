"""Data saved under the old `com.company` attribute groups must keep working."""

import json
import unittest

from FusionConfigurableBOM import constants
from FusionConfigurableBOM.fusion import attribute_store, value_store
from FusionConfigurableBOM.fusion.assembly_scanner import scan_design
from FusionConfigurableBOM.persistence.configuration_store import (
    FusionConfigurationStore,
    default_configuration,
    dumps,
)
from tests.test_hierarchical_scanner import _Component, _Occurrence, _Root


class _Attribute:
    def __init__(self, store, key, value):
        self._store, self._key, self.value = store, key, value

    def deleteMe(self):
        del self._store[self._key]


class _Attributes:
    def __init__(self):
        self.store = {}

    def itemByName(self, group, name):
        return self.store.get((group, name))

    def add(self, group, name, value):
        self.store[(group, name)] = _Attribute(self.store, (group, name), value)
        return self.store[(group, name)]

    def groups(self):
        return {group for group, _ in self.store}


def _root(occurrences=()):
    root = _Root(list(occurrences))
    root.attributes = _Attributes()
    root.entityToken = 'root'
    return root


class NamespaceMigrationTests(unittest.TestCase):
    def test_new_groups_use_the_namespace_and_match_the_manifest(self):
        with open('FusionConfigurableBOM/FusionConfigurableBOM.manifest') as handle:
            self.assertEqual(constants.NAMESPACE, json.load(handle)['id'])
        self.assertNotIn('com.company', constants.NAMESPACE)
        for group in (
            constants.CONFIG_ATTRIBUTE_GROUP,
            constants.FIELD_ATTRIBUTE_GROUP,
            constants.VALUE_ATTRIBUTE_GROUP,
        ):
            self.assertTrue(group.startswith(constants.NAMESPACE))

    def test_configuration_saved_under_the_old_group_loads_and_moves_on_save(self):
        root = _root()
        config = default_configuration()
        config.views[0].name = 'My renamed BOM'
        root.attributes.add(
            constants.LEGACY_CONFIG_ATTRIBUTE_GROUP, constants.CONFIG_ATTRIBUTE_NAME, dumps(config)
        )
        store = FusionConfigurationStore()

        loaded = store.load(root)
        self.assertEqual('My renamed BOM', loaded.views[0].name)

        store.save(root, loaded)
        self.assertEqual({constants.CONFIG_ATTRIBUTE_GROUP}, root.attributes.groups())
        self.assertEqual('My renamed BOM', store.load(root).views[0].name)

    def test_value_map_saved_under_the_old_group_is_read_and_moves_on_write(self):
        component = _Component('Bracket', 'token-a')
        root = _root([_Occurrence(component)])
        root.attributes.add(
            constants.LEGACY_VALUE_ATTRIBUTE_GROUP,
            constants.VALUE_ATTRIBUTE_NAME,
            json.dumps({'token-a': {'supplier': 'Acme'}}),
        )
        design = type('Design', (), {'rootComponent': root})()

        rows, _ = scan_design(design, ['supplier', 'manufacturer'])
        self.assertEqual('Acme', rows[0].custom_values['supplier'])

        value_store.write_value(root, component, 'manufacturer', 'Bolt Co')
        self.assertEqual({constants.VALUE_ATTRIBUTE_GROUP}, root.attributes.groups())
        self.assertEqual(
            {'supplier': 'Acme', 'manufacturer': 'Bolt Co'},
            value_store.read_values(root, component, ['supplier', 'manufacturer']),
        )

    def test_component_values_under_the_old_group_are_read_written_and_renamed(self):
        component = _Component('Bracket', 'token-a')
        component.attributes = _Attributes()
        component.attributes.add(constants.LEGACY_FIELD_ATTRIBUTE_GROUP, 'supplier', 'Acme')
        component.attributes.add(constants.LEGACY_FIELD_ATTRIBUTE_GROUP, 'maker', 'Bolt Co')

        self.assertEqual({'supplier': 'Acme'}, attribute_store.read_values(component, ['supplier']))

        attribute_store.write_value(component, 'supplier', 'Zenith')
        self.assertEqual('Zenith', attribute_store.read_values(component, ['supplier'])['supplier'])
        self.assertIsNone(component.attributes.itemByName(constants.LEGACY_FIELD_ATTRIBUTE_GROUP, 'supplier'))

        attribute_store.rename_value(component, 'maker', 'manufacturer')
        self.assertEqual(
            {'maker': '', 'manufacturer': 'Bolt Co'},
            attribute_store.read_values(component, ['maker', 'manufacturer']),
        )
        self.assertEqual({constants.FIELD_ATTRIBUTE_GROUP}, component.attributes.groups())

    def test_new_data_wins_when_both_groups_exist(self):
        root = _root()
        for group, name in (
            (constants.LEGACY_CONFIG_ATTRIBUTE_GROUP, 'Old'),
            (constants.CONFIG_ATTRIBUTE_GROUP, 'New'),
        ):
            config = default_configuration()
            config.views[0].name = name
            root.attributes.add(group, constants.CONFIG_ATTRIBUTE_NAME, dumps(config))
        self.assertEqual('New', FusionConfigurationStore().load(root).views[0].name)


if __name__ == '__main__':
    unittest.main()
