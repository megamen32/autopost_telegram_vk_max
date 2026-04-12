/**
 * Value formatting and parsing utilities
 */

export function formatValue(value, type) {
  if (value === null || value === undefined) return '';

  switch (type) {
    case 'bool':
    case 'checkbox':
      return String(value) === 'true' ? 'true' : 'false';
    case 'int':
      return String(Number(value));
    case 'float':
      return String(Number(value));
    case 'list_str':
      return Array.isArray(value) ? value.join(', ') : String(value);
    case 'textarea':
      return String(value);
    default:
      return String(value);
  }
}

export function parseValue(stringValue, type) {
  if (stringValue === '' || stringValue === null || stringValue === undefined) {
    return null;
  }

  switch (type) {
    case 'bool':
    case 'checkbox':
      return stringValue === true || String(stringValue) === 'true' || String(stringValue) === 'on' || String(stringValue) === '1';
    case 'int':
      const intVal = Number(stringValue);
      return Number.isInteger(intVal) ? intVal : null;
    case 'float':
      const floatVal = Number(stringValue);
      return !isNaN(floatVal) ? floatVal : null;
    case 'list_str':
      return String(stringValue)
        .split(',')
        .map(x => x.trim())
        .filter(Boolean);
    case 'textarea':
      return String(stringValue);
    default:
      return String(stringValue);
  }
}

export function formatUnixTimestamp(ts) {
  const value = Number(ts);
  if (!Number.isFinite(value) || value <= 0) return '—';
  return new Date(value * 1000).toLocaleString('ru-RU');
}

export function escapeHtml(str) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };
  return String(str ?? '').replace(/[&<>"']/g, m => map[m]);
}

export function markdownToHtml(md) {
  const escHtml = s => escapeHtml(s);

  return String(md || '')
    .split(/\n\n+/)
    .map(block => {
      if (block.startsWith('### ')) return `<h3>${escHtml(block.slice(4))}</h3>`;
      if (block.startsWith('## ')) return `<h2>${escHtml(block.slice(3))}</h2>`;
      if (block.startsWith('# ')) return `<h1>${escHtml(block.slice(2))}</h1>`;

      if (block.split('\n').every(line => line.trim().startsWith('- '))) {
        return (
          `<ul>${block
            .split('\n')
            .map(line => `<li>${escHtml(line.trim().slice(2))}</li>`)
            .join('')}</ul>`
        );
      }

      return `<p>${escHtml(block).replace(/\n/g, '<br>')}</p>`;
    })
    .join('');
}
