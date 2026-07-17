import json
import sys
import types
import unittest
from unittest.mock import patch

from FusionConfigurableBOM.domain.models import ConceptBomRow, configuration_to_dict
from FusionConfigurableBOM.persistence.configuration_store import default_configuration
from FusionConfigurableBOM.ui.palette_controller import PaletteController


class FakeStore:
    def __init__(self, config):
        self.config = config

    def load(self, root):
        return self.config

    def save(self, root, config):
        self.config = config


class FakeAttribute:
    def __init__(self, value):
        self.value = value


class FakeAttributes:
    def __init__(self):
        self.store = {}

    def itemByName(self, group, name):
        return self.store.get((group, name))

    def add(self, group, name, value):
        attribute = FakeAttribute(value)
        self.store[(group, name)] = attribute
        return attribute


class FakeComponent:
    def __init__(self, token):
        self.entityToken = token
        self.attributes = FakeAttributes()
        self.isReferencedComponent = False


class FakeRoot:
    def __init__(self):
        self.attributes = FakeAttributes()


class _RecordingPalette:
    def __init__(self, is_visible=False, is_valid=True):
        self.isValid = is_valid
        self.dockingState = None
        self._is_visible = is_visible
        self.visibility_writes = []

    @property
    def isVisible(self):
        return self._is_visible

    @isVisible.setter
    def isVisible(self, value):
        self._is_visible = value
        self.visibility_writes.append(value)


def _palette_app(existing, created):
    palettes = type('Palettes', (), {
        'itemById': lambda self, palette_id: existing,
        'add': lambda self, *args: created,
    })()
    return type('App', (), {'userInterface': type('UserInterface', (), {'palettes': palettes})()})()


def _adsk_modules():
    docking_states = type('PaletteDockingStates', (), {'PaletteDockStateFloating': 'floating'})
    adsk = types.ModuleType('adsk')
    adsk.core = types.SimpleNamespace(PaletteDockingStates=docking_states)
    return {'adsk': adsk, 'adsk.core': adsk.core}


