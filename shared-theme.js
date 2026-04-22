// Shared theme module — single source of truth for light/dark mode
(function () {
  'use strict';

  const html = document.documentElement;
  const STORAGE_KEY = 'theme';
  const STORAGE_MANUAL = 'theme_manual';

  function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function getIcon(theme) {
    return theme === 'light' ? '\u2600\uFE0F' : '\uD83C\uDF19'; // ☀️ / 🌙
  }

  function applyTheme(theme, persist) {
    const isLight = theme === 'light';
    html.classList.toggle('light-mode', isLight);

    // Update all theme icons on the page
    document.querySelectorAll('#theme-icon').forEach(function (el) {
      el.textContent = getIcon(theme);
    });

    // Fix dashboard logo
    var logo = document.getElementById('sb-img');
    if (logo) {
      logo.style.filter = isLight
        ? 'invert(1) hue-rotate(180deg) brightness(.75)'
        : 'none';
    }

    // Dispatch custom event for listeners
    window.dispatchEvent(new CustomEvent('gn-theme-changed', { detail: { theme: theme } }));

    if (persist) {
      localStorage.setItem(STORAGE_KEY, theme);
      localStorage.setItem(STORAGE_MANUAL, '1');
    }
  }

  function init() {
    var saved = localStorage.getItem(STORAGE_KEY);
    var manual = localStorage.getItem(STORAGE_MANUAL) === '1';
    var theme = (manual && (saved === 'light' || saved === 'dark'))
      ? saved
      : getSystemTheme();
    applyTheme(theme, false);
  }

  function toggle() {
    var current = html.classList.contains('light-mode') ? 'light' : 'dark';
    var next = current === 'light' ? 'dark' : 'light';
    applyTheme(next, true);
  }

  // Expose globals
  window.GnTheme = { init: init, toggle: toggle, apply: applyTheme, getIcon: getIcon };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
