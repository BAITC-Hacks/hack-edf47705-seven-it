(() => {
  const input = document.querySelector('input[type="file"]');
  if (input) {
    input.addEventListener('change', () => {
      const file = input.files[0];
      document.getElementById('file-name').textContent = file ? file.name : 'Выберите Excel или CSV';
      input.closest('.file-picker').classList.toggle('has-file', Boolean(file));
    });
  }
  document.querySelectorAll('[data-loading-form]').forEach((form) => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      button.textContent = button.dataset.loadingText;
    });
  });
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) window.location.reload();
  });
  const error = document.querySelector('.has-error input, .has-error select');
  if (error) error.focus();
})();
