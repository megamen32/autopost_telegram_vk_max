/**
 * Form validation logic
 */

export function validateField(field, value) {
  // Check required
  if (field.required) {
    if (value === null || value === undefined || value === '') {
      return {
        valid: false,
        error: `${field.label} is required`,
      };
    }
  }

  // Type validation
  if (value !== null && value !== undefined && value !== '') {
    switch (field.field_type) {
      case 'int':
        if (!Number.isInteger(Number(value))) {
          return { valid: false, error: `${field.label} must be an integer` };
        }
        break;

      case 'float':
        if (isNaN(Number(value))) {
          return { valid: false, error: `${field.label} must be a number` };
        }
        break;

      case 'choice': {
        const validOptions = (field.options || []).map(o => o.value);
        if (!validOptions.includes(value)) {
          return { valid: false, error: `${field.label} has invalid value` };
        }
        break;
      }
    }
  }

  return { valid: true };
}

export function validateForm(definition, form) {
  const errors = [];

  if (!definition?.fields) {
    return { valid: true, errors: [] };
  }

  for (const field of definition.fields) {
    const el = form.querySelector(`[data-name="${field.name}"]`);
    if (!el) continue;

    const result = validateField(field, parseFieldValue(field, el));
    if (!result.valid) {
      errors.push({
        field: field.name,
        message: result.error,
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

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
