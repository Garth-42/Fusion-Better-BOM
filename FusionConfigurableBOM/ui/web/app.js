/* global adsk */

const state = { config: null, table: null };
const $ = (id) => document.getElementById(id);

function send(message) {
  if (state.table && !message.view_id) message.view_id = state.table.view_id;
  adsk.fusionSendData('fusionBomMessage', JSON.stringify(message));
}

// Fusion palettes deliver sendInfoToHTML calls through this documented bridge.
window.fusionJavaScriptHandler = {
  handle(action, data) {
    if (action !== 'fusionBomMessage') return;

    try {
      const message = JSON.parse(data);
      if (message.type === 'error') return status(message.message, true);
      if (message.type === 'status') return status(message.message);
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

  $('thead').innerHTML = `<tr>${state.table.columns
    .map((column) => `<th>${escape(column.header)}</th>`)
    .join('')}</tr>`;
  $('tbody').innerHTML = state.table.rows
    .map((row) => `<tr>${state.table.columns.map((column) => cell(row, column)).join('')}</tr>`)
    .join('');

  $('empty').hidden = state.table.rows.length !== 0;
  renderEditor();
  status(`Showing ${state.table.rows.length} unique component${state.table.rows.length === 1 ? '' : 's'}.`);
}

function cell(row, column) {
  const value = row.values[column.source_id] ?? '';
  if (column.source_type !== 'attribute') return `<td>${escape(String(value))}</td>`;
  if (row.linked) {
    return `<td><span title="Linked - open source design to edit">${escape(value)} 🔒</span></td>`;
  }
  return `<td><input data-row="${escape(row.row_id)}" data-field="${escape(column.source_id)}" value="${escape(value)}"></td>`;
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
  const lines = [columns.map((column) => column.header)];
  state.table.rows.forEach((row) => {
    lines.push(columns.map((column) => row.values[column.source_id] ?? ''));
  });
  return lines.map((cells) => cells.map(tsvCell).join('\t')).join('\r\n');
}

// Fusion's palette does not always grant the async Clipboard API, so keep a
// textarea + execCommand fallback for the copy button.
function legacyCopy(text) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  let copied = false;
  try {
    copied = document.execCommand('copy');
  } catch (error) {
    copied = false;
  }
  document.body.removeChild(textarea);
  return copied;
}

async function copyTable() {
  if (!state.table || state.table.rows.length === 0) {
    return status('Nothing to copy yet — click Refresh to scan the assembly.', true);
  }
  const tsv = tableToTsv();
  const count = state.table.rows.length;
  const confirm = () => status(`Copied ${count} row${count === 1 ? '' : 's'}. Paste into your spreadsheet.`);
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(tsv);
      return confirm();
    }
  } catch (error) {
    // Clipboard API blocked in this palette context; fall through to the fallback.
  }
  return legacyCopy(tsv) ? confirm() : status('Unable to access the clipboard.', true);
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
  $('viewName').value = view.name;
  $('field').innerHTML = state.config.fields
    .map((field) => `<option value="${escape(field.field_id)}">${escape(field.default_label)}</option>`)
    .join('');
  $('columns').innerHTML = view.columns.map((column, index) => `
    <div class="column">
      <input class="header" data-index="${index}" value="${escape(column.header)}">
      <label><input class="visible" data-index="${index}" type="checkbox" ${column.visible ? 'checked' : ''}> Visible</label>
      <button type="button" data-move="${index},-1">←</button>
      <button type="button" data-move="${index},1">→</button>
    </div>`).join('');
}

function saveConfig() {
  const view = currentView();
  view.name = $('viewName').value.trim() || view.name;
  document.querySelectorAll('.header').forEach((element) => {
    view.columns[element.dataset.index].header = element.value;
  });
  document.querySelectorAll('.visible').forEach((element) => {
    view.columns[element.dataset.index].visible = element.checked;
  });
  send({ action: 'save_config', config: state.config });
}

$('refresh').onclick = () => { status('Scanning assembly…'); send({ action: 'refresh' }); };
$('copy').onclick = copyTable;
$('view').onchange = (event) => {
  const view = state.config.views.find((item) => item.view_id === event.target.value);
  state.table.columns = view.columns.filter((column) => column.visible);
  state.table.view_id = view.view_id;
  render();
};
$('edit').onclick = () => $('editor').showModal();
$('close').onclick = () => $('editor').close();
$('editView').onchange = renderEditor;
$('saveConfig').onclick = saveConfig;
$('duplicate').onclick = () => send({ action: 'duplicate_view', view_id: currentView().view_id, name: `${currentView().name} Copy` });
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
$('tbody').onchange = (event) => {
  if (!event.target.dataset.row) return;
  send({ action: 'save_cell', row_id: event.target.dataset.row, field_id: event.target.dataset.field, value: event.target.value });
};
