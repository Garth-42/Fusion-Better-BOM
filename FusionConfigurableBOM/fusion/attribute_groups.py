"""Read and write add-in attributes across the namespace rename.

Fusion attributes are looked up by (group name, attribute name). The group
names used to start with the template placeholder `com.company`; they now start
with NAMESPACE (see constants.py). Designs saved by earlier builds still hold
their data under the old group, so every read falls back to it, and every write
goes to the new group and then removes the old copy.
"""


def find(attributes, group, legacy_group, name):
    return attributes.itemByName(group, name) or attributes.itemByName(legacy_group, name)


def discard(attribute):
    # Removing the superseded copy is tidy-up only; a read-only (linked)
    # component may refuse, and the new group is preferred on read regardless.
    if not attribute:
        return
    try:
        attribute.deleteMe()
    except Exception:
        pass


def put(attributes, group, legacy_group, name, value):
    attribute = attributes.itemByName(group, name)
    if attribute:
        # Updating an existing Attribute marks the owning design as modified.
        attribute.value = value
    else:
        attributes.add(group, name, value)
    discard(attributes.itemByName(legacy_group, name))
