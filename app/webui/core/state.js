/**
 * Global application state
 */

export const state = {
  defs: [],
  instances: [],
  routes: [],
  overview: {},
  jobs: [],
  links: [],
  diagnostics: {},
  helpEntries: [],
  expandedRouteId: null,

  // VK-specific state
  vkAdminGroups: {},
  vkAdminGroupsLoading: {},
  vkAdminGroupsSelected: {},
};

// State subscribers
const listeners = new Set();

export function subscribe(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

export function notifyListeners() {
  listeners.forEach(cb => cb(state));
}

export function updateState(updates) {
  Object.assign(state, updates);
  notifyListeners();
}

export function resetState() {
  state.defs = [];
  state.instances = [];
  state.routes = [];
  state.overview = {};
  state.jobs = [];
  state.links = [];
  state.diagnostics = {};
  state.helpEntries = [];
  state.expandedRouteId = null;
  state.vkAdminGroups = {};
  state.vkAdminGroupsLoading = {};
  state.vkAdminGroupsSelected = {};
  notifyListeners();
}
