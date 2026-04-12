/**
 * Main application orchestrator.
 * Bootstraps shell UI, loads data, and mounts adapter plugins.
 */

import { apiClient, toast } from './core/api.js';
import { instanceStore } from './core/instance-store.js';
import { pluginRegistry } from './core/plugin-registry.js';
import { routeStore } from './core/route-store.js';
import { shell } from './core/shell.js';
import { state, subscribe, updateState } from './core/state.js';
import { $, $$ } from './shared/dom.js';
import { clearFieldErrors, displayFieldErrors } from './shared/messages.js';
import { escapeHtml, markdownToHtml, formatUnixTimestamp } from './shared/formatters.js';
import {
  ROUTE_POLICY_DEFAULTS as SHARED_ROUTE_POLICY_DEFAULTS,
  collectRouteFormData as collectRouteFormDataShared,
  renderRouteDetail as renderRouteDetailShared,
  validateRouteForm as validateRouteFormShared,
} from './shared/route-form.js';

export const app = {
  async init() {
    shell.init();
    this.attachStaticListeners();
    subscribe(() => {
      this.render();
    });

    try {
      await this.refreshAll();
    } catch (error) {
      console.error('Failed to initialize app:', error);
      toast('Failed to load application data');
    }
  },

  attachStaticListeners() {
    const createBtn = $('#createInstanceBtn');
    if (createBtn && !createBtn.dataset.bound) {
      createBtn.dataset.bound = '1';
      createBtn.addEventListener('click', () => {
        this.createInstanceFromForm().catch(error => {
          console.error('Create instance failed:', error);
          toast(`❌ Create failed: ${error.message}`);
        });
      });
    }

    const routeForm = $('#routeForm');
    if (routeForm && !routeForm.dataset.bound) {
      routeForm.dataset.bound = '1';
      routeForm.addEventListener('submit', event => {
        event.preventDefault();
        this.createRouteFromForm().catch(error => {
          console.error('Create route failed:', error);
          toast(`❌ Create route failed: ${error.message}`);
        });
      });
    }

    const helpCloseBtn = $('#helpCloseBtn');
    if (helpCloseBtn && !helpCloseBtn.dataset.bound) {
      helpCloseBtn.dataset.bound = '1';
      helpCloseBtn.addEventListener('click', () => this.closeHelp());
    }

    const helpBackdrop = $('#helpBackdrop');
    if (helpBackdrop && !helpBackdrop.dataset.bound) {
      helpBackdrop.dataset.bound = '1';
      helpBackdrop.addEventListener('click', event => {
        if (event.target === helpBackdrop) {
          this.closeHelp();
        }
      });
    }
  },

  async refreshAll() {
    const [defs, instances, routes, overview, jobs, links, diagnostics, helpEntries] = await Promise.all([
      apiClient.getAdapterDefinitions(),
      apiClient.getAdapterInstances(),
      apiClient.getRoutes(),
      apiClient.getOverview(),
      apiClient.getJobs(),
      apiClient.getMessageLinks(),
      apiClient.getDiagnostics(),
      apiClient.getHelpEntries(),
    ]);

    updateState({
      defs,
      instances,
      routes,
      overview,
      jobs,
      links,
      diagnostics,
      helpEntries,
    });
  },

  render() {
    this.renderOverview();
    this.renderAdapters();
    this.renderRoutes();
    this.renderJobs();
    this.renderLinks();
    this.renderDiagnostics();
    this.renderAdapterSelectOptions();
    this.attachHelpButtons(document);
  },

  renderOverview() {
    const container = $('#overview');
    if (!container) return;

    const overview = state.overview || {};
    const diagnostics = this.buildDiagnostics();
    const runtimeStatuses = overview.adapter_runtime_statuses || [];
    const instancesById = new Map((state.instances || []).map(instance => [String(instance.id), instance]));

    container.innerHTML = `
      <div class="grid">
        <div class="card">
          <h3>Summary</h3>
          <div class="muted">adapter instances: ${overview.adapter_instances_total || 0}</div>
          <div class="muted">routes: ${overview.routes_total || 0}</div>
          <div class="muted">routes with sync settings: ${overview.routes_with_policy || 0}</div>
          <div class="muted">jobs: ${overview.jobs_total || 0}</div>
          <div class="muted">links: ${overview.links_total || 0}</div>
        </div>
        <div class="card">
          <h3>Instance runtime status</h3>
          ${runtimeStatuses
            .map(
              status => `
                <div style="margin-bottom:10px">
                  <div class="mono">
                    ${escapeHtml(status.instance_id)}
                    <span class="pill">${escapeHtml(status.platform)}</span>
                    <span class="pill">${escapeHtml(status.status || 'unknown')}</span>
                    <span class="pill">${instancesById.get(String(status.instance_id))?.enabled ? 'enabled' : 'disabled'}</span>
                    ${status.connected ? '<span class="good">connected</span>' : '<span class="warning">not connected</span>'}
                  </div>
                  <div class="muted">events: ${status.events_received || 0}, ignored: ${status.events_ignored || 0}, published: ${status.posts_published || 0}</div>
                  ${status.last_error ? `<div class="warning">last error: ${escapeHtml(status.last_error)}</div>` : ''}
                  ${(status.logs || [])
                    .slice(0, 3)
                    .map(log => `<div class="muted mono">${escapeHtml(log.ts || '')} ${escapeHtml(log.message || '')}</div>`)
                    .join('')}
                </div>
              `
            )
            .join('') || '<div class="muted">no adapter instances</div>'}
        </div>
        <div class="card">
          <h3>Jobs by status</h3>
          ${Object.entries(overview.jobs_by_status || {})
            .map(([status, count]) => `<div>${escapeHtml(status)}: ${count}</div>`)
            .join('') || '<div class="muted">empty</div>'}
        </div>
        <div class="card">
          <h3>Diagnostics</h3>
          ${diagnostics.length
            ? diagnostics.map(item => `<div class="muted">${escapeHtml(item)}</div>`).join('')
            : '<div class="muted">No issues found</div>'}
        </div>
      </div>
    `;
  },

  buildDiagnostics() {
    const overview = state.overview || {};
    const diagnostics = [];

    if ((overview.routes_total || 0) > 0 && (overview.routes_with_policy || 0) === 0) {
      diagnostics.push('Routes exist but none have sync settings');
    }

    if ((overview.routes_total || 0) > (overview.routes_with_policy || 0)) {
      diagnostics.push('Some routes do not have sync settings');
    }

    const disabledUpdates = (state.instances || []).filter(item => item.enabled && item.config && item.config.receive_updates === false);
    if (disabledUpdates.length) {
      diagnostics.push(`Adapter receives no updates: ${disabledUpdates.map(item => item.id).join(', ')}`);
    }

    if ((overview.jobs_total || 0) === 0) {
      diagnostics.push('Delivery queue is idle');
    }

    return diagnostics;
  },

  async renderAdapters() {
    const container = $('#adapterInstances');
    if (!container) return;

    instanceStore.unmountAll();
    container.innerHTML = '';

    const instances = state.instances || [];
    if (!instances.length) {
      container.innerHTML = '<div class="card"><div class="muted">Инстансов пока нет</div></div>';
      return;
    }

    for (const instance of instances) {
      const definition = this.getDefinition(instance.adapter_key);
      if (!definition) continue;

      const host = document.createElement('div');
      host.id = `instance-${instance.id}`;
      container.appendChild(host);

      try {
        const controller = await pluginRegistry.mount(host, instance.adapter_key, 'instanceConfig', {
          container: host,
          definition,
          instance,
          api: apiClient,
          shared: {
            clearFieldErrors,
          },
          onSave: async instanceId => {
            await this.saveInstance(instanceId);
          },
          onDelete: async instanceId => {
            await this.deleteInstance(instanceId);
          },
          onTest: async instanceId => {
            await this.testInstance(instanceId);
          },
        });

        if (controller) {
          instanceStore.mount(instance.id, controller, {
            pluginKey: instance.adapter_key,
            definition,
            instance,
            container: host,
          });
        }
      } catch (error) {
        console.error(`Failed to render instance ${instance.id}:`, error);
        host.innerHTML = `<div class="card"><div style="color:#f87171;">Failed to load ${escapeHtml(instance.adapter_key)}: ${escapeHtml(error.message)}</div></div>`;
      }
    }

    this.attachHelpButtons(container);
  },

  async renderRoutes() {
    const container = $('#routes');
    if (!container) return;

    routeStore.unmountAll();

    const routes = state.routes || [];
    if (!routes.length) {
      container.innerHTML = '<div class="muted">Маршрутов пока нет</div>';
      return;
    }

    const rows = routes
      .map(route => {
        const expanded = state.expandedRouteId === route.id;
        return `
          <tr class="route-head" data-route-id="${escapeHtml(route.id)}">
            <td>${escapeHtml(route.id)}</td>
            <td>${this.routeEndpointDisplay(route.source_adapter_id, route.source_chat_id, route.source_chat_canonical)}</td>
            <td>${this.routeEndpointDisplay(route.target_adapter_id, route.target_chat_id, route.target_chat_canonical)}</td>
            <td>${this.routePolicyStatus(route)}</td>
          </tr>
          <tr class="route-expanded ${expanded ? '' : 'hidden'}" data-route-detail="${escapeHtml(route.id)}">
            <td colspan="4">${renderRouteDetailShared(route, {
              sourceOptions: this.renderInstanceOptions(route.source_adapter_id),
              targetOptions: this.renderInstanceOptions(route.target_adapter_id),
              helpButton: this.helpButton.bind(this),
            })}</td>
          </tr>
        `;
      })
      .join('');

    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>маршрут</th>
            <th>откуда</th>
            <th>куда</th>
            <th>состояние</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    $$('#routes [data-route-id]').forEach(row => {
      row.addEventListener('click', () => {
        const routeId = row.dataset.routeId;
        updateState({ expandedRouteId: state.expandedRouteId === routeId ? null : routeId });
      });
    });

    $$('#routes .route-policy-form').forEach(form => {
      form.addEventListener('submit', event => {
        event.preventDefault();
        this.saveRoute(form.dataset.routeId).catch(error => {
          console.error('Route save failed:', error);
          toast(`❌ Route save failed: ${error.message}`);
        });
      });
    });

    $$('#routes .route-delete-inline').forEach(button => {
      button.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        const routeId = button.dataset.id;
        if (confirm(`Delete route "${routeId}"?`)) {
          this.deleteRoute(routeId).catch(error => {
            console.error('Route delete failed:', error);
            toast(`❌ Delete failed: ${error.message}`);
          });
        }
      });
    });

    try {
      await this.mountRouteExtensions();
    } catch (error) {
      console.error('Failed to mount route extensions:', error);
    }
    this.attachHelpButtons(container);
  },

  async mountRouteExtensions() {
    const routes = state.routes || [];
    const expandedRoute = routes.find(route => route.id === state.expandedRouteId);
    if (!expandedRoute) return;

    const detail = document.querySelector(`[data-route-detail="${CSS.escape(expandedRoute.id)}"]`);
    if (!detail) return;

    const sourceContainer = detail.querySelector('[data-route-extension="source"]');
    const targetContainer = detail.querySelector('[data-route-extension="target"]');

    const sourceInstance = this.getInstanceById(expandedRoute.source_adapter_id);
    const targetInstance = this.getInstanceById(expandedRoute.target_adapter_id);
    const sourceDefinition = sourceInstance ? this.getDefinition(sourceInstance.adapter_key) : null;
    const targetDefinition = targetInstance ? this.getDefinition(targetInstance.adapter_key) : null;

    let sharedController = null;
    let sourceController = null;
    let targetController = null;

    sharedController = this.createRouteSharedController(expandedRoute, detail);

    if (sourceContainer && sourceInstance && sourceDefinition) {
      sourceController = await this.mountRouteExtensionBlock(sourceContainer, sourceInstance, sourceDefinition, expandedRoute, 'source', targetInstance);
    }

    if (targetContainer && targetInstance && targetDefinition) {
      targetController = await this.mountRouteExtensionBlock(targetContainer, targetInstance, targetDefinition, expandedRoute, 'target', sourceInstance);
    }

    routeStore.mount(expandedRoute.id, {
      shared: sharedController,
      source: sourceController,
      target: targetController,
    });
  },

  createRouteSharedController(route, root) {
    const form = root.querySelector('.route-policy-form');
    return {
      extractFormData() {
        return collectRouteFormDataShared(
          form,
          route,
          app.getInstanceById(form.source_adapter_id.value),
          app.getInstanceById(form.target_adapter_id.value)
        );
      },
      validate() {
        return validateRouteFormShared(form);
      },
      cleanup() {
        return null;
      },
      getRootElement() {
        return form;
      },
      setErrors(errors) {
        clearFieldErrors(form);
        if (errors?.length) {
          displayFieldErrors(form, errors);
        }
      },
      refreshVisibility() {
        return null;
      },
    };
  },

  async mountRouteExtensionBlock(container, instance, definition, route, role, counterpartInstance) {
    const plugin = await pluginRegistry.loadPlugin(instance.adapter_key);
    if (!(plugin.supports?.routeConfig && plugin.mountRouteConfig)) {
      container.innerHTML = '<div class="muted">Route extensions not supported</div>';
      return null;
    }

    return pluginRegistry.mount(container, instance.adapter_key, 'routeConfig', {
      container,
      definition,
      instance,
      route,
      role,
      sourceAdapter: role === 'target' ? counterpartInstance : instance,
      targetAdapter: role === 'source' ? counterpartInstance : instance,
      api: apiClient,
      shared: {},
    });
  },

  renderInstanceOptions(selectedId = '', { includePlaceholder = false } = {}) {
    const current = selectedId ? String(selectedId) : '';
    const placeholder = includePlaceholder ? '<option value="">— choose —</option>' : '';
    return (
      placeholder +
      (state.instances || [])
      .map(instance => {
        const selected = String(instance.id) === current ? 'selected' : '';
        return `<option value="${escapeHtml(instance.id)}" ${selected}>${escapeHtml(instance.display_name || instance.id)} · ${escapeHtml(instance.adapter_key)} · ${escapeHtml(instance.platform)}</option>`;
      })
      .join('')
    );
  },

  renderAdapterSelectOptions() {
    const select = $('#newAdapterKey');
    if (!select) return;

    const previous = select.value;
    select.innerHTML = (state.defs || [])
      .map(def => `<option value="${escapeHtml(def.adapter_key)}">${escapeHtml(def.title)}</option>`)
      .join('');

    if (previous) {
      select.value = previous;
    } else if (select.options.length) {
      select.selectedIndex = 0;
    }

    const routeForm = $('#routeForm');
    if (routeForm) {
      const sourceSelect = routeForm.querySelector('select[name="source_adapter_id"]');
      const targetSelect = routeForm.querySelector('select[name="target_adapter_id"]');
      if (sourceSelect) {
        const sourcePrevious = sourceSelect.value;
        sourceSelect.innerHTML = this.renderInstanceOptions(sourcePrevious, { includePlaceholder: true });
        sourceSelect.value = sourcePrevious;
      }
      if (targetSelect) {
        const targetPrevious = targetSelect.value;
        targetSelect.innerHTML = this.renderInstanceOptions(targetPrevious, { includePlaceholder: true });
        targetSelect.value = targetPrevious;
      }
    }
  },

  routeEndpointDisplay(adapterId, chatId, canonical = null) {
    const instance = this.getInstanceById(adapterId);
    const adapterLabel = instance
      ? `${escapeHtml(instance.display_name || instance.id)} (${escapeHtml(instance.adapter_key)})`
      : escapeHtml(adapterId);
    const canonicalLabel = canonical ? ` · <span class="muted mono">${escapeHtml(canonical)}</span>` : '';
    return `
      <div>${adapterLabel}</div>
      <div class="mono">${escapeHtml(chatId || '')}${canonicalLabel}</div>
    `;
  },

  routePolicyStatus(route) {
    if (!route.enabled || !route.has_policy || !route.policy_enabled) {
      return '<span class="warning">off</span>';
    }
    return '<span class="good">on</span>';
  },

  async createInstanceFromForm() {
    const adapterKey = $('#newAdapterKey')?.value;
    const displayName = $('#newDisplayName')?.value.trim();

    if (!adapterKey) {
      toast('Adapter type is required');
      return;
    }

    if (!displayName) {
      toast('Name is required');
      return;
    }

    await apiClient.createAdapterInstance({
      id: null,
      adapter_key: adapterKey,
      display_name: displayName,
      enabled: true,
      config: {},
      secrets: {},
    });

    const nameInput = $('#newDisplayName');
    if (nameInput) {
      nameInput.value = '';
    }

    toast('✓ Adapter created');
    await this.refreshAll();
  },

  async createRouteFromForm() {
    const form = $('#routeForm');
    if (!form) return;

    const sourceInstance = this.getInstanceById(form.source_adapter_id.value);
    const targetInstance = this.getInstanceById(form.target_adapter_id.value);
    if (!sourceInstance || !targetInstance) {
      toast('Choose valid source and target adapters');
      return;
    }

    const payload = {
      id: null,
      source_adapter_id: form.source_adapter_id.value,
      source_platform: sourceInstance.platform,
      source_chat_id: form.source_chat_id.value,
      target_adapter_id: form.target_adapter_id.value,
      target_platform: targetInstance.platform,
      target_chat_id: form.target_chat_id.value,
      enabled: true,
      has_policy: true,
      policy_enabled: true,
      content_policy: { ...SHARED_ROUTE_POLICY_DEFAULTS },
      repost_mode: 'ignore',
      copy_text_template: null,
    };

    await apiClient.createRoute(payload);
    toast('Маршрут создан');
    form.reset();
    await this.refreshAll();
  },

  async saveInstance(instanceId) {
    const entry = instanceStore.get(instanceId);
    if (!entry) {
      throw new Error(`Instance controller not found: ${instanceId}`);
    }

    const instance = entry.instance;
    const definition = entry.definition;
    const data = entry.controller.extractFormData();
    const payload = {
      id: instance.id,
      adapter_key: instance.adapter_key,
      display_name: data.display_name ?? instance.display_name,
      enabled: data.enabled ?? instance.enabled,
      config: {},
      secrets: {},
    };

    for (const field of definition.fields || []) {
      if (field.name === 'display_name' || field.name === 'enabled') {
        continue;
      }

      const value = data[field.name];
      if (field.secret) {
        if (value !== null && value !== undefined && value !== '') {
          payload.secrets[field.name] = value;
        }
        continue;
      }

      payload.config[field.name] = value;
    }

    await apiClient.updateAdapterInstance(instance.id, payload);
    toast('✓ Saved');
    await this.refreshAll();
  },

  async testInstance(instanceId) {
    try {
      const result = await apiClient.testAdapterInstance(instanceId);
      toast(result?.enabled ? '✓ Test passed' : '⚠ Adapter is not fully configured');
    } catch (error) {
      console.error('Test failed:', error);
      toast(`❌ Test failed: ${error.message}`);
    }
  },

  async deleteInstance(instanceId) {
    await apiClient.deleteAdapterInstance(instanceId);
    instanceStore.unmount(instanceId);
    toast('✓ Deleted');
    await this.refreshAll();
  },

  async saveRoute(routeId) {
    const route = state.routes.find(item => item.id === routeId);
    const form = document.querySelector(`.route-policy-form[data-route-id="${CSS.escape(routeId)}"]`);
    if (!route || !form) return;

    const validation = await routeStore.validate(routeId);
    routeStore.setErrors(routeId, validation.errors || []);
    if (!validation.valid) {
      toast('Please fix errors before saving');
      return;
    }

    const payload =
      (await routeStore.extractFormData(routeId)) ||
      collectRouteFormDataShared(
        form,
        route,
        this.getInstanceById(form.source_adapter_id.value),
        this.getInstanceById(form.target_adapter_id.value)
      );
    const sourceInstance = this.getInstanceById(payload.source_adapter_id);
    const targetInstance = this.getInstanceById(payload.target_adapter_id);
    if (!sourceInstance || !targetInstance) {
      toast('Choose valid source and target adapters');
      return;
    }

    payload.id = route.id;
    payload.source_platform = sourceInstance.platform;
    payload.target_platform = targetInstance.platform;
    payload.has_policy = payload.policy_enabled;
    payload.enabled = payload.policy_enabled;

    await apiClient.updateRoute(route.id, payload);
    toast('✓ Route saved');
    updateState({ expandedRouteId: route.id });
    await this.refreshAll();
  },

  async deleteRoute(routeId) {
    await apiClient.deleteRoute(routeId);
    routeStore.unmount(routeId);
    if (state.expandedRouteId === routeId) {
      updateState({ expandedRouteId: null });
    }
    toast('✓ Route deleted');
    await this.refreshAll();
  },

  getDefinition(adapterKey) {
    return (state.defs || []).find(def => def.adapter_key === adapterKey) || null;
  },

  getInstanceById(instanceId) {
    return (state.instances || []).find(instance => instance.id === instanceId) || null;
  },

  attachHelpButtons(root = document) {
    root.querySelectorAll('[data-help-id]').forEach(button => {
      if (button.dataset.helpBound) return;
      button.dataset.helpBound = '1';
      button.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        this.openHelp(button.dataset.helpId);
      });
    });
  },

  helpButton(helpId) {
    return helpId
      ? `<button class="help-icon" type="button" data-help-id="${escapeHtml(helpId)}" title="Открыть справку">?</button>`
      : '';
  },

  openHelp(id) {
    const entry = (state.helpEntries || []).find(item => item.id === id);
    if (!entry) {
      toast('Help not found');
      return;
    }

    const backdrop = $('#helpBackdrop');
    if (!backdrop) return;

    const title = $('#helpTitle');
    const summary = $('#helpSummary');
    const body = $('#helpBody');
    if (title) title.textContent = entry.title || 'Help';
    if (summary) summary.textContent = entry.summary || '';
    if (body) body.innerHTML = markdownToHtml(entry.body_markdown || '');
    backdrop.classList.add('open');
  },

  closeHelp() {
    const backdrop = $('#helpBackdrop');
    if (backdrop) backdrop.classList.remove('open');
  },

  renderJobs() {
    const container = $('#jobs');
    if (!container) return;

    const jobs = state.jobs || [];
    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>id</th>
            <th>status</th>
            <th>target</th>
            <th>origin</th>
            <th>attempts</th>
            <th>error</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${jobs
            .map(job => `
              <tr>
                <td>${escapeHtml(job.id)}</td>
                <td>${escapeHtml(job.status)}</td>
                <td>${escapeHtml(job.target_adapter_id || job.target_platform)} / <span class="mono">${escapeHtml(job.target_chat_id)}</span></td>
                <td>${escapeHtml(job.origin_adapter_id || job.origin_platform)} / <span class="mono">${escapeHtml(job.origin_chat_id)}:${escapeHtml(job.origin_message_id)}</span></td>
                <td>${escapeHtml(`${job.attempts}/${job.max_attempts}`)}</td>
                <td class="mono">${escapeHtml(job.last_error || '')}</td>
                <td>${['dead_letter', 'retrying'].includes(job.status) ? `<button class="btn secondary" type="button" data-job-id="${escapeHtml(job.id)}">requeue</button>` : ''}</td>
              </tr>
            `)
            .join('')}
        </tbody>
      </table>
    `;

    $$('#jobs [data-job-id]').forEach(button => {
      button.addEventListener('click', event => {
        event.preventDefault();
        const jobId = button.dataset.jobId;
        this.requeueJob(jobId).catch(error => {
          console.error('Requeue failed:', error);
          toast(`❌ Requeue failed: ${error.message}`);
        });
      });
    });
  },

  async requeueJob(jobId) {
    await apiClient.fetch(`/api/dashboard/jobs/${jobId}/requeue`, { method: 'POST' });
    toast('Job requeued');
    await this.refreshAll();
  },

  renderLinks() {
    const container = $('#links');
    if (!container) return;

    const links = state.links || [];
    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>id</th>
            <th>origin</th>
            <th>target</th>
            <th>created</th>
          </tr>
        </thead>
        <tbody>
          ${links
            .map(link => `
              <tr>
                <td>${escapeHtml(link.id)}</td>
                <td>${escapeHtml(link.origin_platform)} / ${escapeHtml(link.origin_adapter_id || '—')} / <span class="mono">${escapeHtml(link.origin_chat_id)}:${escapeHtml(link.origin_message_id)}</span></td>
                <td>${escapeHtml(link.target_platform)} / ${escapeHtml(link.target_adapter_id || '—')} / <span class="mono">${escapeHtml(link.target_chat_id)}:${escapeHtml(link.target_message_id)}</span></td>
                <td>${escapeHtml(formatUnixTimestamp(link.created_at ? Date.parse(link.created_at) / 1000 : null))}</td>
              </tr>
            `)
            .join('')}
        </tbody>
      </table>
    `;
  },

  renderDiagnostics() {
    const container = $('#diagnosticsPanel');
    if (!container) return;

    const diagnostics = state.diagnostics || {};
    const runtimeStatuses = diagnostics.adapter_runtime_statuses || [];
    const routeRows = diagnostics.routes || [];

    const runtimeCards = runtimeStatuses
      .map(status => `
        <div class="card" style="margin-bottom:12px">
          <div class="inline" style="justify-content:space-between">
            <strong>${escapeHtml(status.instance_id)} <span class="pill">${escapeHtml(status.platform)}</span></strong>
            <span class="muted">${escapeHtml(status.status || 'unknown')} / ${status.connected ? 'connected' : 'not connected'}</span>
          </div>
          <div class="muted">events: ${status.events_received || 0}, ignored: ${status.events_ignored || 0}, published: ${status.posts_published || 0}</div>
          <div class="muted">last event: ${escapeHtml(status.last_event_at || '—')}</div>
          <div class="muted">last error: ${escapeHtml(status.last_error || '—')}</div>
          <details style="margin-top:8px">
            <summary>Последние логи</summary>
            <div class="mono">${(status.logs || []).map(entry => `${escapeHtml(entry.ts || '')} ${escapeHtml(entry.message || '')} ${entry.extra ? escapeHtml(JSON.stringify(entry.extra)) : ''}`).join('<br>') || 'пусто'}</div>
          </details>
          <details style="margin-top:8px">
            <summary>Последние ошибки</summary>
            <div class="mono">${(status.errors || []).map(entry => `${escapeHtml(entry.ts || '')} ${escapeHtml(entry.code || '')} ${escapeHtml(entry.message || '')}`).join('<br>') || 'пусто'}</div>
          </details>
        </div>
      `)
      .join('');

    const routeTable = `
      <table>
        <thead>
          <tr>
            <th>route</th>
            <th>source</th>
            <th>target</th>
            <th>sync</th>
          </tr>
        </thead>
        <tbody>
          ${routeRows
            .map(route => `
              <tr>
                <td>${escapeHtml(route.id)}</td>
                <td>${escapeHtml(route.source_adapter_id)} / <span class="mono">${escapeHtml(route.source_chat_id)}</span></td>
                <td>${escapeHtml(route.target_adapter_id)} / <span class="mono">${escapeHtml(route.target_chat_id)}</span></td>
                <td>${route.has_policy && route.policy_enabled ? '<span class="good">on</span>' : '<span class="warning">off</span>'}</td>
              </tr>
            `)
            .join('')}
        </tbody>
      </table>
    `;

    const globalLogs = (diagnostics.global_logs || [])
      .map(entry => `${escapeHtml(entry.ts || '')} ${escapeHtml(entry.level || '')} ${escapeHtml(entry.instance_id || '')} ${escapeHtml(entry.message || '')} ${entry.extra ? escapeHtml(JSON.stringify(entry.extra)) : ''}`)
      .join('<br>') || 'пусто';

    container.innerHTML = `
      ${runtimeCards}
      <div class="card">
        <h3>Глобальные логи</h3>
        <div class="mono">${globalLogs}</div>
      </div>
      <div class="card">
        <h3>Маршруты</h3>
        ${routeTable}
      </div>
    `;
  },
};

function escapeFieldErrors(errors = []) {
  return errors.map(item => ({ field: item.field, message: item.message }));
}

document.addEventListener('DOMContentLoaded', () => {
  app.init().catch(error => {
    console.error('App initialization failed:', error);
    toast(`❌ Initialization failed: ${error.message}`);
  });
});

window.app = app;
window.state = state;
