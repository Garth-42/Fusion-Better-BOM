"""Regression tests for bugs found in the code review."""

import json
import unittest
from unittest.mock import patch

from FusionConfigurableBOM.constants import VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME
from FusionConfigurableBOM.domain.models import configuration_to_dict
from FusionConfigurableBOM.fusion import value_store
from FusionConfigurableBOM.fusion.assembly_scanner import scan_design, scan_design_hierarchical
from FusionConfigurableBOM.persistence import configuration_store
from FusionConfigurableBOM.persistence.configuration_store import ConfigurationError
from FusionConfigurableBOM.ui.palette_controller import PaletteController
from tests.test_hierarchical_scanner import _Attributes, _Component, _Occurrence, _OccurrenceList, _Root


class _Bodies:
    count = 1


class _Design:
    def __init__(self, root):
        self.rootComponent = root


def _root(occurrences, token='root'):
    root = _Root(occurrences)
    root.attributes = _Attributes()
    root.entityToken = token
    root.name = 'Root'
    return root


def _controller(design):
    app = type('App', (), {})()
    app.activeProduct = design
    controller = PaletteController(app)
    responses = []
    controller.send = lambda palette, payload: responses.append(payload)
    return controller, app, responses


def _send(controller, **message):
    controller.receive(None, json.dumps(message))


def _stored_map(root):
    return json.loads(root.attributes.itemByName(VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME).value)


class SinglePartDesignTests(unittest.TestCase):
    def _design(self):
        root = _root([])
        root.bRepBodies = _Bodies()
        root.partNumber, root.description, root.material = 'P-1', '', None
        return _Design(root)

    def test_values_on_a_single_part_design_survive_a_refresh(self):
        design = self._design()
        controller, _, _ = _controller(design)
        controller.refresh(None, 'purchasing_demo', True)
        _send(controller, action='save_cell', row_id='row_1', field_id='supplier', value='Acme')
        controller.refresh(None, 'purchasing_demo', True)
        self.assertEqual('Acme', controller.rows[0].custom_values['supplier'])

    def test_single_part_design_appears_in_both_structures(self):
        design = self._design()
        self.assertEqual(['Root'], [row.component_name for row in scan_design(design, [])[0]])
        self.assertEqual(['Root'], [node.component_name for node in scan_design_hierarchical(design, [])[0]])


class RollupEditTests(unittest.TestCase):
    def test_editing_a_part_number_rollup_row_updates_every_merged_component(self):
        first, second = _Component('A', 'ta'), _Component('B', 'tb')
        first.partNumber = second.partNumber = 'PN-1'
        design = _Design(_root([_Occurrence(first), _Occurrence(second)]))
        controller, _, _ = _controller(design)
        controller.refresh(None, 'part_number_rollup', True)
        self.assertEqual([2], [row.quantity for row in controller.rows])

        _send(controller, action='save_cell', row_id='row_1', field_id='supplier', value='Acme')
        controller.refresh(None, 'part_number_rollup', True)

        self.assertEqual(
            [(2, 'Acme')], [(row.quantity, row.custom_values['supplier']) for row in controller.rows]
        )

    def test_a_cell_edit_keeps_the_snapshot_and_shows_in_other_formats(self):
        component = _Component('A', 'ta')
        design = _Design(_root([_Occurrence(component)]))
        controller, _, _ = _controller(design)
        import FusionConfigurableBOM.ui.palette_controller as module

        with patch.object(module, 'scan_design_snapshot', wraps=module.scan_design_snapshot) as snapshot:
            controller.refresh(None, 'general', True)
            _send(controller, action='save_cell', row_id='row_1', field_id='supplier', value='Acme')
            controller.refresh(None, 'structured')
            controller.refresh(None, 'purchasing_demo')
        self.assertEqual(1, snapshot.call_count)
        self.assertEqual('Acme', controller.rows[0].custom_values['supplier'])


class DocumentSwitchTests(unittest.TestCase):
    def test_edits_are_refused_after_the_active_design_changes(self):
        design_a = _Design(_root([_Occurrence(_Component('A', 'ta'))], 'root-a'))
        design_b = _Design(_root([_Occurrence(_Component('X', 'tx'))], 'root-b'))
        controller, app, responses = _controller(design_a)
        controller.refresh(None, 'purchasing_demo', True)
        app.activeProduct = design_b

        _send(controller, action='save_cell', row_id='row_1', field_id='supplier', value='Acme')
        _send(controller, action='add_column', view_id='general', field_id='supplier')

        errors = [r['message'] for r in responses if r['type'] == 'error']
        self.assertEqual(2, len(errors))
        self.assertIn('active design changed', errors[0])
        self.assertIsNone(
            design_b.rootComponent.attributes.itemByName(VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME)
        )

    def test_document_activation_asks_a_visible_palette_to_rescan(self):
        palette = type('Palette', (), {'isValid': True, 'isVisible': True})()
        controller, app, responses = _controller(None)
        palettes = type('Palettes', (), {'itemById': lambda self, palette_id: palette})()
        app.userInterface = type('UI', (), {'palettes': palettes})()
        controller.document_activated()
        self.assertEqual([{'type': 'document_changed'}], responses)

    def test_design_is_found_outside_the_design_workspace(self):
        design = _Design(_root([_Occurrence(_Component('A', 'ta'))]))
        controller, app, _ = _controller(object())  # e.g. the CAM product
        products = type('Products', (), {'itemByProductType': lambda self, name: design})()
        app.activeDocument = type('Document', (), {'products': products})()
        controller.refresh(None, 'general', True)
        self.assertEqual(['A'], [row.component_name for row in controller.rows])


