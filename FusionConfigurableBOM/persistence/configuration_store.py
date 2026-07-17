import json, re, uuid
from ..constants import CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME
from ..domain.models import BomConfiguration, BomTableFormat, ColumnDefinition, CustomFieldDefinition, configuration_to_dict

SCHEMA_VERSION = 1
_FIELD_RE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')

class ConfigurationError(ValueError): pass

def default_configuration():
    fields = [CustomFieldDefinition('manufacturer', 'Manufacturer'), CustomFieldDefinition('manufacturer_part_number', 'Manufacturer Part Number'), CustomFieldDefinition('supplier', 'Supplier'), CustomFieldDefinition('supplier_part_number', 'Supplier Part Number')]
    builtin = lambda key, header, width=None: ColumnDefinition('builtin', key, header, width=width)
    attribute = lambda key, header: ColumnDefinition('attribute', key, header)
    return BomConfiguration(SCHEMA_VERSION, fields, [
        BomTableFormat('general', 'General BOM', [builtin('quantity','Qty',70), builtin('component_name','Component',220), builtin('fusion_part_number','Part Number',160), builtin('fusion_description','Description',220)]),
        BomTableFormat('purchasing_demo', 'Purchasing Demo', [builtin('quantity','Qty',70), builtin('component_name','Component',220), attribute('manufacturer','Manufacturer'), attribute('manufacturer_part_number','Manufacturer Part Number'), attribute('supplier','Supplier'), attribute('supplier_part_number','Supplier Part Number')])])

def validate(config):
    if config.schema_version != SCHEMA_VERSION: raise ConfigurationError('Unsupported configuration schema version.')
    field_ids = [f.field_id for f in config.fields]
    if len(field_ids) != len(set(field_ids)) or any(not _FIELD_RE.match(i) for i in field_ids): raise ConfigurationError('Field IDs must be unique lowercase identifiers.')
    view_ids = [v.view_id for v in config.views]
    if len(view_ids) != len(set(view_ids)) or not view_ids: raise ConfigurationError('At least one uniquely identified view is required.')
    return config

def from_dict(raw):
    try:
        config = BomConfiguration(raw['schema_version'], [CustomFieldDefinition(**f) for f in raw.get('fields',[])], [BomTableFormat(v['view_id'], v['name'], [ColumnDefinition(**c) for c in v.get('columns',[])]) for v in raw.get('views',[])])
    except (KeyError, TypeError) as exc: raise ConfigurationError('Invalid configuration structure.') from exc
    return validate(config)

def loads(value): return from_dict(json.loads(value))
def dumps(config): return json.dumps(configuration_to_dict(validate(config)), separators=(',', ':'), sort_keys=True)
def new_id(prefix): return f'{prefix}_{uuid.uuid4().hex[:8]}'

class FusionConfigurationStore:
    def load(self, root):
        attribute = root.attributes.itemByName(CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME)
        return default_configuration() if not attribute else loads(attribute.value)
    def save(self, root, config):
        value = dumps(config)
        attribute = root.attributes.itemByName(CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME)
        if attribute:
            attribute.value = value
        else:
            root.attributes.add(CONFIG_ATTRIBUTE_GROUP, CONFIG_ATTRIBUTE_NAME, value)
