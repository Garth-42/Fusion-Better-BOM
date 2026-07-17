import unittest

from FusionConfigurableBOM.constants import VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME
from FusionConfigurableBOM.fusion import value_store


class Attribute:
    def __init__(self, value):
        self.value = value


class Attributes:
    def __init__(self):
        self.values = {}
        self.add_calls = []

    def itemByName(self, group, name):
        return self.values.get((group, name))

    def add(self, group, name, value):
        self.add_calls.append((group, name, value))
        attribute = Attribute(value)
        self.values[(group, name)] = attribute
        return attribute


class Root:
    def __init__(self):
        self.attributes = Attributes()


class Component:
    def __init__(self, token):
        self.entityToken = token


class ValueStoreTests(unittest.TestCase):
    def test_write_then_read_round_trips_a_value(self):
        root = Root()
        component = Component('token-a')

        self.assertTrue(value_store.write_value(root, component, 'manufacturer', 'Acme'))

        self.assertEqual({'manufacturer': 'Acme'},
                         value_store.read_values(root, component, ['manufacturer']))

    def test_value_is_stored_on_the_root_value_attribute(self):
        root = Root()
        value_store.write_value(root, Component('token-a'), 'supplier', 'Digikey')

        self.assertIn((VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME), root.attributes.values)

    def test_subsequent_writes_update_the_attribute_in_place(self):
        root = Root()
        component = Component('token-a')

        value_store.write_value(root, component, 'manufacturer', 'Acme')
        value_store.write_value(root, component, 'manufacturer', 'Globex')
        value_store.write_value(root, component, 'supplier', 'Mouser')

        # The map attribute is created once and then updated, never re-added.
        self.assertEqual(1, len(root.attributes.add_calls))
        self.assertEqual({'manufacturer': 'Globex', 'supplier': 'Mouser'},
                         value_store.read_values(root, component, ['manufacturer', 'supplier']))

    def test_read_only_returns_stored_fields_so_blanks_are_preserved(self):
        root = Root()
        component = Component('token-a')
        value_store.write_value(root, component, 'manufacturer', '')

        # A stored empty string is present (an intentional clear); an untouched
        # field is absent so the caller can fall back to a legacy value.
        self.assertEqual({'manufacturer': ''},
                         value_store.read_values(root, component, ['manufacturer', 'supplier']))

    def test_occurrences_that_share_a_token_share_the_value(self):
        root = Root()
        value_store.write_value(root, Component('token-a'), 'manufacturer', 'Acme')

        self.assertEqual({'manufacturer': 'Acme'},
                         value_store.read_values(root, Component('token-a'), ['manufacturer']))

    def test_a_component_without_a_token_is_not_written(self):
        root = Root()

        self.assertFalse(value_store.write_value(root, Component(None), 'manufacturer', 'Acme'))
        self.assertEqual([], root.attributes.add_calls)

    def test_rename_field_migrates_values_across_components(self):
        root = Root()
        value_store.write_value(root, Component('token-a'), 'manufacturer', 'Acme')
        value_store.write_value(root, Component('token-b'), 'manufacturer', 'Globex')

        value_store.rename_field(root, 'manufacturer', 'maker')

        self.assertEqual({'maker': 'Acme'},
                         value_store.read_values(root, Component('token-a'), ['maker']))
        self.assertEqual({'maker': 'Globex'},
                         value_store.read_values(root, Component('token-b'), ['maker']))
        self.assertEqual({}, value_store.read_values(root, Component('token-a'), ['manufacturer']))

    def test_missing_attributes_are_handled_gracefully(self):
        rootless = object()

        self.assertEqual({}, value_store.read_values(rootless, Component('token-a'), ['manufacturer']))
        self.assertFalse(value_store.write_value(rootless, Component('token-a'), 'manufacturer', 'Acme'))


if __name__ == '__main__':
    unittest.main()