class ErrorMessageTests(unittest.TestCase):
    def setUp(self):
        self.design = _Design(_root([_Occurrence(_Component('A', 'ta'))]))
        self.controller, self.app, self.responses = _controller(self.design)
        self.controller.refresh(None, 'general', True)
        self.responses.clear()

    def _error(self):
        self.assertEqual(['error'], [r['type'] for r in self.responses])
        return self.responses[0]['message']

    def test_unknown_view(self):
        _send(self.controller, action='add_column', view_id='gone', field_id='supplier')
        self.assertIn('no longer exists', self._error())

    def test_stale_row(self):
        _send(self.controller, action='save_cell', row_id='row_99', field_id='supplier', value='x')
        self.assertIn('Refresh', self._error())

    def test_no_design(self):
        self.app.activeProduct = object()
        _send(self.controller, action='add_column', view_id='general', field_id='supplier')
        self.assertIn('Open a Fusion design', self._error())

    def test_unknown_action(self):
        _send(self.controller, action='nope')
        self.assertIn('Unknown action', self._error())

    def test_duplicate_and_invalid_new_fields_are_rejected(self):
        _send(self.controller, action='new_field', field_id='supplier', label='Supplier', view_id='general')
        self.assertIn('already exists', self._error())
        self.responses.clear()
        _send(self.controller, action='new_field', field_id='3d', label='3D', view_id='general')
        self.assertIn('start with a lowercase letter', self._error())

    def test_default_formats_cannot_be_deleted_but_custom_ones_can(self):
        _send(self.controller, action='delete_view', view_id='structured')
        self.assertIn('Default formats', self._error())
        self.responses.clear()
        _send(
            self.controller,
            action='save_as_view',
            view_id='general',
            name='Mine',
            config=configuration_to_dict(self.controller.store.load(self.design.rootComponent)),
        )
        view_id = next(r for r in self.responses if r['type'] == 'state')['table']['view_id']
        _send(self.controller, action='delete_view', view_id=view_id)
        views = self.controller.store.load(self.design.rootComponent).views
        self.assertNotIn(view_id, [view.view_id for view in views])


class ValueStoreIdentityTests(unittest.TestCase):
    def test_values_are_keyed_by_the_persistent_component_id(self):
        root, component = _root([]), _Component('A', 'token-1')
        component.id = 'guid-1'
        value_store.write_value(root, component, 'supplier', 'Acme')
        self.assertEqual({'id:guid-1': {'supplier': 'Acme'}}, _stored_map(root))
        # A different token string for the same component must not lose the value.
        component.entityToken = 'token-2'
        self.assertEqual({'supplier': 'Acme'}, value_store.read_values(root, component, ['supplier']))

    def test_legacy_token_entries_are_read_and_folded_into_the_id_entry(self):
        root, component = _root([]), _Component('A', 'token-1')
        value_store.write_value(root, component, 'supplier', 'Acme')  # stored under the token
        component.id = 'guid-1'
        self.assertEqual({'supplier': 'Acme'}, value_store.read_values(root, component, ['supplier']))
        value_store.write_value(root, component, 'manufacturer', 'Bolt Co')
        self.assertEqual({'id:guid-1': {'supplier': 'Acme', 'manufacturer': 'Bolt Co'}}, _stored_map(root))


class ScannerFallbackTests(unittest.TestCase):
    def test_all_occurrences_fallback_does_not_double_count_nested_parts(self):
        part = _Component('Part', 'part')
        nested = _Occurrence(part)
        nested.assemblyContext = object()  # it has a parent occurrence
        top = _Occurrence(_Component('Sub', 'sub'), [nested])
        top.assemblyContext = None
        root = _root([])
        root.allOccurrences = _OccurrenceList([top, nested])
        rows, _ = scan_design(_Design(root), [])
        self.assertEqual([('Part', 1)], [(row.component_name, row.quantity) for row in rows])


class ConfigurationValidationTests(unittest.TestCase):
    def _raw_with_orphan(self):
        raw = configuration_to_dict(configuration_store.default_configuration())
        raw['views'][0]['columns'].append(
            {
                'source_type': 'attribute',
                'source_id': 'missing',
                'header': 'Missing',
                'visible': True,
                'width': None,
            }
        )
        return raw

    def test_editor_input_with_a_column_for_a_missing_field_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            configuration_store.from_dict(self._raw_with_orphan())

    def test_stored_configuration_with_an_orphan_column_still_loads(self):
        config = configuration_store.loads(json.dumps(self._raw_with_orphan()))
        self.assertNotIn('missing', [column.source_id for column in config.views[0].columns])


if __name__ == '__main__':
    unittest.main()
