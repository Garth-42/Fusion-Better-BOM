/* global adsk */

const state = { config: null, table: null, sort: null, collapsed: new Set() };
const $ = (id) => document.getElementById(id);
let copyFeedbackTimer;
let autoSaveTimer;

// Attribute and configuration edits live in Fusion attributes, which only reach
// disk when the document is saved. Saving on every keystroke would be slow, so
// mutating actions schedule a debounced save that coalesces a burst of edits
// into a single persist. The manual Save design button stays for an immediate save.
const AUTO_SAVE_DELAY_MS = 900;
const MUTATING_ACTIONS = new Set([
  'save_cell', 'save_config', 'save_as_view', 'new_field',
  'add_column', 'duplicate_view', 'delete_view',
]);

function send(message) {
  if (state.table && !message.view_id) message.view_id = state.table.view_id;
  adsk.fusionSendData('fusionBomMessage', JSON.stringify(message));
  if (MUTATING_ACTIONS.has(message.action)) scheduleAutoSave();
}

function scheduleAutoSave() {
  clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(flushAutoSave, AUTO_SAVE_DELAY_MS);
}

function flushAutoSave() {
  clearTimeout(autoSaveTimer);
  // `auto` keeps this best-effort: a document that cannot be saved yet must not
  // raise the way an explicit Save design click does.
  send({ action: 'save_design', auto: true });
}

// Fusion palettes deliver sendInfoToHTML calls through this documented bridge.
window.fusionJavaScriptHandler = {
  handle(action, data) {
    if (action !== 'fusionBomMessage') return;

    try {
      const message = JSON.parse(data);
      if (message.type === 'error') return status(message.message, true);
      if (message.type === 'status') return status(message.message);
      if (message.type === 'copy_result') {
        showCopyFeedback(message.copied, message.row_count);
        return message.copied ? undefined : status(message.message, true);
      }
      if (message.type === 'state') {
        state.config = message.config;
        state.table = message.table;
        render();
      }
    } catch (error) {
      status(`Unable to display BOM data: ${error.message}`, true);
    }
  },
};

function status(text, error = false) {
  $('status').textContent = text;
  $('status').className = error ? 'error' : '';
}

function render() {
  if (!state.config || !state.table) return;

  const viewSelect = $('view');
  viewSelect.innerHTML = state.config.views
    .map((view) => `<option value="${escape(view.view_id)}">${escape(view.name)}</option>`)
    .join('');
  viewSelect.value = state.table.view_id;

  const hierarchical = state.table.structure === 'hierarchical';
  const treeIndex = hierarchical ? treeColumnIndex() : -1;
  $('thead').innerHTML = `<tr>${state.table.columns
    .map((column) => columnHeader(column, hierarchical))
    .join('')}</tr>`;
  const rows = hierarchical ? visibleTreeRows() : sortedRows();
  $('tbody').innerHTML = rows
    .map((row) => renderRow(row, treeIndex))
    .join('');

  $('empty').hidden = state.table.rows.length !== 0;
  $('tableHint').hidden = !state.table.rows.some((row) => rowHasEditableColumn(row));
  renderEditor();
  if (hierarchical) {
    const total = state.table.rows.length;
    status(`Showing ${rows.length} of ${total} assembly line${total === 1 ? '' : 's'}.`);
  } else {
    status(`Showing ${state.table.rows.length} unique component${state.table.rows.length === 1 ? '' : 's'}.`);
  }
}

// The tree affordance (indent + expand/collapse) lives on the Component column
// when the view shows it, otherwise on the first column.
function treeColumnIndex() {
  const index = state.table.columns.findIndex((column) => column.source_id === 'component_name');
  return index === -1 ? 0 : index;
}

function renderRow(row, treeIndex) {
  const assembly = treeIndex !== -1 && row.is_assembly;
  return `<tr${assembly ? ' class="assembly-row"' : ''}>${state.table.columns
    .map((column, index) => cell(row, column, index === treeIndex ? treeLead(row) : ''))
    .join('')}</tr>`;
}

