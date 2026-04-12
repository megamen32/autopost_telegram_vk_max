/**
 * Generic form field rendering
 */

import { escapeHtml, formatValue } from './formatters.js';

export function renderField(field, value, secretPresent = false) {
  const val = value ?? field.default ?? '';
  const attrs = `data-name="${field.name}" data-type="${field.field_type}" ${field.secret ? 'data-secret="1"' : ''}`;

  // Boolean field - select true/false
  if (field.field_type === 'bool') {
    return `<select ${attrs}>
      <option value="true" ${val !== false ? 'selected' : ''}>true</option>
      <option value="false" ${val === false ? 'selected' : ''}>false</option>
    </select>`;
  }

  if (field.field_type === 'checkbox') {
    return `<input ${attrs} type="checkbox" ${val ? 'checked' : ''}>`;
  }

  // Choice field - select from options
  if (field.field_type === 'choice') {
    return `<select ${attrs}>
      ${(field.options || [])
        .map(o => `<option value="${escapeHtml(o.value)}" ${o.value === val ? 'selected' : ''}>${escapeHtml(o.label)}</option>`)
        .join('')}
    </select>`;
  }

  // List of strings - comma-separated
  if (field.field_type === 'list_str') {
    const formatted = Array.isArray(val) ? val.join(', ') : formatValue(val, 'list_str');
    return `<input ${attrs} value="${escapeHtml(formatted)}" placeholder="id1, id2">`;
  }

  if (field.field_type === 'textarea') {
    return `<textarea ${attrs} placeholder="${escapeHtml(field.placeholder || '')}">${escapeHtml(formatValue(val, 'textarea'))}</textarea>`;
  }

  // Password/secret field
  if (field.secret) {
    return `<input ${attrs} type="password" placeholder="${secretPresent ? 'Оставь пустым чтобы не менять' : 'Введите значение'}">`;
  }

  // Default: text input (works for str, int, float, etc.)
  return `<input ${attrs} value="${escapeHtml(formatValue(val, field.field_type))}">`;
}

export function renderFieldWrapper(field, value, secretPresent, helpButton) {
  const fieldHtml = renderField(field, value, secretPresent);

  return `<label data-field-wrapper="1" data-field-name="${escapeHtml(field.name)}">
    <span class="label-row">
      <span class="label">${escapeHtml(field.label)}</span>
      ${helpButton ? helpButton(field.help_entry_id) : ''}
    </span>
    ${fieldHtml}
    <span class="help">${escapeHtml(field.help_text || '')}</span>
  </label>`;
}

export function renderFields(fields, config, secretFieldsPresent, helpButton) {
  return fields
    .map(f => renderFieldWrapper(f, config[f.name], !!secretFieldsPresent[f.name], helpButton))
    .join('');
}
