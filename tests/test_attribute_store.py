import unittest

from FusionConfigurableBOM.constants import (
    CONFIG_ATTRIBUTE_GROUP,
    CONFIG_ATTRIBUTE_NAME,
    FIELD_ATTRIBUTE_GROUP,
)
from FusionConfigurableBOM.fusion.attribute_store import write_value
from FusionConfigurableBOM.persistence.configuration_store import (
    FusionConfigurationStore,
    default_configuration,
)


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


class AttributeStoreTests(unittest.TestCase):
    def test_write_value_updates_an_existing_attribute(self):
        attributes = Attributes()
        existing = Attribute('old')
        attributes.values[(FIELD_ATTRIBUTE_GROUP, 'manufacturer')] = existing
        component = type('Component', (), {'attributes': attributes})()

        write_value(component, 'manufacturer', 'Acme')

        self.assertEqual('Acme', existing.value)
        self.assertEqual([], attributes.add_calls)

    def test_configuration_store_updates_an_existing_attribute(self):
        attributes = Attributes()
        existing = Attribute('old configuration')
        attributes.values[(CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME)] = existing
        root = type('Root', (), {'attributes': attributes})()

        FusionConfigurationStore().save(root, default_configuration())

        self.assertIn('"schema_version":2', existing.value)
        self.assertEqual([], attributes.add_calls)
