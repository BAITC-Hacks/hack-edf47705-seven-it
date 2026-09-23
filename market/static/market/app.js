(() => {
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
