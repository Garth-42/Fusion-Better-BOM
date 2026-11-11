import json
import os

from ..constants import PALETTE_ID
from ..domain.models import BomTableFormat, ColumnDefinition, CustomFieldDefinition, configuration_to_dict
from ..domain.table_builder import build_table
from ..fusion.assembly_scanner import (
    scan_design_from_snapshot,
    scan_design_hierarchical_from_snapshot,
    scan_design_snapshot,
)
from ..fusion.attribute_store import rename_value, write_value
from ..fusion.identity import component_key
from ..fusion.value_store import rename_field as rename_root_field
from ..fusion.value_store import write_values as write_root_values
from ..persistence.configuration_store import (
    DEFAULT_VIEW_IDS,
    FIELD_ID_RULE,
    FusionConfigurationStore,
    from_dict,
    is_valid_field_id,
    new_id,
)
from .clipboard import copy_text

NO_DESIGN_MESSAGE = 'Open a Fusion design to scan its assembly.'
STALE_MESSAGE = 'The table is out of date. Click Refresh and try again.'


class PaletteController:
    def __init__(self, app):
        self.app = app
        self.store = FusionConfigurationStore()
        self.rows = []
        # row_id -> the (first) Fusion component behind that row.
        self.components = {}
        self._auto_save_hinted = False
        self._on_palette_created = None
        self._rows_structure = 'flat'
        self._rows_rollup = 'component'
        # Identity of the design root the current rows were scanned from.
        self._scanned_root = None
        self._scan_cache = {}
        self._snapshot = None
        self._snapshot_key = None

    # ----- palette window -------------------------------------------------

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
            url = 'file:///' + path.replace('\\', '/')
            palette = ui.palettes.add(PALETTE_ID, 'Configurable BOM', url, True, True, True, 900, 600)
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

    def document_activated(self):
        # The user switched to another document tab. The rows on screen belong to
        # the previous design, so ask the page to re-scan (it knows which format
        # is selected). Edits against the old rows are refused in receive().
        palette = self.app.userInterface.palettes.itemById(PALETTE_ID)
        if palette and getattr(palette, 'isValid', True) and palette.isVisible:
            self.send(palette, {'type': 'document_changed'})

    def send(self, palette, payload):
        palette.sendInfoToHTML('fusionBomMessage', json.dumps(payload))

    # ----- scanning -------------------------------------------------------

    def _design(self):
        product = getattr(self.app, 'activeProduct', None)
        if getattr(product, 'rootComponent', None):
            return product
        # In a non-design workspace (e.g. Manufacture) activeProduct is not the
        # Design, but the document still has one.
        products = getattr(getattr(self.app, 'activeDocument', None), 'products', None)
        if products:
            try:
                design = products.itemByProductType('DesignProductType')
            except Exception:
                design = None
            if getattr(design, 'rootComponent', None):
                return design
        raise ValueError(NO_DESIGN_MESSAGE)

    def _root_identity(self, design):
        # Fusion hands back a brand-new Python proxy on every `rootComponent`
        # access, so id() of that proxy can never key a cache or tell two
        # designs apart; component_key uses the persistent ID instead.
        return component_key(design.rootComponent)

    def refresh(self, palette, view_id=None, force=False):
        try:
            design = self._design()
            config = self.store.load(design.rootComponent)
            view = self._view(config, view_id)
            if force:
                # A user-requested Refresh is the explicit freshness boundary.
                # Format switches reuse the parsed snapshot, avoiding repeat
                # Fusion occurrence-tree walks while the design is unchanged.
                self._invalidate_snapshot()
            self._load_rows(design, config, view)
            self._send_state(palette, config, view.view_id)
        except Exception as exc:
            self._send_error(palette, exc)

    def _view(self, config, view_id):
        """The requested view, or the first one when it is missing/unspecified."""
        return next((view for view in config.views if view.view_id == view_id), config.views[0])

    def _invalidate_snapshot(self):
        self._scan_cache.clear()
        self._snapshot, self._snapshot_key = None, None

    def _load_rows(self, design, config, view):
        self.rows, self.components = self._scan_cached(design, config, view)
        self._rows_structure, self._rows_rollup = view.structure, view.rollup_by
        self._scanned_root = self._root_identity(design)

    def _scan_cached(self, design, config, view):
        # The snapshot holds everything read from Fusion and is independent of
        # table columns, so every format is aggregated from it without another
        # walk. It is rebuilt on explicit Refresh, a different design, or a
        # changed field set; cell edits patch it in place.
        root_identity = self._root_identity(design)
        field_ids = tuple(field.field_id for field in config.fields)
        snapshot_key = (root_identity, field_ids)
        if self._snapshot_key != snapshot_key:
            self._snapshot = scan_design_snapshot(design, list(field_ids))
            self._snapshot_key = snapshot_key
            self._scan_cache.clear()
        key = (view.structure, view.rollup_by if view.structure == 'flat' else None)
        if key not in self._scan_cache:
            if view.structure == 'hierarchical':
                self._scan_cache[key] = scan_design_hierarchical_from_snapshot(self._snapshot)
            else:
                self._scan_cache[key] = scan_design_from_snapshot(self._snapshot, view.rollup_by)
        return self._scan_cache[key]

    def _resync_rows_structure(self, design, config, view):
        # The format editor can flip a view between flat and hierarchical (or
        # change its roll-up). When the view now on screen was scanned in another
        # shape the cached rows no longer fit, so re-aggregate before sending
        # state -- otherwise a newly hierarchical view would render flat rows.
        if view.structure == self._rows_structure and (
            view.structure == 'hierarchical' or view.rollup_by == self._rows_rollup
        ):
            return
        self._load_rows(design, config, view)

    def _send_state(self, palette, config, view_id=None):
        view = self._view(config, view_id)
        self.send(
            palette,
            {'type': 'state', 'config': configuration_to_dict(config), 'table': build_table(self.rows, view)},
        )

    def _send_error(self, palette, exc):
        # Some exceptions (StopIteration, KeyError) have empty or cryptic text.
        if isinstance(exc, KeyError):
            text = f'The request was missing {exc}.'
        else:
            text = str(exc) or type(exc).__name__
        self.send(palette, {'type': 'error', 'message': text})

    # ----- messages from the page ----------------------------------------

    def receive(self, palette, raw):
        try:
            message = json.loads(raw)
            action = message['action']
            if action == 'refresh':
                return self.refresh(palette, message.get('view_id'), bool(message.get('force')))
            if action == 'save_design':
                return self._save_design(palette, auto=bool(message.get('auto')))
            if action == 'copy_table':
                return self._copy_table(palette, message)

            design = self._design()
            # Everything below edits data using what the page last saw. If the
            # user has since switched documents, that would write one design's
            # rows/configuration into another.
            if self._scanned_root is not None and self._scanned_root != self._root_identity(design):
                raise ValueError(
                    'The active design changed since this table was scanned. Click Refresh and try again.'
                )
            if action == 'save_cell':
                # A cell save originates from the live input element. Returning a
                # full state redraw would replace that element and steal focus.
                self._save_cell(design, message)
            else:
                handler = self._CONFIG_ACTIONS.get(action)
                if handler is None:
                    raise ValueError(f'Unknown action: {action}')
                root = design.rootComponent
                config = self.store.load(root)
                active_view_id = handler(self, config, message) or message.get('view_id')
                self.store.save(root, config)
                # No snapshot invalidation needed: it is keyed on the field set,
                # so a new or renamed field forces a re-scan on its own.
                view = self._view(config, active_view_id)
                self._resync_rows_structure(design, config, view)
                self._send_state(palette, config, view.view_id)
            self.send(palette, {'type': 'status', 'message': 'Updated.'})
        except Exception as exc:
            self._send_error(palette, exc)

    def _copy_table(self, palette, message):
        try:
            copy_text(message['tsv'])
        except Exception as exc:
            return self.send(palette, {'type': 'copy_result', 'copied': False, 'message': str(exc)})
        return self.send(palette, {'type': 'copy_result', 'copied': True, 'row_count': message['row_count']})

    def _save_cell(self, design, message):
        row_id, field_id, value = message['row_id'], message['field_id'], message.get('value', '')
        if row_id not in self.components:
            raise ValueError(STALE_MESSAGE)
        row = next((item for item in self.rows if item.row_id == row_id), None)
        # A part-number roll-up row can stand for several component definitions;
        # the edit applies to all of them so the row does not split on refresh.
        members = [member for member in getattr(row, 'members', []) if not member.linked]
        targets = [member.component for member in members]
        if not getattr(row, 'members', []):
            component = self.components[row_id]
            if not getattr(component, 'isReferencedComponent', False):
                targets = [component]
        if not targets:
            raise ValueError('Linked components are read-only; open the source design to edit.')
        # Authoritative store on the active design's root so the value is saved
        # with the design; the component write keeps legacy data in sync but
        # does not persist for parts that live in another file.
        write_root_values(design.rootComponent, targets, field_id, value)
        for component in targets:
            try:
                write_value(component, field_id, value)
            except Exception:
                pass  # Best-effort legacy mirror; the root store is authoritative.
        # Keep the parsed snapshot current so later format switches need no
        # Fusion walk, and drop the aggregated rows derived from the old values.
        for member in members:
            member.custom_values[field_id] = value
        self._scan_cache.clear()
        # A hierarchical scan lists one definition as several nodes; values are
        # shared by definition, so update every row on screen that resolves to
        # an edited component.
        target_keys = {component_key(component) for component in targets}
        for item in self.rows:
            keys = {member.key for member in getattr(item, 'members', [])}
            if item.row_id in self.components:
                keys.add(component_key(self.components[item.row_id]))
            if keys & target_keys:
                item.custom_values[field_id] = value

    def _find_view(self, config, view_id):
        view = next((item for item in config.views if item.view_id == view_id), None)
        if view is None:
            raise ValueError('That table format no longer exists. ' + STALE_MESSAGE)
        return view

    def _action_save_config(self, config, message):
        self._apply_config(config, message['config'], message.get('renamed_fields', []))

    def _action_save_as_view(self, config, message):
        self._apply_config(config, message['config'], message.get('renamed_fields', []))
        source = self._find_view(config, message['view_id'])
        name = str(message['name']).strip()
        if not name:
            raise ValueError('Enter a name for the new table format.')
        saved = BomTableFormat(new_id('view'), name, list(source.columns), source.structure, source.rollup_by)
        config.views.append(saved)
        # Select the newly created format so Save as visibly did something.
        return saved.view_id

    def _action_new_field(self, config, message):
        field_id, label = message['field_id'], str(message['label']).strip()
        if not is_valid_field_id(field_id):
            raise ValueError(FIELD_ID_RULE)
        if any(field.field_id == field_id for field in config.fields):
            raise ValueError(f'A custom field with the key "{field_id}" already exists.')
        if not label:
            raise ValueError('Enter a name for the custom field.')
        view = self._find_view(config, message.get('view_id', config.views[0].view_id))
        config.fields.append(CustomFieldDefinition(field_id, label))
        view.columns.append(ColumnDefinition('attribute', field_id, label))
        for row in self.rows:
            row.custom_values[field_id] = ''

    def _action_add_column(self, config, message):
        view = self._find_view(config, message['view_id'])
        field = next((item for item in config.fields if item.field_id == message['field_id']), None)
        if field is None:
            raise ValueError('That custom field no longer exists. ' + STALE_MESSAGE)
        if any(c.source_type == 'attribute' and c.source_id == field.field_id for c in view.columns):
            raise ValueError(f'"{field.default_label}" is already a column in this format.')
        view.columns.append(ColumnDefinition('attribute', field.field_id, field.default_label))

    def _action_delete_view(self, config, message):
        view = self._find_view(config, message['view_id'])
        if len(config.views) <= 1 or view.view_id in DEFAULT_VIEW_IDS:
            raise ValueError('Default formats cannot be deleted.')
        config.views.remove(view)

    _CONFIG_ACTIONS = {
        'save_config': _action_save_config,
        'save_as_view': _action_save_as_view,
        'new_field': _action_new_field,
        'add_column': _action_add_column,
        'delete_view': _action_delete_view,
    }

    def _apply_config(self, config, raw, renamed_fields=()):
        parsed = from_dict(raw)
        root = getattr(self._design(), 'rootComponent', None)
        old_field_ids = {field.field_id for field in config.fields}
        new_field_ids = {field.field_id for field in parsed.fields}
        for rename in renamed_fields:
            old_field_id, new_field_id = rename['old_id'], rename['new_id']
            if old_field_id not in old_field_ids or new_field_id not in new_field_ids:
                raise ValueError('Invalid custom attribute rename.')
            if old_field_id == new_field_id:
                continue
            # Migrate the authoritative root-stored values, then the legacy
            # per-component values, so a renamed column keeps its data.
            if root is not None:
                rename_root_field(root, old_field_id, new_field_id)
            for row in self.rows:
                row.custom_values[new_field_id] = row.custom_values.pop(old_field_id, '')
                component = self.components.get(row.row_id)
                if component and not row.linked:
                    try:
                        rename_value(component, old_field_id, new_field_id)
                    except Exception:
                        pass  # Best-effort legacy mirror; the root store is authoritative.
        config.fields, config.views = parsed.fields, parsed.views

    # ----- saving the Fusion document -------------------------------------

    def _save_design(self, palette, auto=False):
        # Fusion attributes only reach disk when the document is saved, and adding
        # an attribute does not mark the document modified, so Fusion never prompts
        # on close. Persisting here is what actually survives a close/reopen.
        # `auto` is only sent when the user has switched on Auto-save in the
        # palette, because every save creates a new version of the design.
        try:
            document = getattr(self.app, 'activeDocument', None)
            if not document:
                if auto:
                    return
                raise ValueError('Open a Fusion design before saving BOM changes.')
            try:
                saved = document.save('Saved Configurable BOM changes.')
            except Exception:
                # Auto-saves are best-effort; the Save design button surfaces errors.
                if auto:
                    return
                raise
            if not saved:
                hint = 'Save the design in Fusion once (File ▸ Save) so BOM edits can persist.'
                if not auto:
                    raise RuntimeError('Fusion could not save the active design. ' + hint)
                # An unsaved/untitled document cannot be saved from here; hint once
                # so repeated auto-saves do not spam the status line.
                if not self._auto_save_hinted:
                    self._auto_save_hinted = True
                    self.send(palette, {'type': 'status', 'message': hint})
                return
            self._auto_save_hinted = False
            self.send(palette, {'type': 'status', 'message': 'Design saved.', 'design_saved': True})
        except Exception as exc:
            self._send_error(palette, exc)
