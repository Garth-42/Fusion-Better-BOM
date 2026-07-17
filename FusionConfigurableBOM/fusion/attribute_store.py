from ..constants import FIELD_ATTRIBUTE_GROUP

def read_values(component, field_ids):
    return {field_id: (attribute.value if (attribute := component.attributes.itemByName(FIELD_ATTRIBUTE_GROUP, field_id)) else '') for field_id in field_ids}

def write_value(component, field_id, value):
    component.attributes.add(FIELD_ATTRIBUTE_GROUP, field_id, str(value))

def rename_value(component, old_field_id, new_field_id):
    attribute = component.attributes.itemByName(FIELD_ATTRIBUTE_GROUP, old_field_id)
    if not attribute:
        return
    component.attributes.add(FIELD_ATTRIBUTE_GROUP, new_field_id, attribute.value)
    attribute.deleteMe()
