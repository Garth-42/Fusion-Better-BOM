ADDIN_NAME = 'Fusion Configurable BOM'
COMMAND_ID = 'fusion_configurable_bom_open'
COMMAND_NAME = 'Open Configurable BOM'
COMMAND_DESCRIPTION = 'Open the configurable BOM palette.'
PALETTE_ID = 'fusion_configurable_bom_palette'
# Everything the add-in stores in a design lives in attribute groups under this
# namespace. Changing it again would orphan saved data unless the old value is
# added to the fallback chain the way LEGACY_NAMESPACE is (see
# fusion/attribute_groups.py). It also matches the manifest "id".
NAMESPACE = 'com.fusion_configurable_bom'
# The template placeholder used by earlier builds; still read, never written.
LEGACY_NAMESPACE = 'com.company.fusion_configurable_bom'
FIELD_ATTRIBUTE_GROUP = NAMESPACE + '.fields'
LEGACY_FIELD_ATTRIBUTE_GROUP = LEGACY_NAMESPACE + '.fields'
CONFIG_ATTRIBUTE_GROUP = NAMESPACE
LEGACY_CONFIG_ATTRIBUTE_GROUP = LEGACY_NAMESPACE
CONFIG_ATTRIBUTE_NAME = 'configuration'
# BOM cell values live in one JSON map on the active design's root component so
# they are saved with the design the user actually saves, even when a part is a
# component referenced from another file (whose own document is not saved here).
VALUE_ATTRIBUTE_GROUP = NAMESPACE + '.values'
LEGACY_VALUE_ATTRIBUTE_GROUP = LEGACY_NAMESPACE + '.values'
VALUE_ATTRIBUTE_NAME = 'component_values'
