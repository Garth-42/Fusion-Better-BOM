from .models import ConceptBomRow

def build_table(rows, view):
    columns = [c for c in view.columns if c.visible]
    hierarchical = view.structure == 'hierarchical'
    serialized = []
    for row in rows:
        values = {}
        for column in columns:
            if column.source_type == 'attribute':
                values[column.source_id] = row.custom_values.get(column.source_id, '')
            else:
                values[column.source_id] = getattr(row, column.source_id, '') or ''
        entry = {'row_id': row.row_id, 'linked': row.linked, 'values': values}
        if hierarchical:
            # Tree metadata the UI needs to indent and expand/collapse. Defaults
            # keep a flat row renderable if one ever reaches a hierarchical view.
            entry['level'] = getattr(row, 'level', 0)
            entry['parent_id'] = getattr(row, 'parent_id', None)
            entry['is_assembly'] = getattr(row, 'is_assembly', False)
        serialized.append(entry)
    return {'view_id': view.view_id, 'structure': view.structure, 'rollup_by': getattr(view, 'rollup_by', 'component'), 'columns': [{'source_type': c.source_type, 'source_id': c.source_id, 'header': c.header, 'width': c.width} for c in columns], 'rows': serialized}
