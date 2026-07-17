import json, os
from ..constants import PALETTE_ID
from ..domain.table_builder import build_table
from ..persistence.configuration_store import FusionConfigurationStore, new_id
from ..domain.models import CustomFieldDefinition, ColumnDefinition, BomTableFormat
from ..fusion.assembly_scanner import scan_design
from ..fusion.attribute_store import write_value, rename_value
from .clipboard import copy_text

class PaletteController:
    def __init__(self, app): self.app, self.store, self.rows, self.components = app, FusionConfigurationStore(), [], {}
    def show(self):
        import adsk.core
        path = os.path.join(os.path.dirname(__file__), 'web', 'index.html')
        palette = self.app.userInterface.palettes.itemById(PALETTE_ID)
        if not palette:
            palette = self.app.userInterface.palettes.add(PALETTE_ID, 'Configurable BOM', 'file:///' + path.replace('\\','/'), True, True, True, 900, 600)
            # A floating palette is a separate Fusion window, so it opens above
            # the Browser/feature tree instead of being obscured by that panel.
            palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateFloating
        palette.isVisible = True
        return palette
    def refresh(self, palette):
        design = self.app.activeProduct
        if not getattr(design, 'rootComponent', None): return self.send(palette, {'type':'error','message':'Open a Fusion design to scan its assembly.'})
        try:
            config = self.store.load(design.rootComponent)
            # allOccurrences is a Fusion API traversal and can be expensive on large designs.
            # Only do it for an explicit Refresh; edit operations render from this cache.
            self.rows, self.components = scan_design(design, [f.field_id for f in config.fields])
            self._send_state(palette, config)
        except Exception as exc: self.send(palette, {'type':'error','message':str(exc)})
    def receive(self, palette, raw):
        try:
            message = json.loads(raw); action = message['action']
            if action == 'refresh': return self.refresh(palette)
            if action == 'copy_table':
                try:
                    copy_text(message['tsv'])
                except Exception as exc:
                    return self.send(palette, {'type': 'copy_result', 'copied': False, 'message': str(exc)})
                return self.send(palette, {'type': 'copy_result', 'copied': True, 'row_count': message['row_count']})
            design = self.app.activeProduct; config = self.store.load(design.rootComponent)
            if action == 'save_cell':
                component = self.components[message['row_id']]
                if getattr(component, 'isReferencedComponent', False): raise ValueError('Linked components are read-only; open the source design to edit.')
                value = message.get('value', '')
                write_value(component, message['field_id'], value)
                next(row for row in self.rows if row.row_id == message['row_id']).custom_values[message['field_id']] = value
            elif action == 'save_config':
                self._apply_config(config, message['config'], message.get('renamed_fields', [])); self.store.save(design.rootComponent, config)
            elif action == 'save_as_view':
                self._apply_config(config, message['config'], message.get('renamed_fields', []))
                source = next(v for v in config.views if v.view_id == message['view_id'])
                config.views.append(BomTableFormat(new_id('view'), message['name'], list(source.columns)))
                self.store.save(design.rootComponent, config)
            elif action == 'new_field':
                field_id = message['field_id']; config.fields.append(CustomFieldDefinition(field_id, message['label']))
                for row in self.rows: row.custom_values[field_id] = ''
                next(v for v in config.views if v.view_id == message.get('view_id', config.views[0].view_id)).columns.append(ColumnDefinition('attribute', field_id, message['label'])); self.store.save(design.rootComponent, config)
            elif action == 'add_column':
                view = next(v for v in config.views if v.view_id == message['view_id'])
                field = next(f for f in config.fields if f.field_id == message['field_id'])
                if not any(c.source_type == 'attribute' and c.source_id == field.field_id for c in view.columns): view.columns.append(ColumnDefinition('attribute', field.field_id, field.default_label))
                self.store.save(design.rootComponent, config)
            elif action == 'duplicate_view':
                source = next(v for v in config.views if v.view_id == message['view_id']); config.views.append(BomTableFormat(new_id('view'), message.get('name', source.name + ' Copy'), list(source.columns))); self.store.save(design.rootComponent, config)
            elif action == 'delete_view':
                if len(config.views) <= 1 or message['view_id'] in ('general', 'purchasing_demo'): raise ValueError('Default formats cannot be deleted.')
                config.views[:] = [v for v in config.views if v.view_id != message['view_id']]; self.store.save(design.rootComponent, config)
            self._send_state(palette, config, message.get('view_id'))
            self.send(palette, {'type':'status','message':'Saved.'})
        except Exception as exc: self.send(palette, {'type':'error','message':str(exc)})
    def _apply_config(self, config, raw, renamed_fields=()):
        from ..persistence.configuration_store import from_dict
        parsed = from_dict(raw)
        old_field_ids = {field.field_id for field in config.fields}
        new_field_ids = {field.field_id for field in parsed.fields}
        for rename in renamed_fields:
            old_id, new_id = rename['old_id'], rename['new_id']
            if old_id not in old_field_ids or new_id not in new_field_ids:
                raise ValueError('Invalid custom attribute rename.')
            if old_id == new_id:
                continue
            for row in self.rows:
                row.custom_values[new_id] = row.custom_values.pop(old_id, '')
                component = self.components.get(row.row_id)
                if component and not row.linked:
                    rename_value(component, old_id, new_id)
        config.fields, config.views = parsed.fields, parsed.views
    def _config(self, config):
        from ..domain.models import configuration_to_dict
        return configuration_to_dict(config)
    def _send_state(self, palette, config, view_id=None):
        view = next((item for item in config.views if item.view_id == view_id), config.views[0])
        self.send(palette, {'type':'state','config': self._config(config), 'table': build_table(self.rows, view)})
    def send(self, palette, payload): palette.sendInfoToHTML('fusionBomMessage', json.dumps(payload))