class PaletteControllerTests(unittest.TestCase):
    def test_show_opens_a_new_palette_in_a_floating_window(self):
        palette = type('Palette', (), {'dockingState': None, 'isVisible': False})()
        palettes = type('Palettes', (), {
            'itemById': lambda self, palette_id: None,
            'add': lambda self, *args: palette,
        })()
        app = type('App', (), {'userInterface': type('UserInterface', (), {'palettes': palettes})()})()
        controller = PaletteController(app)
        docking_states = type('PaletteDockingStates', (), {
            'PaletteDockStateFloating': 'floating',
        })
        adsk = types.ModuleType('adsk')
        adsk.core = types.SimpleNamespace(PaletteDockingStates=docking_states)

        with patch.dict(sys.modules, {'adsk': adsk, 'adsk.core': adsk.core}):
            result = controller.show()

        self.assertIs(palette, result)
        self.assertEqual('floating', palette.dockingState)
        self.assertTrue(palette.isVisible)

    def test_show_wires_the_html_handler_only_when_the_palette_is_built(self):
        # The incoming-message handler must be attached at creation so it also
        # re-attaches after a workspace switch rebuilds the palette.
        palette = _RecordingPalette(is_visible=False)
        controller = PaletteController(_palette_app(existing=None, created=palette))
        created_with = []
        controller.on_palette_created(created_with.append)

        with patch.dict(sys.modules, _adsk_modules()):
            controller.show()

        self.assertEqual([palette], created_with)
        self.assertTrue(palette.isVisible)

    def test_show_rebuilds_a_palette_invalidated_by_a_workspace_switch(self):
        # Fusion deletes palettes when the workspace changes; the stale handle is
        # invalid and must be replaced rather than reused.
        stale = _RecordingPalette(is_visible=True, is_valid=False)
        fresh = _RecordingPalette(is_visible=False)
        controller = PaletteController(_palette_app(existing=stale, created=fresh))

        with patch.dict(sys.modules, _adsk_modules()):
            result = controller.show()

        self.assertIs(fresh, result)
        self.assertEqual('floating', fresh.dockingState)
        self.assertTrue(fresh.isVisible)

    def test_show_raises_an_already_visible_palette_back_to_the_front(self):
        # Re-opening a palette that is up but buried toggles visibility so its
        # floating window re-stacks above the tree and collapsed panels.
        palette = _RecordingPalette(is_visible=True)
        controller = PaletteController(_palette_app(existing=palette, created=None))

        with patch.dict(sys.modules, _adsk_modules()):
            controller.show()

        self.assertEqual([False, True], palette.visibility_writes)
        self.assertTrue(palette.isVisible)

    def test_saving_a_cell_updates_cached_value_without_redrawing_the_input(self):
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
        self.assertEqual('Acme', controller.rows[0].custom_values['manufacturer'])
        self.assertFalse(any(response['type'] == 'state' for response in responses))
        self.assertIn({'type': 'status', 'message': 'Saved.'}, responses)

    def test_saving_a_cell_persists_the_value_on_the_design_root(self):
        # The value must land on the active design's root (which is always saved
        # with the design), not only on the component (which may live in another
        # file and would be lost on close/reopen).
        root = FakeRoot()
        component = FakeComponent('token-a')
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        controller.rows = [ConceptBomRow('row_1', 'Bracket', 1, custom_values={'manufacturer': ''})]
        controller.components = {'row_1': component}
        controller.send = lambda palette, payload: None

        controller.receive(None, json.dumps({
            'action': 'save_cell', 'row_id': 'row_1', 'field_id': 'manufacturer',
            'value': 'Acme', 'view_id': 'purchasing_demo',
        }))

        from FusionConfigurableBOM.fusion import value_store
        self.assertEqual({'manufacturer': 'Acme'},
                         value_store.read_values(root, component, ['manufacturer']))

    def test_refresh_routes_a_hierarchical_view_to_the_tree_scan(self):
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        controller.send = lambda palette, payload: None

        with patch('FusionConfigurableBOM.ui.palette_controller.scan_design_snapshot',
                   return_value=object()) as snapshot, \
             patch('FusionConfigurableBOM.ui.palette_controller.scan_design_hierarchical_from_snapshot',
                   return_value=([], {})) as hierarchical, \
             patch('FusionConfigurableBOM.ui.palette_controller.scan_design_from_snapshot') as flat:
            controller.receive(None, json.dumps({'action': 'refresh', 'view_id': 'structured'}))

        hierarchical.assert_called_once()
        flat.assert_not_called()
        snapshot.assert_called_once()

    def test_switching_back_to_a_scanned_format_reuses_its_cached_result(self):
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        controller.send = lambda palette, payload: None

        with patch('FusionConfigurableBOM.ui.palette_controller.scan_design_snapshot', return_value=object()) as snapshot, \
             patch('FusionConfigurableBOM.ui.palette_controller.scan_design_from_snapshot', return_value=([], {})) as scan, \
             patch('FusionConfigurableBOM.ui.palette_controller.scan_design_hierarchical_from_snapshot', return_value=([], {})):
            controller.refresh(None, 'general')
            controller.refresh(None, 'structured')
            controller.refresh(None, 'general')

        # The Fusion tree is parsed once; returning to General reuses its rows.
        self.assertEqual(1, scan.call_count)
        self.assertEqual(1, snapshot.call_count)

    def test_saving_a_cell_propagates_to_every_row_sharing_a_component(self):
        # A hierarchical scan lists one definition as several nodes; a single edit
        # must update every cached row for that definition, since values are shared.
        root = FakeRoot()
        shared = FakeComponent('screw-token')
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        controller.rows = [
            ConceptBomRow('row_1', 'Screw', 2, custom_values={'manufacturer': ''}),
            ConceptBomRow('row_2', 'Screw', 3, custom_values={'manufacturer': ''}),
        ]
        controller.components = {'row_1': shared, 'row_2': shared}
        controller.send = lambda palette, payload: None

        controller.receive(None, json.dumps({
            'action': 'save_cell', 'row_id': 'row_1', 'field_id': 'manufacturer',
            'value': 'Acme', 'view_id': 'structured',
        }))

        self.assertEqual('Acme', controller.rows[0].custom_values['manufacturer'])
        self.assertEqual('Acme', controller.rows[1].custom_values['manufacturer'])

    def test_changing_the_active_view_to_hierarchical_rescans_with_the_tree_scan(self):
        # Flipping the on-screen format to hierarchical in the editor must re-scan so
        # the cached flat rows are replaced with tree nodes before state is sent;
        # otherwise the table would render flat rows under a hierarchical header.
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        controller.rows = [ConceptBomRow('row_1', 'Bracket', 1)]
        controller.components = {'row_1': object()}
        controller._rows_structure = 'flat'
        controller.send = lambda palette, payload: None
        raw_config = configuration_to_dict(default_configuration())
        for view in raw_config['views']:
            if view['view_id'] == 'general':
                view['structure'] = 'hierarchical'

        with patch('FusionConfigurableBOM.ui.palette_controller.scan_design_snapshot',
                   return_value=object()), \
             patch('FusionConfigurableBOM.ui.palette_controller.scan_design_hierarchical_from_snapshot',
                   return_value=([], {})) as hierarchical, \
             patch('FusionConfigurableBOM.ui.palette_controller.scan_design_from_snapshot') as flat:
            controller.receive(None, json.dumps({
                'action': 'save_config', 'config': raw_config, 'view_id': 'general',
            }))

        hierarchical.assert_called_once()
        flat.assert_not_called()
        self.assertEqual('hierarchical', controller._rows_structure)

    def test_editing_a_flat_view_does_not_trigger_a_rescan(self):
        # A config edit that leaves the on-screen structure alone must not pay for
        # an assembly re-scan; the cached rows still fit.
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        controller.rows = [ConceptBomRow('row_1', 'Bracket', 1)]
        controller.components = {'row_1': object()}
        controller._rows_structure = 'flat'
        controller.send = lambda palette, payload: None

        with patch('FusionConfigurableBOM.ui.palette_controller.scan_design_hierarchical') as hierarchical, \
             patch('FusionConfigurableBOM.ui.palette_controller.scan_design') as flat:
            controller.receive(None, json.dumps({
                'action': 'save_config', 'config': configuration_to_dict(default_configuration()),
                'view_id': 'general',
            }))

        hierarchical.assert_not_called()
        flat.assert_not_called()

    def test_refresh_action_scans_the_design_and_sends_rows(self):
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        scanned_rows = [ConceptBomRow('row_1', 'Bracket', 2)]
        with patch('FusionConfigurableBOM.ui.palette_controller.scan_design_snapshot',
                   return_value=object()) as snapshot, \
             patch('FusionConfigurableBOM.ui.palette_controller.scan_design_from_snapshot',
                   return_value=(scanned_rows, {'row_1': object()})) as scan_design:
            controller.receive(None, json.dumps({'action': 'refresh'}))

        scan_design.assert_called_once()
        snapshot.assert_called_once()
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
        state = next(response for response in responses if response['type'] == 'state')
        self.assertEqual(views[1].view_id, state['table']['view_id'])
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

    def test_save_design_persists_the_active_fusion_document(self):
        class Document:
            def __init__(self):
                self.descriptions = []

            def save(self, description):
                self.descriptions.append(description)
                return True

        document = Document()
        app = type('App', (), {'activeDocument': document})()
        controller = PaletteController(app)
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        controller.receive(None, json.dumps({'action': 'save_design'}))

        self.assertEqual(['Saved Configurable BOM changes.'], document.descriptions)
        self.assertEqual([{'type': 'status', 'message': 'Design saved.'}], responses)

    def test_auto_save_persists_the_document_without_manual_action(self):
        saved = []
        document = type('Document', (), {'save': lambda self, description: saved.append(description) or True})()
        app = type('App', (), {'activeDocument': document})()
        controller = PaletteController(app)
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        controller.receive(None, json.dumps({'action': 'save_design', 'auto': True}))

        self.assertEqual(['Saved Configurable BOM changes.'], saved)
        self.assertEqual([{'type': 'status', 'message': 'Design saved.'}], responses)

    def test_auto_save_is_best_effort_when_the_document_cannot_be_saved(self):
        # An unsaved/untitled document returns False from save(); auto-saves must
        # not raise, and the one-time hint must not spam on repeated edits.
        document = type('Document', (), {'save': lambda self, description: False})()
        app = type('App', (), {'activeDocument': document})()
        controller = PaletteController(app)
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        controller.receive(None, json.dumps({'action': 'save_design', 'auto': True}))
        controller.receive(None, json.dumps({'action': 'save_design', 'auto': True}))

        self.assertFalse(any(response['type'] == 'error' for response in responses))
        hints = [response for response in responses if response['type'] == 'status']
        self.assertEqual(1, len(hints))
        self.assertIn('persist', hints[0]['message'])

    def test_auto_save_ignores_a_missing_document(self):
        app = type('App', (), {'activeDocument': None})()
        controller = PaletteController(app)
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        controller.receive(None, json.dumps({'action': 'save_design', 'auto': True}))

        self.assertEqual([], responses)

    def test_manual_save_reports_when_the_document_cannot_be_saved(self):
        document = type('Document', (), {'save': lambda self, description: False})()
        app = type('App', (), {'activeDocument': document})()
        controller = PaletteController(app)
        responses = []
        controller.send = lambda palette, payload: responses.append(payload)

        controller.receive(None, json.dumps({'action': 'save_design'}))

        self.assertEqual(1, len(responses))
        self.assertEqual('error', responses[0]['type'])
        self.assertIn('could not save', responses[0]['message'])

    def test_renaming_a_custom_attribute_migrates_cached_component_values(self):
        root = object()
        app = type('App', (), {'activeProduct': type('Product', (), {'rootComponent': root})()})()
        controller = PaletteController(app)
        controller.store = FakeStore(default_configuration())
        component = object()
        controller.rows = [ConceptBomRow('row_1', 'Bracket', 1, custom_values={'manufacturer': 'Acme'})]
        controller.components = {'row_1': component}
        controller.send = lambda palette, payload: None
        raw_config = configuration_to_dict(controller.store.config)
        for field in raw_config['fields']:
            if field['field_id'] == 'manufacturer': field['field_id'] = 'maker'
        for view in raw_config['views']:
            for column in view['columns']:
                if column['source_type'] == 'attribute' and column['source_id'] == 'manufacturer':
                    column['source_id'] = 'maker'

        with patch('FusionConfigurableBOM.ui.palette_controller.rename_value') as rename_value:
            controller.receive(None, json.dumps({
                'action': 'save_config', 'config': raw_config,
                'renamed_fields': [{'old_id': 'manufacturer', 'new_id': 'maker'}],
            }))

        rename_value.assert_called_once_with(component, 'manufacturer', 'maker')
        self.assertEqual({'maker': 'Acme'}, controller.rows[0].custom_values)
        self.assertIn('maker', [field.field_id for field in controller.store.config.fields])
