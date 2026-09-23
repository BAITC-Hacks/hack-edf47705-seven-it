(() => {
  const key = 'foresell-theme';
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = null;
  const valid = (value) => value === 'light' || value === 'dark';
  try {
    const stored = window.localStorage.getItem(key);
    if (valid(stored)) preference = stored;
  } catch (_) { /* Themes still work when browser storage is unavailable. */ }

  function apply(theme) {
    root.dataset.theme = theme;
    document.querySelectorAll('[data-set-theme]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.setTheme === theme));
    });
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#0b0d10' : '#f7f8fa');
  }
  const preferred = () => preference || (system.matches ? 'dark' : 'light');
  apply(preferred());

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.theme-switch').forEach((control) => { control.hidden = false; });
    document.querySelectorAll('[data-set-theme]').forEach((button) => {
      button.addEventListener('click', () => {
        preference = button.dataset.setTheme;
        apply(preference);
        try { window.localStorage.setItem(key, preference); } catch (_) { /* Keep the selection for this page. */ }
      });
    });
    apply(preferred());
  });
  system.addEventListener('change', () => { if (!preference) apply(preferred()); });
  window.addEventListener('storage', (event) => {
    if (event.key !== key && event.key !== null) return;
    preference = valid(event.newValue) ? event.newValue : null;
    apply(preferred());
  });
  window.addEventListener('pageshow', () => {
    try {
      const stored = window.localStorage.getItem(key);
      preference = valid(stored) ? stored : null;
    } catch (_) { /* Preserve the in-memory preference. */ }
    apply(preferred());
  });
})();
