(() => {
  function initialize() {
    document.querySelectorAll('[data-permission-picker]').forEach((picker) => {
      const search = picker.querySelector('[data-permission-search]');
      const cards = [...picker.querySelectorAll('[data-permission-card]')];
      const inputs = [...picker.querySelectorAll('input[type="checkbox"]')];
      const update = () => {
        picker.querySelector('[data-permission-count]').textContent =
          `Выбрано прав: ${inputs.filter((input) => input.checked).length} из ${inputs.length}`;
      };
      picker.querySelector('.permission-toolbar').hidden = false;
      search.addEventListener('input', () => {
        const query = search.value.trim().toLocaleLowerCase('ru');
        cards.forEach((card) => { card.hidden = !card.textContent.toLocaleLowerCase('ru').includes(query); });
        picker.querySelector('[data-permission-empty]').hidden = cards.some((card) => !card.hidden);
      });
      picker.addEventListener('change', update);
      // Filtering never disables inputs: hidden selections are still submitted.
      picker.closest('form')?.addEventListener('reset', () => setTimeout(update, 0));
      update();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
  else initialize();
})();
