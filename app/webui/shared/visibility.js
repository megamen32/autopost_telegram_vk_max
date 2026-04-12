/**
 * Visibility rule evaluation for conditional field display
 */

export function isFieldVisible(values, rule) {
  if (!rule) return true;

  // Handle composite rules
  if (rule.all) return rule.all.every(child => isFieldVisible(values, child));
  if (rule.any) return rule.any.some(child => isFieldVisible(values, child));

  // No field specified means always visible
  if (!rule.field) return true;

  const value = values[rule.field];

  // Equality checks
  if (rule.eq !== undefined && rule.eq !== null && value !== rule.eq) return false;
  if (rule.ne !== undefined && rule.ne !== null && value === rule.ne) return false;

  // List checks
  if (Array.isArray(rule.in) && !rule.in.includes(value)) return false;
  if (Array.isArray(rule.not_in) && rule.not_in.includes(value)) return false;

  // Boolean checks
  if (rule.is_true === true && value !== true) return false;
  if (rule.is_false === true && value !== false) return false;

  // Null checks
  if (rule.is_none === true && value !== null && value !== undefined && value !== '') return false;
  if (rule.is_not_none === true && (value === null || value === undefined || value === '')) return false;

  return true;
}

export function evaluateVisibility(form, definition) {
  if (!definition?.fields) return;

  const values = collectFormValues(form, definition);

  for (const field of definition.fields) {
    const wrapper = form.querySelector(`[data-field-wrapper="1"][data-field-name="${field.name}"]`);
    if (!wrapper) continue;

    const isVisible = isFieldVisible(values, field.visible_when);
    wrapper.classList.toggle('hidden', !isVisible);
  }
}

// Helper to collect current form values
function collectFormValues(form, def) {
  const values = {};
  for (const field of (def.fields || [])) {
    const el = form.querySelector(`[data-name="${field.name}"]`);
    if (!el) continue;
    values[field.name] = parseFieldValue(field, el);
  }
  return values;
}

// Helper to parse field value based on type
function parseFieldValue(field, el) {
  const raw = el?.type === 'checkbox' ? el.checked : el.value;

  if (field.field_type === 'bool' || field.field_type === 'checkbox') {
    return raw === true || String(raw) === 'true' || String(raw) === 'on' || String(raw) === '1';
  }
  if (field.field_type === 'int') return raw === '' ? null : Number(raw);
  if (field.field_type === 'float') return raw === '' ? null : Number(raw);
  if (field.field_type === 'list_str') {
    return String(raw || '')
      .split(',')
      .map(x => x.trim())
      .filter(Boolean);
  }
  return raw === '' ? null : String(raw);
}
