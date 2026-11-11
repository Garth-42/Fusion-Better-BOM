/* global adsk */

const state = {
  config: null, table: null, sort: null, collapsed: new Set(),
  // The format editor works on `draft`, a private copy of the configuration, so
  // Cancel really discards and a rejected save leaves `config` untouched.
  // `draftKeys` holds attribute keys the user has retyped (original -> new).
  draft: null, draftKeys: {}, editViewId: null,
};
const $ = (id) => document.getElementById(id);
const clone = (value) => JSON.parse(JSON.stringify(value));
let copyFeedbackTimer;
let autoSaveTimer;
let cellTimer;
let closeEditorOnState = false;
// Cell edits waiting to be sent, keyed by row + field so only the latest value
// of each cell goes to Fusion.
const pendingCells = new Map();

// Typing sends one message per pause rather than one per keystroke: each save
// rewrites the design's stored value map, which is wasteful mid-word.
const CELL_SAVE_DELAY_MS = 300;
// BOM edits live in Fusion attributes, which only reach disk when the document
// is saved -- and every save creates a new version of the design. So saving is
// manual by default (the Save design button shows when there is something to
// save); the Auto-save checkbox opts in to a debounced save after edits.
const AUTO_SAVE_DELAY_MS = 900;
const AUTO_SAVE_KEY = 'fusionBomAutoSave';
const MUTATING_ACTIONS = new Set([
  'save_cell', 'save_config', 'save_as_view', 'new_field', 'add_column', 'delete_view',
]);

function send(message) {
  // Pending cell edits must reach Fusion before anything that redraws or saves.
  if (message.action !== 'save_cell') flushCells();
  if (state.table && !message.view_id) message.view_id = state.table.view_id;
  adsk.fusionSendData('fusionBomMessage', JSON.stringify(message));
  if (MUTATING_ACTIONS.has(message.action)) {
    setUnsaved(true);
    if ($('autoSave').checked) scheduleAutoSave();
  }
}

function queueCell(rowId, fieldId, value) {
  // Keep the local copy current so sorting, collapsing or copying re-renders
  // what the user typed rather than the last value Fusion sent.
  const row = state.table.rows.find((item) => item.row_id === rowId);
  if (row) row.values[fieldId] = value;
  pendingCells.set(`${rowId}\n${fieldId}`, { action: 'save_cell', row_id: rowId, field_id: fieldId, value });
  clearTimeout(cellTimer);
  cellTimer = setTimeout(flushCells, CELL_SAVE_DELAY_MS);
}

function flushCells() {
  clearTimeout(cellTimer);
  const messages = [...pendingCells.values()];
  pendingCells.clear();
  messages.forEach(send);
}

