ADDIN_NAME = 'Fusion Configurable BOM'
COMMAND_ID = 'fusion_configurable_bom_open'
COMMAND_NAME = 'Open Configurable BOM'
COMMAND_DESCRIPTION = 'Open the configurable BOM palette.'
PALETTE_ID = 'fusion_configurable_bom_palette'
FIELD_ATTRIBUTE_GROUP = 'com.company.fusion_configurable_bom.fields'
CONFIG_ATTRIBUTE_GROUP = 'com.company.fusion_configurable_bom'
CONFIG_ATTRIBUTE_NAME = 'configuration'
# BOM cell values live in one JSON map on the active design's root component so
# they are saved with the design the user actually saves, even when a part is a
# component referenced from another file (whose own document is not saved here).
VALUE_ATTRIBUTE_GROUP = 'com.company.fusion_configurable_bom.values'
VALUE_ATTRIBUTE_NAME = 'component_values'