function treeLead(row) {
  const style = `padding-left:${(row.level || 0) * 16}px`;
  if (!row.is_assembly) {
    return `<span class="tree-lead" style="${style}"><span class="tree-spacer"></span></span>`;
  }
  const collapsed = state.collapsed.has(row.row_id);
  const label = `${collapsed ? 'Expand' : 'Collapse'} ${row.values.component_name ?? 'assembly'}`;
  return `<span class="tree-lead" style="${style}"><button class="tree-toggle" type="button" data-toggle="${escape(row.row_id)}" aria-expanded="${collapsed ? 'false' : 'true'}" aria-label="${escape(label)}" title="${collapsed ? 'Expand' : 'Collapse'}">${collapsed ? '▶' : '▼'}</button></span>`;
}

// A row is hidden when any ancestor is collapsed. Rows arrive parent-before-child,
// so one pass over the parent chain is enough.
function visibleTreeRows() {
  const parentOf = new Map(state.table.rows.map((row) => [row.row_id, row.parent_id]));
  const hidden = (row) => {
    let parent = row.parent_id;
    while (parent != null) {
      if (state.collapsed.has(parent)) return true;
      parent = parentOf.get(parent);
    }
    return false;
  };
  return state.table.rows.filter((row) => !hidden(row));
}

function columnHeader(column, hierarchical = false) {
  // Sorting a tree by a column would break parent/child nesting, so a structured
  // view shows plain headers without the flat sort controls.
  if (hierarchical) return `<th><span class="column-heading"><span>${escape(column.header)}</span></span></th>`;
  const isSorted = state.sort && state.sort.sourceId === column.source_id;
  const active = (direction) => isSorted && state.sort.direction === direction ? ' active' : '';
  return `<th><span class="column-heading"><span>${escape(column.header)}</span><span class="sort-actions" aria-label="Sort ${escape(column.header)}"><button class="sort-button${active('ascending')}" type="button" data-sort="${escape(column.source_id)},ascending" aria-label="Sort ${escape(column.header)} ascending" title="Sort ascending">▲</button><button class="sort-button${active('descending')}" type="button" data-sort="${escape(column.source_id)},descending" aria-label="Sort ${escape(column.header)} descending" title="Sort descending">▼</button></span></span></th>`;
}

function sortedRows() {
  const rows = [...state.table.rows];
  if (!state.sort) return rows;
  const { sourceId, direction } = state.sort;
  const multiplier = direction === 'ascending' ? 1 : -1;
  return rows.sort((left, right) => compareValues(left.values[sourceId], right.values[sourceId]) * multiplier);
}

function compareValues(left, right) {
  const leftText = String(left ?? '');
  const rightText = String(right ?? '');
  const leftNumber = Number(leftText);
  const rightNumber = Number(rightText);
  if (leftText !== '' && rightText !== '' && Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {
    return leftNumber - rightNumber;
  }
  return leftText.localeCompare(rightText, undefined, { numeric: true, sensitivity: 'base' });
}

function cell(row, column, lead = '') {
  const value = row.values[column.source_id] ?? '';
  if (column.source_type !== 'attribute') return `<td>${lead}${escape(String(value))}</td>`;
  if (row.linked) {
    return `<td>${lead}<span title="Linked - open source design to edit">${escape(value)} 🔒</span></td>`;
  }
  return `<td class="editable-cell" title="Editable cell">${lead}<input data-row="${escape(row.row_id)}" data-field="${escape(column.source_id)}" aria-label="${escape(column.header)} for ${escape(row.values.component_name ?? 'component')} (editable)" value="${escape(value)}"><span class="edit-marker" aria-hidden="true">✎</span></td>`;
}

function rowHasEditableColumn(row) {
  return !row.linked && state.table.columns.some((column) => column.source_type === 'attribute');
}

function escape(value) {
  return String(value).replace(/[&<>"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
  }[character]));
}

