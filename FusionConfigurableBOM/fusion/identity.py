"""Stable identity for Fusion components.

Fusion hands back a new Python proxy on every property access, so `id()` of a
proxy is useless as a key. `Component.id` is the persistent ID Fusion creates
with the component and saves with the document, so it is preferred. An
`entityToken` is only a fallback: Autodesk's guidance is that the token string
for one entity may differ between reads, so tokens should not be compared.
"""


def _read(component, name):
    try:
        value = getattr(component, name, None)
    except Exception:
        return None
    return value if isinstance(value, str) and value else None


def component_key(component):
    """Hashable in-memory key for caches and same-component checks."""
    component_id = _read(component, 'id')
    if component_id:
        return ('id', component_id)
    token = _read(component, 'entityToken')
    if token:
        return ('entity_token', token)
    return ('object_id', id(component))


def storage_keys(component):
    """Keys for the saved value map: (preferred key, legacy key).

    Values used to be stored under the entityToken. The preferred key is now
    `id:<Component.id>`; the legacy token key is still read so existing designs
    keep their values, and is folded into the preferred key on the next write.
    Either element may be None.
    """
    component_id = _read(component, 'id')
    token = _read(component, 'entityToken')
    if component_id:
        return 'id:' + component_id, token
    return token, None
