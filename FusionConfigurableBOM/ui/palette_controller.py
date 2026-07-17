import json, os
from ..constants import PALETTE_ID
from ..domain.table_builder import build_table
from ..persistence.configuration_store import FusionConfigurationStore, new_id
from ..domain.models import CustomFieldDefinition, ColumnDefinition, BomTableFormat
from ..fusion.assembly_scanner import scan_design, scan_design_hierarchical
from ..fusion.attribute_store import write_value, rename_value
from ..fusion.value_store import write_value as write_root_value, rename_field as rename_root_field
from .clipboard import copy_text

def _same_component(a, b):
    # Two occurrences of one definition share a persistent entityToken even when
    # Fusion hands back different Python proxies; fall back to identity for the
    # test doubles that omit a token.
    if a is None or b is None:
        return a is b
    token_a, token_b = getattr(a, 'entityToken', None), getattr(b, 'entityToken', None)
    if token_a or token_b:
        return token_a == token_b
    return a is b

class PaletteController:
    def __init__(self, app): self.app, self.store, self.rows, self.components, self._auto_save_hinted, self._on_palette_created = app, FusionConfigurationStore(), [], {}, False, None
    def on_palette_created(self, hook):
        # install() registers the HTML message wiring here so it runs whenever the
        # palette is (re)built inside show(), not once at add-in load.
        self._on_palette_created = hook
    def show(self):
        import adsk.core
        ui = self.app.userInterface
        palette = ui.palettes.itemById(PALETTE_ID)
        # Fusion discards palettes when the user switches workspaces; a stale
        # handle reports isValid == False and has to be rebuilt from scratch.
        if palette and not getattr(palette, 'isValid', True):
            palette = None
        if not palette:
            path = os.path.join(os.path.dirname(__file__), 'web', 'index.html')
            # Create the palette on demand -- the first time the user opens the BOM
            # -- rather than eagerly at add-in load. That is what makes its first
            # appearance a fresh floating window stacked above the Browser and
            # object tree; a palette built at load parks behind those panels, and
            # the API exposes no raise/z-order call to lift it back out.
            #
            # Create it visible (not hidden-then-shown) and with Fusion's default
            # web browser: some Fusion builds defer rendering a palette created
            # hidden, so showing it a moment later paints blank, and forcing the
            # newer browser can leave the HTML unrendered. Both must match the
            # original working call so the toolbar and table draw on first open.
            palette = ui.palettes.add(PALETTE_ID, 'Configurable BOM', 'file:///' + path.replace('\\', '/'), True, True, True, 900, 600)
            palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateFloating
            if self._on_palette_created:
                self._on_palette_created(palette)
        elif palette.isVisible:
            # Re-opening a palette that is already up but buried behind the tree or
            # the collapsed Comments/Browser panels: hiding it first, then showing
            # it again below, re-stacks the floating window back on top.
            palette.isVisible = False
        palette.isVisible = True
        return palette
    def refresh(self, palette, view_id=None):
        design = self.app.activeProduct
        if not getattr(design, 'rootComponent', None): return self.send(palette, {'type':'error','message':'Open a Fusion design to scan its assembly.'})
        try:
            config = self.store.load(design.rootComponent)
            view = self._view(config, view_id)
            # allOccurrences is a Fusion API traversal and can be expensive on large designs.
            # Only do it for an explicit Refresh; edit operations render from this cache.
            # The active view's structure picks a flat leaf scan or a structured tree walk.
            self.rows, self.components = self._scan(design, config, view)
            self._send_state(palette, config, view.view_id)
        except Exception as exc: self.send(palette, {'type':'error','message':str(exc)})
    def _view(self, config, view_id):
        return next((view for view in config.views if view.view_id == view_id), config.views[0])
    def _scan(self, design, config, view):
        field_ids = [f.field_id for f in config.fields]
        if getattr(view, 'structure', 'flat') == 'hierarchical':
            return scan_design_hierarchical(design, field_ids)
        return scan_design(design, field_ids)
    def receive(self, palette, raw):
        try:
            message = json.loads(raw); action = message['action']
            if action == 'refresh': return self.refresh(palette, message.get('view_id'))
            if action == 'save_design': return self._save_design(palette, auto=bool(message.get('auto')))
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
                # Authoritative store on the active design's root so the value is
                # saved with the design; the component write keeps legacy data in
                # sync but does not persist for parts that live in another file.
                write_root_value(design.rootComponent, component, message['field_id'], value)
                try:
                    write_value(component, message['field_id'], value)
                except Exception:
                    pass  # Best-effort legacy mirror; the root store above is authoritative.
                # A hierarchical scan can list one component definition as several
                # nodes; values are shared by definition, so update every cached
                # row that resolves to the same component (a flat scan matches one).
                for row in self.rows:
                    if _same_component(self.components.get(row.row_id), component):
                        row.custom_values[message['field_id']] = value
            elif action == 'save_config':
                self._apply_config(config, message['config'], message.get('renamed_fields', [])); self.store.save(design.rootComponent, config)
            elif action == 'save_as_view':
                self._apply_config(config, message['config'], message.get('renamed_fields', []))
                source = next(v for v in config.views if v.view_id == message['view_id'])
                config.views.append(BomTableFormat(new_id('view'), message['name'], list(source.columns), source.structure))
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
                source = next(v for v in config.views if v.view_id == message['view_id']); config.views.append(BomTableFormat(new_id('view'), message.get('name', source.name + ' Copy'), list(source.columns), source.structure)); self.store.save(design.rootComponent, config)
            elif action == 'delete_view':
                if len(config.views) <= 1 or message['view_id'] in ('general', 'purchasing_demo', 'structured'): raise ValueError('Default formats cannot be deleted.')
                config.views[:] = [v for v in config.views if v.view_id != message['view_id']]; self.store.save(design.rootComponent, config)
            # A cell save originates from the live input element. Returning a full
            # state redraw for every keystroke would replace that element, steal
            # focus, and prevent the remaining value from being saved.
            if action != 'save_cell':
                self._send_state(palette, config, message.get('view_id'))
            self.send(palette, {'type':'status','message':'Saved.'})
        except Exception as exc: self.send(palette, {'type':'error','message':str(exc)})
    def _save_design(self, palette, auto=False):
        # Fusion attributes only reach disk when the document is saved, and adding
        # an attribute does not mark the document modified, so Fusion never prompts
        # on close. Persisting here is what actually survives a close/reopen.
        document = getattr(self.app, 'activeDocument', None)
        if not document:
            if auto:
                return
            raise ValueError('Open a Fusion design before saving BOM changes.')
        try:
            saved = document.save('Saved Configurable BOM changes.')
        except Exception:
            # Auto-saves are best-effort; the manual Save design button surfaces errors.
            if auto:
                return
            raise
        if not saved:
            hint = 'Save the design in Fusion once (File ▸ Save) so BOM edits can persist.'
            if not auto:
                raise RuntimeError('Fusion could not save the active design. ' + hint)
            # An unsaved/untitled document cannot be saved from here; hint once so
            # repeated auto-saves do not spam the status line.
            if not self._auto_save_hinted:
                self._auto_save_hinted = True
                self.send(palette, {'type': 'status', 'message': hint})
            return
        self._auto_save_hinted = False
        self.send(palette, {'type': 'status', 'message': 'Design saved.'})
    def _apply_config(self, config, raw, renamed_fields=()):
        from ..persistence.configuration_store import from_dict
        parsed = from_dict(raw)
        root = getattr(self.app.activeProduct, 'rootComponent', None)
        old_field_ids = {field.field_id for field in config.fields}
        new_field_ids = {field.field_id for field in parsed.fields}
        for rename in renamed_fields:
            old_id, new_id = rename['old_id'], rename['new_id']
            if old_id not in old_field_ids or new_id not in new_field_ids:
                raise ValueError('Invalid custom attribute rename.')
            if old_id == new_id:
                continue
            # Migrate the authoritative root-stored values, then the legacy
            # per-component values, so a renamed column keeps its data.
            if root is not None:
                rename_root_field(root, old_id, new_id)
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
