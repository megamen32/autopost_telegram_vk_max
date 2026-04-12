/**
 * API wrapper - all HTTP communication goes through here
 */

async function api(url, opts = {}) {
  const response = await fetch(url, {
    headers: { 'content-type': 'application/json' },
    ...opts,
  });
  if (!response.ok) throw new Error(await response.text());
  const contentType = response.headers.get('content-type');
  return contentType?.includes('json') ? response.json() : response.text();
}

function unwrapList(payload, key) {
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload?.[key] || [];
}

export const apiClient = {
  // Adapter definitions and instances
  async getAdapterDefinitions() {
    return api('/api/adapter-definitions').then(r => unwrapList(r, 'definitions'));
  },

  async getAdapterInstances() {
    return api('/api/adapter-instances').then(r => unwrapList(r, 'instances'));
  },

  async createAdapterInstance(payload) {
    return api('/api/adapter-instances', { method: 'POST', body: JSON.stringify(payload) });
  },

  async updateAdapterInstance(id, payload) {
    return api('/api/adapter-instances', { method: 'POST', body: JSON.stringify({ ...payload, id }) });
  },

  async deleteAdapterInstance(id) {
    return api(`/api/adapter-instances/${id}`, { method: 'DELETE' });
  },

  async testAdapterInstance(id) {
    return api(`/api/adapter-instances/${id}/test`, { method: 'POST' });
  },

  // Routes
  async getRoutes() {
    return api('/api/dashboard/routes').then(r => unwrapList(r, 'routes'));
  },

  async createRoute(payload) {
    return api('/routes', { method: 'POST', body: JSON.stringify(payload) });
  },

  async updateRoute(id, payload) {
    return api('/routes', { method: 'POST', body: JSON.stringify({ ...payload, id }) });
  },

  async deleteRoute(id) {
    return api(`/routes/${id}`, { method: 'DELETE' });
  },

  // Diagnostics and info
  async getOverview() {
    return api('/api/dashboard/overview');
  },

  async getDiagnostics() {
    return api('/api/dashboard/diagnostics');
  },

  async getHelpEntries() {
    return api('/api/help/entries').then(r => r.entries || []);
  },

  async getJobs() {
    return api('/api/dashboard/jobs').then(r => unwrapList(r, 'jobs'));
  },

  async getLogs(filters = {}) {
    const query = new URLSearchParams(filters);
    return api('/api/dashboard/diagnostics').then(r => r.global_logs || []);
  },

  async getPostStatus(filters = {}) {
    const query = new URLSearchParams(filters);
    return api(`/api/dashboard/message-links?${query}`).then(r => r || []);
  },

  async getMessageLinks(filters = {}) {
    const query = new URLSearchParams(filters);
    return api(`/api/dashboard/message-links?${query}`).then(r => unwrapList(r, 'links'));
  },

  // VK-specific
  async loadVkAdminGroups(instanceId) {
    return api(`/api/adapter-instances/${instanceId}/vk-admin-groups`)
      .then(r => r.groups || []);
  },

  async getVkAuthUrl(instanceId) {
    return api(`/api/adapter-instances/${instanceId}/vk-auth-url`)
      .then(r => r.auth_url || '');
  },

  async revokeVkToken(instanceId, tokenType = 'all') {
    return api(`/api/adapter-instances/${instanceId}/vk-revoke`, {
      method: 'POST',
      body: JSON.stringify({ token_type: tokenType }),
    });
  },

  // Generic fetch for legacy routes
  async fetch(url, opts = {}) {
    return api(url, opts);
  },
};

// Helper for showing messages
export function toast(msg) {
  const el = document.querySelector('#toast');
  if (el) {
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 3000);
  }
}
