import json, re, uuid
from ..constants import CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME
from ..domain.models import BomConfiguration, BomTableFormat, ColumnDefinition, CustomFieldDefinition, configuration_to_dict

SCHEMA_VERSION = 3
STRUCTURES = ('flat', 'hierarchical')
ROLLUP_BY = ('component', 'part_number', 'subassembly')
_FIELD_RE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')

class ConfigurationError(ValueError): pass

def default_configuration():
    fields = [CustomFieldDefinition('manufacturer', 'Manufacturer'), CustomFieldDefinition('manufacturer_part_number', 'Manufacturer Part Number'), CustomFieldDefinition('supplier', 'Supplier'), CustomFieldDefinition('supplier_part_number', 'Supplier Part Number')]
    builtin = lambda key, header, width=None: ColumnDefinition('builtin', key, header, width=width)
    attribute = lambda key, header: ColumnDefinition('attribute', key, header)
    return BomConfiguration(SCHEMA_VERSION, fields, [
        BomTableFormat('general', 'General BOM', [builtin('quantity','Qty',70), builtin('component_name','Component',220), builtin('fusion_part_number','Part Number',160), builtin('fusion_description','Description',220)]),
        BomTableFormat('part_number_rollup', 'Part Number Roll-up', [builtin('quantity','Qty',70), builtin('fusion_part_number','Part Number',160), builtin('component_name','Component',220), builtin('fusion_description','Description',220)], 'flat', 'part_number'),
        BomTableFormat('subassembly_rollup', 'Subassembly Roll-up', [builtin('quantity','Qty',70), builtin('parent_assembly','Subassembly',180), builtin('component_name','Component',220), builtin('fusion_part_number','Part Number',160)], 'flat', 'subassembly'),
        BomTableFormat('purchasing_demo', 'Purchasing Demo', [builtin('quantity','Qty',70), builtin('component_name','Component',220), attribute('manufacturer','Manufacturer'), attribute('manufacturer_part_number','Manufacturer Part Number'), attribute('supplier','Supplier'), attribute('supplier_part_number','Supplier Part Number')]),
        BomTableFormat('structured', 'Structured BOM', [builtin('quantity','Qty',70), builtin('total_quantity','Total Qty',80), builtin('component_name','Component',260), builtin('fusion_part_number','Part Number',160), builtin('fusion_description','Description',220)], 'hierarchical')])

def _ensure_default_views(config):
    # Add any built-in view the config is missing, matched by view_id, without
    # touching the user's own views or their customizations. Default views are
    # protected from deletion, so a design should always be able to reach every
    # one -- including views added in a later release, like the hierarchical
    # "Structured BOM". A design configured before such a view shipped never gains
    # it otherwise: _migrate only bumps the schema version and never introduces
    # new views, so the format simply would not appear in the picker.
    existing = {view.view_id for view in config.views}
    for view in default_configuration().views:
        if view.view_id not in existing:
            config.views.append(view)
    # A few early configurations stored the default General BOM with no
    # columns. It is not a usable table format, so restore the shipped preset
    # while leaving any non-empty user layout untouched.
    general = next((view for view in config.views if view.view_id == 'general'), None)
    if general is not None and not general.columns:
        default_general = next(view for view in default_configuration().views if view.view_id == 'general')
        general.name = default_general.name
        general.columns = default_general.columns
        general.structure = default_general.structure
        general.rollup_by = default_general.rollup_by
    return config

def validate(config):
    if config.schema_version != SCHEMA_VERSION: raise ConfigurationError('Unsupported configuration schema version.')
    field_ids = [f.field_id for f in config.fields]
    if len(field_ids) != len(set(field_ids)) or any(not _FIELD_RE.match(i) for i in field_ids): raise ConfigurationError('Field IDs must be unique lowercase identifiers.')
    view_ids = [v.view_id for v in config.views]
    if len(view_ids) != len(set(view_ids)) or not view_ids: raise ConfigurationError('At least one uniquely identified view is required.')
    if any(v.structure not in STRUCTURES for v in config.views): raise ConfigurationError('View structure must be flat or hierarchical.')
    if any(v.rollup_by not in ROLLUP_BY for v in config.views): raise ConfigurationError('Roll-up must be by component, part number, or subassembly.')
    return config

def _migrate(raw):
    version = raw.get('schema_version')
    if version == SCHEMA_VERSION: return raw
    # v1 predates structure and v2 predates the configurable flat roll-up.
    # from_dict supplies safe defaults for both fields, preserving every saved
    # column and value while upgrading the document.
    if version in (1, 2): return {**raw, 'schema_version': SCHEMA_VERSION}
    raise ConfigurationError('Unsupported configuration schema version.')

def from_dict(raw):
    raw = _migrate(raw)
    try:
        config = BomConfiguration(raw['schema_version'], [CustomFieldDefinition(**f) for f in raw.get('fields',[])], [BomTableFormat(v['view_id'], v['name'], [ColumnDefinition(**c) for c in v.get('columns',[])], v.get('structure', 'flat'), v.get('rollup_by', 'component')) for v in raw.get('views',[])])
    except (KeyError, TypeError) as exc: raise ConfigurationError('Invalid configuration structure.') from exc
    return validate(config)

def loads(value): return from_dict(json.loads(value))
def dumps(config): return json.dumps(configuration_to_dict(validate(config)), separators=(',', ':'), sort_keys=True)
def new_id(prefix): return f'{prefix}_{uuid.uuid4().hex[:8]}'

class FusionConfigurationStore:
    def load(self, root):
        attribute = root.attributes.itemByName(CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME)
        config = default_configuration() if not attribute else loads(attribute.value)
        return _ensure_default_views(config)
    def save(self, root, config):
        value = dumps(config)
        attribute = root.attributes.itemByName(CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME)
        if attribute:
            attribute.value = value
        else:
            root.attributes.add(CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME, value)
