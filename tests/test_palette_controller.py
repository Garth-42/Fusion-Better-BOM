import json
import unittest
from unittest.mock import patch

from FusionConfigurableBOM.domain.models import ConceptBomRow
from FusionConfigurableBOM.persistence.configuration_store import default_configuration
from FusionConfigurableBOM.ui.palette_controller import PaletteController


class FakeStore:
    def __init__(self, config):
        self.config = config

    def load(self, root):
        return self.config

    def save(self, root, config):
        self.config = config


class PaletteControllerTests(unittest.TestCase):
    def test_saving_a_cell_updates_cached_table_without_rescanning(self):
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        controller.rows = [ConceptBomRow('row_1', 'Bracket', 1, custom_values={'manufacturer': ''})]
        controller.components = {'row_1': object()}
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        with patch('FusionConfigurableBOM.ui.palette_controller.write_value') as write_value:
            controller.receive(None, json.dumps({
                'action': 'save_cell', 'row_id': 'row_1', 'field_id': 'manufacturer',
                'value': 'Acme', 'view_id': 'purchasing_demo',
            }))

        write_value.assert_called_once_with(controller.components['row_1'], 'manufacturer', 'Acme')
        state = next(response for response in responses if response['type'] == 'state')
        self.assertEqual('Acme', state['table']['rows'][0]['values']['manufacturer'])

