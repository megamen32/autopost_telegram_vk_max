/**
 * DOM helper utilities
 */

export function $(selector) {
  return document.querySelector(selector);
}

export function $$(selector) {
  return Array.from(document.querySelectorAll(selector));
}

export function createElement(tag, options = {}) {
  const el = document.createElement(tag);
  if (options.class) el.className = options.class;
  if (options.id) el.id = options.id;
  if (options.text) el.textContent = options.text;
  if (options.html) el.innerHTML = options.html;
  Object.entries(options.attrs || {}).forEach(([key, value]) => {
    el.setAttribute(key, value);
  });
  Object.entries(options.props || {}).forEach(([key, value]) => {
    el[key] = value;
  });
  return el;
}

export function addClass(el, className) {
  if (el) el.classList.add(className);
}

export function removeClass(el, className) {
  if (el) el.classList.remove(className);
}

export function toggleClass(el, className, force) {
  if (el) el.classList.toggle(className, force);
}

export function hasClass(el, className) {
  return el?.classList.contains(className) ?? false;
}

export function setAttr(el, name, value) {
  if (el) el.setAttribute(name, value);
}

export function getAttr(el, name) {
  return el?.getAttribute(name) ?? null;
}

export function queryParent(el, selector) {
  return el?.closest(selector) ?? null;
}

export function queryAll(root, selector) {
  return Array.from((root || document).querySelectorAll(selector));
}

export function insertBefore(newEl, refEl) {
  refEl?.parentNode?.insertBefore(newEl, refEl);
}

export function insertAfter(newEl, refEl) {
  refEl?.parentNode?.insertBefore(newEl, refEl.nextSibling);
}

export function remove(el) {
  el?.parentNode?.removeChild(el);
}

export function on(el, event, handler) {
  if (el) el.addEventListener(event, handler);
  return () => el?.removeEventListener(event, handler);
}

export function once(el, event, handler) {
  if (!el) return;
  const wrapper = (e) => {
    handler(e);
    el.removeEventListener(event, wrapper);
  };
  el.addEventListener(event, wrapper);
}

export function setValue(el, value) {
  if (el) el.value = value;
}

export function getValue(el) {
  return el?.value ?? '';
}

export function setText(el, text) {
  if (el) el.textContent = text;
}

export function setHtml(el, html) {
  if (el) el.innerHTML = html;
}

export function getData(el, key) {
  return el?.dataset?.[key] ?? null;
}

export function setData(el, key, value) {
  if (el) el.dataset[key] = value;
}

export function show(el) {
  if (el) el.classList.remove('hidden');
}

export function hide(el) {
  if (el) el.classList.add('hidden');
}

export function isVisible(el) {
  return el && !el.classList.contains('hidden');
}

export function focusFirst(root, selector = 'input, select, textarea') {
  const el = (root || document).querySelector(selector);
  if (el) el.focus();
  return el;
}

export function onFormSubmit(form, handler) {
  if (!form) return;
  form.addEventListener('submit', e => {
    e.preventDefault();
    handler();
  });
}
