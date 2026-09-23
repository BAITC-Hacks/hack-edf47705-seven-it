(() => {
  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;
    const label = input.labels?.[0]?.textContent.trim() || 'Пароль';
    button.hidden = false;
    const conceal = () => {
      input.type = 'password';
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', 'Показать пароль: ' + label);
    };
    button.addEventListener('click', () => {
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.setAttribute('aria-pressed', String(show));
      button.setAttribute('aria-label', (show ? 'Скрыть пароль: ' : 'Показать пароль: ') + label);
    });
    input.form?.addEventListener('submit', conceal);
    window.addEventListener('pageshow', conceal);
  });
})();
