import json

from ..constants import VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME

# BOM cell values are stored in one JSON map on the *active design's* root
# component, keyed by each component's persistent entityToken. Storing a value on
# the component itself does not survive a save when that component lives in
# another (referenced) file, because saving the active design does not save the
# referenced document - that is why edited values vanished on close/reopen. The
# root component always belongs to the active design, so its attributes are
# written whenever the user saves.


def _component_key(component):
    token = getattr(component, 'entityToken', None)
    return token or None


def _attributes(root):
    return getattr(root, 'attributes', None)


def _load_map(root):
    attributes = _attributes(root)
    if attributes is None:
        return {}
    attribute = attributes.itemByName(VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME)
    if not attribute:
        return {}
    try:
        data = json.loads(attribute.value)
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _store_map(root, data):
    attributes = _attributes(root)
    if attributes is None:
        return
    value = json.dumps(data, separators=(',', ':'), sort_keys=True)
    attribute = attributes.itemByName(VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME)
    if attribute:
        # Updating an existing attribute marks the owning design as modified.
        attribute.value = value
    else:
        attributes.add(VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME, value)


def read_values(root, component, field_ids):
    """Return only the field_ids present for this component, so an empty stored
    value ('') is preserved and can override a stale component attribute."""
    key = _component_key(component)
    entry = _load_map(root).get(key, {}) if key else {}
    return {field_id: entry[field_id] for field_id in field_ids if field_id in entry}


def write_value(root, component, field_id, value):
    key = _component_key(component)
    if not key or _attributes(root) is None:
        return False
    data = _load_map(root)
    data.setdefault(key, {})[field_id] = str(value)
    _store_map(root, data)
    return True


def rename_field(root, old_field_id, new_field_id):
    if old_field_id == new_field_id:
        return
    data = _load_map(root)
    changed = False
    for entry in data.values():
        if isinstance(entry, dict) and old_field_id in entry:
            entry[new_field_id] = entry.pop(old_field_id)
            changed = True
    if changed:
        _store_map(root, data)
