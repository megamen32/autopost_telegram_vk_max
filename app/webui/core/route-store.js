/**
 * Store for mounted route config controllers
 */

const controllers = new Map();

export const routeStore = {
  mount(routeId, entry) {
    const mounted = {};
    if (entry?.shared) mounted.shared = entry.shared;
    if (entry?.source) mounted.source = entry.source;
    if (entry?.target) mounted.target = entry.target;
    controllers.set(routeId, mounted);
  },

  get(routeId) {
    return controllers.get(routeId);
  },

  getAll() {
    return Array.from(controllers.entries()).map(([id, data]) => ({
      routeId: id,
      ...data,
    }));
  },

  unmount(routeId) {
    const entry = controllers.get(routeId);
    if (entry) {
      try {
        entry.shared?.cleanup?.();
        entry.source?.cleanup?.();
        entry.target?.cleanup?.();
      } catch (e) {
        console.error(`Error cleaning up route controller for ${routeId}:`, e);
      }
      controllers.delete(routeId);
    }
  },

  unmountAll() {
    for (const [routeId] of controllers) {
      this.unmount(routeId);
    }
  },

  async extractFormData(routeId) {
    const entry = controllers.get(routeId);
    if (!entry) return null;

    const data = {};
    if (entry.shared) {
      Object.assign(data, (await entry.shared.extractFormData?.()) || {});
    }
    if (entry.source) {
      const sourceData = await entry.source.extractFormData?.();
      if (sourceData) {
        data.source_adapter_config = sourceData;
      }
    }
    if (entry.target) {
      const targetData = await entry.target.extractFormData?.();
      if (targetData) {
        data.target_adapter_config = targetData;
      }
    }
    return data;
  },

  async validate(routeId) {
    const entry = controllers.get(routeId);
    if (!entry) return { valid: true, errors: [] };

    const errors = [];

    if (entry.shared) {
      const result = await entry.shared.validate?.();
      if (result?.errors) errors.push(...result.errors);
    }
    if (entry.source) {
      const result = await entry.source.validate?.();
      if (result?.errors) errors.push(...result.errors);
    }
    if (entry.target) {
      const result = await entry.target.validate?.();
      if (result?.errors) errors.push(...result.errors);
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  },

  setErrors(routeId, errors) {
    const entry = controllers.get(routeId);
    if (!entry) return;

    const sharedErrors = errors.filter(e => !e.adapter);
    const sourceErrors = errors.filter(e => e.adapter === 'source');
    const targetErrors = errors.filter(e => e.adapter === 'target');

    entry.shared?.setErrors?.(sharedErrors);
    entry.source?.setErrors?.(sourceErrors);
    entry.target?.setErrors?.(targetErrors);
  },
};
