(() => {
  function reveal(target) {
    for (let node = target; node; node = node.parentElement) {
      if (node instanceof HTMLDetailsElement) node.open = true;
    }
  }
  function revealHash() {
    try {
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target) {
        reveal(target);
        requestAnimationFrame(() => target.scrollIntoView({ block: 'start' }));
      }
    } catch (_) { /* Ignore malformed fragments. */ }
  }
  document.addEventListener('click', (event) => {
    const anchor = event.target.closest('a[href^="#"]');
    if (anchor) {
      try { const target = document.getElementById(decodeURIComponent(anchor.hash.slice(1))); if (target) reveal(target); } catch (_) { /* Ignore invalid links. */ }
    }
    document.querySelectorAll('[data-popover][open]').forEach((menu) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    document.querySelectorAll('[data-popover][open]').forEach((menu) => {
      menu.open = false;
      menu.querySelector('summary').focus();
    });
  });
  document.addEventListener('invalid', (event) => reveal(event.target), true);
  window.addEventListener('hashchange', revealHash);
  if (location.hash) revealHash();
  const chat = document.querySelector('.chat-history');
  if (chat) chat.scrollTop = chat.scrollHeight;
  const buttons = new Map();
  document.querySelectorAll('form[data-busy]').forEach((form) => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('button[type="submit"]');
      if (!button) return;
      buttons.set(button, button.textContent);
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      button.textContent = form.dataset.busy;
    });
  });
  window.addEventListener('pageshow', () => {
    buttons.forEach((label, button) => {
      button.disabled = false;
      button.removeAttribute('aria-busy');
      button.textContent = label;
    });
    buttons.clear();
  });
})();