function setUnsaved(unsaved) {
  const button = $('saveDesign');
  button.classList.toggle('unsaved', unsaved);
  button.textContent = unsaved ? 'Save design •' : 'Save design';
  button.title = unsaved
    ? 'BOM changes are not yet saved with the Fusion design'
    : 'Save the Fusion design, including BOM changes';
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

function readAutoSavePreference() {
  // Storage can be unavailable in an embedded browser; default to off.
  try { return localStorage.getItem(AUTO_SAVE_KEY) === 'on'; } catch (error) { return false; }
}

function writeAutoSavePreference(enabled) {
  try { localStorage.setItem(AUTO_SAVE_KEY, enabled ? 'on' : 'off'); } catch (error) { /* not persisted */ }
}

// Fusion palettes deliver sendInfoToHTML calls through this documented bridge.
window.fusionJavaScriptHandler = {
  handle(action, data) {
    if (action !== 'fusionBomMessage') return;

    try {
      const message = JSON.parse(data);
      if (message.type === 'error') {
        closeEditorOnState = false;
        return status(message.message, true);
      }
      if (message.type === 'status') {
        if (message.design_saved) setUnsaved(false);
        return status(message.message);
      }
      if (message.type === 'copy_result') {
        showCopyFeedback(message.copied, message.row_count);
        return message.copied ? undefined : status(message.message, true);
      }
      if (message.type === 'document_changed') return documentChanged();
      if (message.type === 'state') {
        state.config = message.config;
        state.table = message.table;
        resetDraft();
        if (closeEditorOnState && $('editor').open) $('editor').close();
        closeEditorOnState = false;
        render();
      }
    } catch (error) {
      status(`Unable to display BOM data: ${error.message}`, true);
    }
  },
};

// The user switched to another Fusion document. Everything on screen -- and any
// edit not yet sent -- belongs to the previous design, so drop it and re-scan.
function documentChanged() {
  clearTimeout(cellTimer);
  clearTimeout(autoSaveTimer);
  pendingCells.clear();
  state.collapsed.clear();
  setUnsaved(false);
  if ($('editor').open) $('editor').close();
  status('Active design changed — scanning assembly…');
  send({ action: 'refresh', force: true });
}

function status(text, error = false) {
  $('status').textContent = text;
  $('status').className = error ? 'error' : '';
  // The modal editor covers the main status line, so mirror it inside.
  $('editorStatus').textContent = text;
  $('editorStatus').className = error ? 'error' : '';
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

function resetDraft() {
  state.draft = state.config ? clone(state.config) : null;
  state.draftKeys = {};
}

function currentView() {
  return state.draft.views.find((view) => view.view_id === state.editViewId) || state.draft.views[0];
}

function renderEditor() {
  if (!state.draft) return;
  const view = currentView();
  state.editViewId = view.view_id;
  $('editView').innerHTML = state.draft.views
    .map((item) => `<option value="${escape(item.view_id)}">${escape(item.name)}</option>`)
    .join('');
  $('editView').value = view.view_id;
  $('editStructure').value = view.structure || 'flat';
  $('editRollup').value = view.rollup_by || 'component';
  $('editRollup').disabled = (view.structure || 'flat') === 'hierarchical';
  $('field').innerHTML = state.draft.fields
    .map((field) => `<option value="${escape(field.field_id)}">${escape(field.default_label)}</option>`)
    .join('');
  $('columns').innerHTML = view.columns.map((column, index) => {
    const isAttribute = column.source_type === 'attribute';
    const key = state.draftKeys[column.source_id] ?? column.source_id;
    return `
    <div class="column">
      <label class="column-header">Column header<input class="header" data-index="${index}" value="${escape(column.header)}"></label>
      ${isAttribute
    ? `<label class="attribute-key">Attribute key<input class="field-id" data-original-id="${escape(column.source_id)}" value="${escape(key)}" aria-label="Attribute key for ${escape(column.header)}"></label>`
    : `<span class="builtin-source">Built-in field: ${escape(column.source_id)}</span>`}
      <label><input class="visible" data-index="${index}" type="checkbox" ${column.visible ? 'checked' : ''}> Visible</label>
      <div class="column-actions" aria-label="Reorder column">
        <button type="button" data-move="${index},-1" aria-label="Move ${escape(column.header)} up" title="Move up" ${index === 0 ? 'disabled' : ''}>↑</button>
        <button type="button" data-move="${index},1" aria-label="Move ${escape(column.header)} down" title="Move down" ${index === view.columns.length - 1 ? 'disabled' : ''}>↓</button>
      </div>
    </div>`;
  }).join('');
}

// Copy what is typed in the editor into the draft. Called before anything that
// redraws the editor (reordering, switching format) and before saving, so edits
// are not lost and the form always matches the draft.
function syncDraft() {
  if (!state.draft) return;
  const view = currentView();
  view.structure = $('editStructure').value;
  view.rollup_by = $('editRollup').value;
  document.querySelectorAll('#columns .header').forEach((element) => {
    const column = view.columns[element.dataset.index];
    if (column.header === element.value) return;
    column.header = element.value;
    if (column.source_type !== 'attribute') return;
    // A custom column's header is the field's display name everywhere.
    const field = state.draft.fields.find((item) => item.field_id === column.source_id);
    if (field) field.default_label = element.value;
    state.draft.views.forEach((item) => item.columns.forEach((other) => {
      if (other.source_type === 'attribute' && other.source_id === column.source_id) other.header = element.value;
    }));
  });
  document.querySelectorAll('#columns .visible').forEach((element) => {
    view.columns[element.dataset.index].visible = element.checked;
  });
  document.querySelectorAll('#columns .field-id').forEach((element) => {
    state.draftKeys[element.dataset.originalId] = element.value.trim();
  });
}

// Build the configuration to send from the draft plus any retyped attribute
// keys. The draft itself keeps the original keys, so if Fusion rejects the
// save the editor is still consistent and the user can simply correct and retry.
function collectEditorChanges() {
  syncDraft();
  const config = clone(state.draft);
  const renamedFields = Object.entries(state.draftKeys)
    .filter(([oldId, newId]) => newId !== oldId)
    .map(([oldId, newId]) => ({ old_id: oldId, new_id: newId }));
  renamedFields.forEach((rename) => {
    config.fields.forEach((field) => {
      if (field.field_id === rename.old_id) field.field_id = rename.new_id;
    });
    config.views.forEach((view) => view.columns.forEach((column) => {
      if (column.source_type === 'attribute' && column.source_id === rename.old_id) column.source_id = rename.new_id;
    }));
  });
  return { config, renamedFields };
}

function saveConfig() {
  const { config, renamedFields } = collectEditorChanges();
  closeEditorOnState = true;
  send({ action: 'save_config', config, renamed_fields: renamedFields });
}

$('refresh').onclick = () => { status('Scanning assembly…'); send({ action: 'refresh', force: true }); };
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
  // Always ask Fusion for the table: each row only carries values for the
  // columns of the format it was built for, so swapping columns locally would
  // show stored values as blank. The controller builds every format from one
  // cached snapshot, so this does not re-walk the assembly.
  send({ action: 'refresh', view_id: event.target.value });
};
$('autoSave').checked = readAutoSavePreference();
$('autoSave').onchange = (event) => {
  writeAutoSavePreference(event.target.checked);
  if (event.target.checked && $('saveDesign').classList.contains('unsaved')) scheduleAutoSave();
  else clearTimeout(autoSaveTimer);
};
$('edit').onclick = () => {
  if (!state.config) return status('Click Refresh to scan the design before editing formats.', true);
  flushCells();
  resetDraft();
  state.editViewId = state.table.view_id;
  renderEditor();
  $('editor').showModal();
};
// Cancel, the close button and Esc all end up here: discard unsaved edits.
$('editor').addEventListener('close', () => { closeEditorOnState = false; resetDraft(); });
$('editView').onchange = (event) => {
  // syncDraft still targets the previous format (state.editViewId).
  syncDraft();
  state.editViewId = event.target.value;
  renderEditor();
};
$('editStructure').onchange = (event) => { $('editRollup').disabled = event.target.value === 'hierarchical'; };
$('saveConfig').onclick = saveConfig;
$('saveAs').onclick = () => {
  const source = currentView();
  const name = prompt('Name for the new table format', `${source.name} Copy`);
  if (name === null) return;
  const trimmedName = name.trim();
  if (!trimmedName) return status('Enter a name to save a new table format.', true);
  const { config, renamedFields } = collectEditorChanges();
  send({ action: 'save_as_view', config, view_id: source.view_id, name: trimmedName, renamed_fields: renamedFields });
};
$('delete').onclick = () => {
  const view = currentView();
  if (!confirm(`Delete the table format "${view.name}"? This cannot be undone.`)) return;
  send({ action: 'delete_view', view_id: view.view_id });
};
$('addColumn').onclick = () => send({ action: 'add_column', view_id: currentView().view_id, field_id: $('field').value });
$('addField').onclick = () => {
  const label = prompt('Custom field name');
  if (!label) return;
  let fieldId = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  if (!fieldId) return status('Use at least one letter or number in the field name.', true);
  // Attribute keys must start with a letter and be at most 64 characters.
  if (!/^[a-z]/.test(fieldId)) fieldId = `f_${fieldId}`;
  fieldId = fieldId.slice(0, 64).replace(/_+$/, '');
  send({ action: 'new_field', field_id: fieldId, label: label.trim(), view_id: currentView().view_id });
};
$('columns').onclick = (event) => {
  if (!event.target.dataset.move) return;
  const [index, direction] = event.target.dataset.move.split(',').map(Number);
  const columns = currentView().columns;
  const destination = index + direction;
  if (destination < 0 || destination >= columns.length) return;
  syncDraft();
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
// `input` updates the local table immediately and sends the value to Fusion
// after a short pause in typing (see queueCell).
$('tbody').oninput = (event) => {
  if (!event.target.dataset.row) return;
  queueCell(event.target.dataset.row, event.target.dataset.field, event.target.value);
};
// When focus leaves the table entirely (clicking the model, a toolbar button,
// or another panel -- often just before closing Fusion) send pending edits at
// once, and save promptly if Auto-save is on.
$('tbody').onfocusout = (event) => {
  if (!event.target.dataset || !event.target.dataset.row) return;
  const goingTo = event.relatedTarget;
  if (goingTo && $('tbody').contains(goingTo)) return;
  flushCells();
  if ($('autoSave').checked && $('saveDesign').classList.contains('unsaved')) flushAutoSave();
};
setUnsaved(false);
