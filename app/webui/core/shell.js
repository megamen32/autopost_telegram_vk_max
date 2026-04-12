/**
 * Shell coordination - tab switching, container management
 */

export const shell = {
  /**
   * Initialize shell UI interactions
   */
  init() {
    const tabs = document.querySelectorAll('.tabs button');
    const tabSections = document.querySelectorAll('.tab');

    tabs.forEach(button => {
      button.addEventListener('click', () => {
        // Deactivate all tabs and buttons
        tabs.forEach(b => b.classList.remove('active'));
        tabSections.forEach(t => t.classList.remove('active'));

        // Activate selected
        button.classList.add('active');
        const tabName = button.dataset.tab;
        const tabEl = document.getElementById(`tab-${tabName}`);
        if (tabEl) {
          tabEl.classList.add('active');
        }
      });
    });
  },

  /**
   * Show a specific tab
   */
  showTab(tabName) {
    const button = document.querySelector(`.tabs button[data-tab="${tabName}"]`);
    if (button) {
      button.click();
    }
  },

  /**
   * Get container for a tab section
   */
  getContainer(tabName, sectionName = null) {
    const tab = document.getElementById(`tab-${tabName}`);
    if (!tab) return null;

    if (sectionName) {
      return tab.querySelector(`#${sectionName}`);
    }
    return tab;
  },

  /**
   * Clear container contents
   */
  clearContainer(container) {
    if (container) {
      container.innerHTML = '';
    }
  },
};
