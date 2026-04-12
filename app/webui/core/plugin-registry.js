/**
 * Plugin registry - loads adapter plugins and manages their lifecycle
 */

const pluginCache = new Map();
const templateCache = new Map();
const loadedStyles = new Set();

function resolveAssetExtensionPoint(extensionPoint) {
  if (extensionPoint === 'instanceConfig') return 'instance';
  if (extensionPoint === 'routeConfig') return 'route';
  return extensionPoint;
}

function assetUrl(adapterKey, extensionPoint, filename) {
  const resolvedExtensionPoint = resolveAssetExtensionPoint(extensionPoint);
  return new URL(`../adapters/${adapterKey}/${resolvedExtensionPoint}/${filename}`, import.meta.url);
}

export const pluginRegistry = {
  /**
   * Load adapter plugin module
   */
  async loadPlugin(adapterKey) {
    if (pluginCache.has(adapterKey)) {
      return pluginCache.get(adapterKey);
    }

    try {
      const module = await import(new URL(`../adapters/${adapterKey}/plugin.js`, import.meta.url).toString());
      const plugin = module.default;
      pluginCache.set(adapterKey, plugin);
      return plugin;
    } catch (e) {
      console.error(`Failed to load plugin for ${adapterKey}:`, e);
      throw e;
    }
  },

  /**
   * Load HTML template for extension point
   */
  async loadTemplate(adapterKey, extensionPoint) {
    const cacheKey = `${adapterKey}:${extensionPoint}`;
    if (templateCache.has(cacheKey)) {
      return templateCache.get(cacheKey);
    }

    try {
      const response = await fetch(assetUrl(adapterKey, extensionPoint, 'template.html'));
      if (!response.ok) {
        console.warn(`Template not found: ${cacheKey}`);
        return '';
      }
      const html = await response.text();
      templateCache.set(cacheKey, html);
      return html;
    } catch (e) {
      console.warn(`Failed to load template for ${cacheKey}:`, e);
      return '';
    }
  },

  /**
   * Load and inject CSS for adapter plugin
   */
  async loadStyle(adapterKey, extensionPoint = 'instance') {
    const styleKey = `${adapterKey}:${extensionPoint}`;
    if (loadedStyles.has(styleKey)) {
      return;
    }

    try {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = assetUrl(adapterKey, extensionPoint, 'style.css').toString();
      link.onerror = () => {
        console.warn(`Style not found: ${styleKey}`);
        loadedStyles.add(styleKey);
      };
      link.onload = () => {
        loadedStyles.add(styleKey);
      };
      document.head.appendChild(link);
    } catch (e) {
      console.warn(`Failed to load style for ${styleKey}:`, e);
    }
  },

  /**
   * Check if adapter supports extension point
   */
  async supportsExtensionPoint(adapterKey, extensionPoint) {
    const plugin = await this.loadPlugin(adapterKey);
    if (!plugin.supports) return false;
    return Boolean(plugin.supports[extensionPoint]);
  },

  /**
   * Mount adapter extension at container
   */
  async mount(container, adapterKey, extensionPoint, ctx) {
    if (!container) {
      throw new Error(`Container not provided for ${adapterKey}:${extensionPoint}`);
    }

    const plugin = await this.loadPlugin(adapterKey);
    const mountFn = plugin[`mount${capitalize(extensionPoint)}`];

    if (!mountFn) {
      console.warn(`Plugin ${adapterKey} does not support ${extensionPoint}`);
      return null;
    }

    // Load template and styles
    const template = await this.loadTemplate(adapterKey, extensionPoint);
    await this.loadStyle(adapterKey, extensionPoint);

    // Prepare context with template loader
    const fullCtx = {
      ...ctx,
      template,
      templateLoader: {
        loadTemplate: (path) => this.loadTemplate(adapterKey, path),
      },
    };

    // Mount and return controller
    try {
      const controller = await mountFn.call(plugin, fullCtx);
      return controller;
    } catch (e) {
      console.error(`Error mounting ${adapterKey}:${extensionPoint}:`, e);
      throw e;
    }
  },
};

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
