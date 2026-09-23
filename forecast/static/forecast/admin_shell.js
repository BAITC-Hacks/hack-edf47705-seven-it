(() => {
  const toggle = document.querySelector('.pro-menu-toggle');
  const sidebar = document.getElementById('pro-sidebar');
  const backdrop = document.querySelector('.pro-menu-backdrop');
  if (!toggle || !sidebar || !backdrop) return;
  document.body.classList.add('pro-menu-ready');
  toggle.hidden = false;
  function setOpen(open) {
    document.body.classList.toggle('pro-menu-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    backdrop.hidden = !open;
    if (open) sidebar.querySelector('a')?.focus();
  }
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  backdrop.addEventListener('click', () => { setOpen(false); toggle.focus(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { setOpen(false); toggle.focus(); }
  });
  const mobile = window.matchMedia('(max-width: 900px)');
  mobile.addEventListener('change', () => setOpen(false));
})();
