import json

from ..constants import LEGACY_VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME
from .attribute_groups import find, put
from .identity import storage_keys

# BOM cell values are stored in one JSON map on the *active design's* root
# component, keyed by each component's persistent ID (see identity.py). Storing
# a value on the component itself does not survive a save when that component
# lives in another (referenced) file, because saving the active design does not
# save the referenced document - that is why edited values vanished on
# close/reopen. The root component always belongs to the active design, so its
# attributes are written whenever the user saves.


def _attributes(root):
    return getattr(root, 'attributes', None)


def load_map(root):
    """Parse the whole saved value map once (the scanner reuses it per scan)."""
    attributes = _attributes(root)
    if attributes is None:
        return {}
    attribute = find(attributes, VALUE_ATTRIBUTE_GROUP, LEGACY_VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME)
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
    put(attributes, VALUE_ATTRIBUTE_GROUP, LEGACY_VALUE_ATTRIBUTE_GROUP, VALUE_ATTRIBUTE_NAME, value)


def _entry(data, component):
    """Merged values for a component: legacy token entry, then the ID entry."""
    key, legacy_key = storage_keys(component)
    merged = {}
    for candidate in (legacy_key, key):
        entry = data.get(candidate) if candidate else None
        if isinstance(entry, dict):
            merged.update(entry)
    return merged


def read_values(root, component, field_ids, data=None):
    """Return only the field_ids present for this component, so an empty stored
    value ('') is preserved and can override a stale component attribute.

    Pass `data` (from load_map) to avoid re-parsing the map for every component.
    """
    entry = _entry(load_map(root) if data is None else data, component)
    return {field_id: entry[field_id] for field_id in field_ids if field_id in entry}


def write_values(root, components, field_id, value):
    """Store one field value for several components with a single map rewrite."""
    if _attributes(root) is None:
        return False
    data = load_map(root)
    written = False
    for component in components:
        key, legacy_key = storage_keys(component)
        if not key:
            continue
        entry = _entry(data, component)
        entry[field_id] = str(value)
        data[key] = entry
        if legacy_key:
            data.pop(legacy_key, None)  # Folded into the ID entry above.
        written = True
    if written:
        _store_map(root, data)
    return written


def write_value(root, component, field_id, value):
    return write_values(root, [component], field_id, value)


def rename_field(root, old_field_id, new_field_id):
    if old_field_id == new_field_id:
        return
    data = load_map(root)
    changed = False
    for entry in data.values():
        if isinstance(entry, dict) and old_field_id in entry:
            entry[new_field_id] = entry.pop(old_field_id)
            changed = True
    if changed:
        _store_map(root, data)
