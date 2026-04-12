/**
 * Store for mounted instance config controllers
 */

const controllers = new Map();

export const instanceStore = {
  mount(instanceId, controller, metadata = {}) {
    controllers.set(instanceId, {
      controller,
      ...metadata,
    });
  },

  get(instanceId) {
    return controllers.get(instanceId);
  },

  getAll() {
    return Array.from(controllers.entries()).map(([id, data]) => ({
      instanceId: id,
      ...data,
    }));
  },

  unmount(instanceId) {
    const entry = controllers.get(instanceId);
    if (entry) {
      try {
        entry.controller.cleanup?.();
      } catch (e) {
        console.error(`Error cleaning up controller for ${instanceId}:`, e);
      }
      controllers.delete(instanceId);
    }
  },

  unmountAll() {
    for (const [instanceId] of controllers) {
      this.unmount(instanceId);
    }
  },

  async extractFormData(instanceId) {
    const entry = controllers.get(instanceId);
    if (!entry) return null;
    return entry.controller.extractFormData?.() || null;
  },

  async validate(instanceId) {
    const entry = controllers.get(instanceId);
    if (!entry) return { valid: true, errors: [] };
    return entry.controller.validate?.() || { valid: true, errors: [] };
  },

  setErrors(instanceId, errors) {
    const entry = controllers.get(instanceId);
    if (entry?.controller.setErrors) {
      entry.controller.setErrors(errors);
    }
  },
};
