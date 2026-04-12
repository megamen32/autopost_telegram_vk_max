/**
 * MAX adapter plugin
 */

import { renderFields } from '../../shared/form-renderer.js';
import { evaluateVisibility } from '../../shared/visibility.js';
import { validateForm } from '../../shared/validation.js';
import { parseValue } from '../../shared/formatters.js';

async function mountInstanceConfig(ctx) {
  const { container, template, definition, instance } = ctx;
  const config = instance.config || {};
  const secretFieldsPresent = instance.secret_fields_present || {};

  const simple = definition.fields.filter(f => f.scope === 'simple');
  const advanced = definition.fields.filter(f => f.scope === 'advanced');

  const helpButton = (id) =>
    id ? `<button class="help-icon" type="button" data-help-id="${escapeHtml(id)}" title="Открыть справку">?</button>` : '';

  const wrapper = document.createElement('div');
  wrapper.innerHTML = template || '';
  const form = wrapper.querySelector('form') || document.createElement('form');
  if (!form.parentElement) {
    form.className = 'instance-form adapter-max__form';
    wrapper.appendChild(form);
  }
  form.dataset.adapterKey = 'max';
  form.dataset.instanceId = instance.id;
  form.querySelector('[data-slot="display-name"]')?.replaceChildren(document.createTextNode(instance.display_name || 'MAX'));
  form.querySelector('[data-slot="instance-id"]')?.replaceChildren(document.createTextNode(instance.id));
  form.querySelector('[data-slot="fields-basic"]')?.replaceChildren(htmlToFragment(renderFields(simple, config, secretFieldsPresent, helpButton)));
  form.querySelector('[data-slot="fields-advanced"]')?.replaceChildren(htmlToFragment(renderFields(advanced, config, secretFieldsPresent, helpButton)));
  const extraSlot = form.querySelector('[data-slot="extra"]');
  if (extraSlot) {
    extraSlot.innerHTML = '';
  }
  container.appendChild(form);

  const controller = createController(form, definition, instance, ctx.api);

  form.addEventListener('change', () => evaluateVisibility(form, definition));
  form.addEventListener('input', () => evaluateVisibility(form, definition));
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    ctx.onSave?.(instance.id, controller);
  });

  form.querySelector('.instance-delete-btn')?.addEventListener('click', () => {
    if (confirm(`Delete adapter instance "${instance.display_name}"?`)) {
      ctx.onDelete?.(instance.id);
    }
  });

  form.querySelector('.instance-test-btn')?.addEventListener('click', async () => {
    try {
      await ctx.api.testAdapterInstance(instance.id);
      console.log('Test passed');
    } catch (e) {
      console.error('Test failed:', e);
    }
  });

  evaluateVisibility(form, definition);

  return controller;
}

function createController(form, definition, instance, api) {
  return {
    extractFormData() {
      const data = {};
      for (const field of definition.fields) {
        const el = form.querySelector(`[data-name="${field.name}"]`);
        if (!el) continue;
        data[field.name] = parseValue(el.type === 'checkbox' ? el.checked : el.value, field.field_type);
      }
      return data;
    },

    validate() {
      return validateForm(definition, form);
    },

    cleanup() {
      form.remove();
    },

    getRootElement() {
      return form;
    },

    setErrors(errors) {
      errors.forEach(error => {
        const field = form.querySelector(`[data-name="${error.field}"]`);
        if (field) {
          const errorEl = document.createElement('div');
          errorEl.style.color = '#f87171';
          errorEl.style.fontSize = '12px';
          errorEl.style.marginTop = '4px';
          errorEl.textContent = error.message;
          field.parentNode.appendChild(errorEl);
        }
      });
    },

    refreshVisibility() {
      evaluateVisibility(form, definition);
    },
  };
}

function escapeHtml(str) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };
  return String(str ?? '').replace(/[&<>"']/g, m => map[m]);
}

function htmlToFragment(html) {
  const template = document.createElement('template');
  template.innerHTML = html;
  return template.content;
}

async function mountRouteConfig(ctx) {
  const { container, template, route, role, instance, sourceAdapter, targetAdapter } = ctx;
  const div = document.createElement('div');
  div.className = 'adapter-max__route-config';
  div.innerHTML = template || '<div class="adapter-max__route-template"></div>';
  const root = div.firstElementChild || div;
  root.innerHTML = `
    <div class="muted">No additional route settings for MAX</div>
    <div class="help" style="margin-top:4px">
      route: <span class="mono">${escapeHtml(route?.id || 'unknown')}</span> · role: <span class="mono">${escapeHtml(role || 'unknown')}</span>
    </div>
    <div class="help">adapter: <span class="mono">${escapeHtml(instance?.adapter_key || 'max')}</span></div>
    <div class="help">
      peer: <span class="mono">${escapeHtml((role === 'source' ? targetAdapter : sourceAdapter)?.display_name || '—')}</span>
    </div>
  `;
  container.appendChild(div);

  return {
    extractFormData() {
      return {};
    },
    validate() {
      return { valid: true, errors: [] };
    },
    cleanup() {
      div.remove();
    },
    getRootElement() {
      return root;
    },
  };
}

export default {
  key: 'max',

  supports: {
    instanceConfig: true,
    routeConfig: true,
    preview: false,
    diagnostics: false,
    logs: false,
  },

  mountInstanceConfig,
  mountRouteConfig,
};
