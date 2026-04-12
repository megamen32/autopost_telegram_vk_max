/**
 * Common UI messages and error handling
 */

import { $ } from './dom.js';

export function toast(msg) {
  const el = $('#toast');
  if (el) {
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 3000);
  }
}

export function showError(msg) {
  toast(`❌ ${msg}`);
}

export function showSuccess(msg) {
  toast(`✓ ${msg}`);
}

export function showInfo(msg) {
  toast(`ℹ ${msg}`);
}

export const errorMessages = {
  REQUIRED_FIELD: (label) => `${label} обязательное поле`,
  INVALID_TYPE: (label, type) => `${label} должно быть ${type}`,
  INVALID_VALUE: (label) => `${label} содержит неправильное значение`,
  NETWORK_ERROR: 'Ошибка сети. Попробуй позже',
  UNKNOWN_ERROR: 'Неизвестная ошибка',
  NOT_FOUND: 'Не найдено',
  INVALID_JSON: 'Неправильный JSON формат',
  DUPLICATE: (name) => `${name} уже существует`,
  CANNOT_DELETE: (name) => `Не можно удалить ${name}`,
  UNAUTHORIZED: 'Авторизация требуется',
  FORBIDDEN: 'Доступ запрещён',
  BAD_REQUEST: 'Неправильный запрос',
  SERVER_ERROR: 'Ошибка сервера',
};

export function getErrorMessage(error) {
  if (typeof error === 'string') return error;
  if (error?.message) return error.message;
  return errorMessages.UNKNOWN_ERROR;
}

export function formatFieldError(fieldName, errorMessage) {
  return {
    field: fieldName,
    message: errorMessage,
  };
}

export function displayFieldErrors(form, errors) {
  // Clear previous errors
  form.querySelectorAll('.field-error').forEach(el => el.remove());

  // Add new errors
  errors.forEach(error => {
    const field = form.querySelector(`[data-name="${error.field}"]`);
    if (field) {
      const errorEl = document.createElement('div');
      errorEl.className = 'field-error';
      errorEl.style.color = '#f87171';
      errorEl.style.fontSize = '12px';
      errorEl.style.marginTop = '4px';
      errorEl.textContent = error.message;
      field.parentNode.appendChild(errorEl);
    }
  });
}

export function clearFieldErrors(form) {
  form.querySelectorAll('.field-error').forEach(el => el.remove());
}
