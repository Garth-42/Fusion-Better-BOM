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

    def test_refresh_action_scans_the_design_and_sends_rows(self):
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        scanned_rows = [ConceptBomRow('row_1', 'Bracket', 2)]
        with patch('FusionConfigurableBOM.ui.palette_controller.scan_design',
                   return_value=(scanned_rows, {'row_1': object()})) as scan_design:
            controller.receive(None, json.dumps({'action': 'refresh'}))

        scan_design.assert_called_once()
        self.assertEqual(scanned_rows, controller.rows)
        state = next(response for response in responses if response['type'] == 'state')
        self.assertEqual(1, len(state['table']['rows']))
        self.assertEqual('Bracket', state['table']['rows'][0]['values']['component_name'])
        # A refresh must not report "Saved." — it only ever sends scanned state.
        self.assertFalse(any(response['type'] == 'status' and response['message'] == 'Saved.'
                             for response in responses))

    def test_save_as_creates_a_named_copy_with_pending_column_edits(self):
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)
        raw_config = {
            'schema_version': 1,
            'fields': [],
            'views': [{
                'view_id': 'general', 'name': 'General BOM',
                'columns': [{'source_type': 'builtin', 'source_id': 'quantity',
                             'header': 'Count', 'visible': True, 'width': 70}],
            }],
        }

        controller.receive(None, json.dumps({
            'action': 'save_as_view', 'config': raw_config, 'view_id': 'general',
            'name': 'Assembly summary',
        }))

        views = controller.store.config.views
        self.assertEqual(['General BOM', 'Assembly summary'], [view.name for view in views])
        self.assertEqual('Count', views[1].columns[0].header)
        self.assertNotEqual(views[0].view_id, views[1].view_id)
        self.assertTrue(any(response['type'] == 'status' and response['message'] == 'Saved.'
                            for response in responses))

    def test_copy_table_uses_the_host_clipboard(self):
        app = type('App', (), {'activeProduct': None})()
        controller = PaletteController(app)
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        with patch('FusionConfigurableBOM.ui.palette_controller.copy_text') as copy_text:
            controller.receive(None, json.dumps({
                'action': 'copy_table', 'tsv': 'Qty\tPart\r\n1\tBracket', 'row_count': 1,
            }))

        copy_text.assert_called_once_with('Qty\tPart\r\n1\tBracket')
        self.assertEqual({'type': 'copy_result', 'copied': True, 'row_count': 1}, responses[0])
