from ..constants import FIELD_ATTRIBUTE_GROUP, LEGACY_FIELD_ATTRIBUTE_GROUP
from .attribute_groups import discard, find, put

# Per-component values. The design root's value map (value_store.py) is the
# authoritative store; this one is kept in sync as a mirror and read as a
# fallback for values entered before the root map existed.


def _find(component, field_id):
    return find(component.attributes, FIELD_ATTRIBUTE_GROUP, LEGACY_FIELD_ATTRIBUTE_GROUP, field_id)


def read_values(component, field_ids):
    return {
        field_id: (attribute.value if (attribute := _find(component, field_id)) else '')
        for field_id in field_ids
    }


def write_value(component, field_id, value):
    put(component.attributes, FIELD_ATTRIBUTE_GROUP, LEGACY_FIELD_ATTRIBUTE_GROUP, field_id, str(value))


def rename_value(component, old_field_id, new_field_id):
    attribute = _find(component, old_field_id)
    if not attribute:
        return
    write_value(component, new_field_id, attribute.value)
    attributes = component.attributes
    # The value may exist under either group name (or both); clear them all.
    for group in (FIELD_ATTRIBUTE_GROUP, LEGACY_FIELD_ATTRIBUTE_GROUP):
        discard(attributes.itemByName(group, old_field_id))