// Spreadsheets split a pasted cell on tabs/newlines, so any value containing
// them must be quoted (with embedded quotes doubled) exactly like a TSV field.
function tsvCell(value) {
  const text = String(value ?? '');
  return /[\t\r\n"]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

// Serialize exactly what the current view shows — visible columns and their
// raw values — as tab-separated rows that paste straight into Sheets/Excel.
function tableToTsv() {
  const columns = state.table.columns;
  const hierarchical = state.table.structure === 'hierarchical';
  const treeIndex = hierarchical ? treeColumnIndex() : -1;
  const rows = hierarchical ? visibleTreeRows() : sortedRows();
  const lines = [columns.map((column) => column.header)];
  rows.forEach((row) => {
    lines.push(columns.map((column, index) => {
      const value = row.values[column.source_id] ?? '';
      // Indent the tree column so the pasted outline keeps its structure.
      return index === treeIndex && row.level ? '  '.repeat(row.level) + value : value;
    }));
  });
  return lines.map((cells) => cells.map(tsvCell).join('\t')).join('\r\n');
}

function showCopyFeedback(copied, count) {
  const button = $('copy');
  clearTimeout(copyFeedbackTimer);
  button.classList.remove('copied', 'copy-failed');
  button.classList.add(copied ? 'copied' : 'copy-failed');
  button.textContent = copied ? 'Copied ✓' : 'Copy failed';
  copyFeedbackTimer = setTimeout(() => {
    button.classList.remove('copied', 'copy-failed');
    button.textContent = 'Copy table';
  }, 1800);
  if (copied) status(`Copied ${count} row${count === 1 ? '' : 's'}. Paste into your spreadsheet.`);
}

function copyTable() {
  if (!state.table || state.table.rows.length === 0) {
    return status('Nothing to copy yet — click Refresh to scan the assembly.', true);
  }
  const tsv = tableToTsv();
  status('Copying table to the system clipboard…');
  send({ action: 'copy_table', tsv, row_count: state.table.rows.length });
}

function currentView() {
  return state.config.views.find((view) => view.view_id === $('editView').value) || state.config.views[0];
}

function renderEditor() {
  if (!state.config) return;
  const view = currentView();
  $('editView').innerHTML = state.config.views
    .map((item) => `<option value="${escape(item.view_id)}">${escape(item.name)}</option>`)
    .join('');
  $('editView').value = view.view_id;
  $('field').innerHTML = state.config.fields
    .map((field) => `<option value="${escape(field.field_id)}">${escape(field.default_label)}</option>`)
    .join('');
  $('columns').innerHTML = view.columns.map((column, index) => {
    const isAttribute = column.source_type === 'attribute';
    return `
    <div class="column">
      <label class="column-header">Column header<input class="header" data-index="${index}" value="${escape(column.header)}"></label>
      ${isAttribute
    ? `<label class="attribute-key">Attribute key<input class="field-id" data-original-id="${escape(column.source_id)}" value="${escape(column.source_id)}" aria-label="Attribute key for ${escape(column.header)}"></label>`
    : `<span class="builtin-source">Built-in field: ${escape(column.source_id)}</span>`}
      <label><input class="visible" data-index="${index}" type="checkbox" ${column.visible ? 'checked' : ''}> Visible</label>
      <div class="column-actions" aria-label="Reorder column">
        <button type="button" data-move="${index},-1" aria-label="Move ${escape(column.header)} up" title="Move up" ${index === 0 ? 'disabled' : ''}>↑</button>
        <button type="button" data-move="${index},1" aria-label="Move ${escape(column.header)} down" title="Move down" ${index === view.columns.length - 1 ? 'disabled' : ''}>↓</button>
      </div>
    </div>`;
  }).join('');
}

function collectEditorChanges() {
  const view = currentView();
  document.querySelectorAll('.header').forEach((element) => {
    view.columns[element.dataset.index].header = element.value;
  });
  document.querySelectorAll('.visible').forEach((element) => {
    view.columns[element.dataset.index].visible = element.checked;
  });
  const displayNames = new Map(view.columns
    .filter((column) => column.source_type === 'attribute')
    .map((column) => [column.source_id, column.header]));
  state.config.fields.forEach((field) => {
    const displayName = displayNames.get(field.field_id);
    if (displayName === undefined) return;
    field.default_label = displayName;
    state.config.views.forEach((item) => item.columns.forEach((column) => {
      if (column.source_type === 'attribute' && column.source_id === field.field_id) column.header = displayName;
    }));
  });
  const renamedFields = [];
  const fieldsByOriginalId = new Map(state.config.fields.map((field) => [field.field_id, field]));
  document.querySelectorAll('.field-id').forEach((element) => {
    const field = fieldsByOriginalId.get(element.dataset.originalId);
    const fieldId = element.value.trim();
    if (fieldId !== field.field_id) renamedFields.push({ old_id: field.field_id, new_id: fieldId });
    field.field_id = fieldId;
  });
  if (renamedFields.length) {
    state.config.views.forEach((item) => item.columns.forEach((column) => {
      const rename = renamedFields.find((change) => change.old_id === column.source_id);
      if (rename && column.source_type === 'attribute') column.source_id = rename.new_id;
    }));
  }
  return renamedFields;
}

function saveConfig() {
  const renamedFields = collectEditorChanges();
  send({ action: 'save_config', config: state.config, renamed_fields: renamedFields });
}

$('refresh').onclick = () => { status('Scanning assembly…'); send({ action: 'refresh' }); };
$('saveDesign').onclick = () => { clearTimeout(autoSaveTimer); status('Saving Fusion design…'); send({ action: 'save_design' }); };
$('copy').onclick = copyTable;
$('thead').onclick = (event) => {
  const sort = event.target.dataset.sort;
  if (!sort) return;
  const [sourceId, direction] = sort.split(',');
  state.sort = { sourceId, direction };
  render();
};
$('view').onchange = (event) => {
  const view = state.config.views.find((item) => item.view_id === event.target.value);
  // Flat and hierarchical views need differently shaped rows (aggregated leaves
  // vs tree nodes), so switching the BOM structure re-scans in the new mode
  // instead of just re-filtering columns from the current rows.
  if ((view.structure || 'flat') !== (state.table.structure || 'flat')) {
    status('Scanning assembly…');
    return send({ action: 'refresh', view_id: view.view_id });
  }
  state.table.columns = view.columns.filter((column) => column.visible);
  state.table.view_id = view.view_id;
  render();
};
$('edit').onclick = () => $('editor').showModal();
$('editView').onchange = renderEditor;
$('saveConfig').onclick = saveConfig;
$('saveAs').onclick = () => {
  const source = currentView();
  const name = prompt('Name for the new table format', `${source.name} Copy`);
  if (name === null) return;
  const trimmedName = name.trim();
  if (!trimmedName) return status('Enter a name to save a new table format.', true);
  const renamedFields = collectEditorChanges();
  send({ action: 'save_as_view', config: state.config, view_id: source.view_id, name: trimmedName, renamed_fields: renamedFields });
};
$('delete').onclick = () => send({ action: 'delete_view', view_id: currentView().view_id });
$('addColumn').onclick = () => send({ action: 'add_column', view_id: currentView().view_id, field_id: $('field').value });
$('addField').onclick = () => {
  const label = prompt('Custom field name');
  if (!label) return;
  const fieldId = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  if (!fieldId) return status('Use at least one letter or number in the field name.', true);
  send({ action: 'new_field', field_id: fieldId, label, view_id: currentView().view_id });
};
$('columns').onclick = (event) => {
  if (!event.target.dataset.move) return;
  const [index, direction] = event.target.dataset.move.split(',').map(Number);
  const columns = currentView().columns;
  const destination = index + direction;
  if (destination < 0 || destination >= columns.length) return;
  [columns[index], columns[destination]] = [columns[destination], columns[index]];
  renderEditor();
};
// Expand/collapse a sub-assembly. Toggle buttons are the only elements in the
// table body carrying data-toggle, so other clicks (including into inputs) pass
// through untouched.
$('tbody').onclick = (event) => {
  const rowId = event.target.dataset.toggle;
  if (!rowId) return;
  if (state.collapsed.has(rowId)) state.collapsed.delete(rowId);
  else state.collapsed.add(rowId);
  render();
};
// `input` writes the value into the Fusion attribute while the user types so the
// live table stays correct; the debounced auto-save (scheduled by `send`) then
// persists it to the document a moment after typing stops.
$('tbody').oninput = (event) => {
  if (!event.target.dataset.row) return;
  send({ action: 'save_cell', row_id: event.target.dataset.row, field_id: event.target.dataset.field, value: event.target.value });
};
// Persist promptly when focus leaves the table entirely (clicking the model, a
// toolbar button, or another panel — often just before closing Fusion). Moving
// between cells stays coalesced by the debounce instead of saving per cell.
$('tbody').onfocusout = (event) => {
  if (!event.target.dataset || !event.target.dataset.row) return;
  const goingTo = event.relatedTarget;
  if (goingTo && $('tbody').contains(goingTo)) return;
  flushAutoSave();
};
