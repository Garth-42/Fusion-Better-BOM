from ..constants import FIELD_ATTRIBUTE_GROUP

def read_values(component, field_ids):
    return {field_id: (attribute.value if (attribute := component.attributes.itemByName(FIELD_ATTRIBUTE_GROUP, field_id)) else '') for field_id in field_ids}

def write_value(component, field_id, value):
    component.attributes.add(FIELD_ATTRIBUTE_GROUP, field_id, str(value))
