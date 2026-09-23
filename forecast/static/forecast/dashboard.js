(() => {
  const data = JSON.parse(document.getElementById('chart-data').textContent);
  const chart = document.getElementById('demand-chart');
  const select = document.getElementById('category-select');
  const rows = Array.from(document.querySelectorAll('tbody tr[data-category]'));
  const facts = new Map(rows.map((row) => {
    const cells = row.querySelectorAll('td');
    return [row.dataset.category, {
      trend: cells[1].textContent.trim().replace(/\s+/g, ' '),
      forecast: cells[2].textContent.trim(),
      yoy: cells[3].textContent.trim(),
      orderBy: cells[5].textContent.trim(),
    }];
  }));
  const months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  const format = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
  const monthLabel = (value) => {
    const [year, month] = value.split('-');
    return months[Number(month) - 1] + ' ' + year.slice(2);
  };
  function svgElement(name, attrs = {}, text = '') {
    const element = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
    if (text) element.textContent = text;
    return element;
  }
  function render(category) {
    const series = data[category];
    if (!series || !facts.has(category)) return;
    select.value = category;
    rows.forEach((row) => {
      const selected = row.dataset.category === category;
      row.classList.toggle('selected', selected);
      row.querySelector('button').setAttribute('aria-pressed', String(selected));
    });
    document.getElementById('chart-current').textContent = category;
    const currentFacts = facts.get(category);
    const factContainer = document.getElementById('chart-facts');
    factContainer.replaceChildren();
    [['Изменение спроса', currentFacts.trend], ['Прогноз на 3 месяца', currentFacts.forecast], ['К прошлому году', currentFacts.yoy], ['Готовиться до', currentFacts.orderBy]].forEach(([label, value]) => {
      const cell = document.createElement('div');
      const title = document.createElement('span');
      const number = document.createElement('strong');
      title.textContent = label;
      number.textContent = value;
      cell.append(title, number);
      factContainer.append(cell);
    });
    chart.replaceChildren();
    chart.append(svgElement('title', { id: 'chart-title' }, category + ': история и прогноз спроса'));
    chart.append(svgElement('desc', { id: 'chart-description' }, 'Сплошная линия — история, пунктир — прогноз. Прогноз на три месяца: ' + currentFacts.forecast + '. Тренд: ' + currentFacts.trend));
    const points = series.history.concat(series.forecast);
    if (!points.length) return;
    const maxValue = Math.max(1, ...points.map((point) => point[1]));
    const magnitude = Math.pow(10, Math.floor(Math.log10(maxValue / 4)));
    const interval = Math.ceil(maxValue / 4 / magnitude) * magnitude;
    const ceiling = interval * 4;
    const left = 64, right = 932, top = 24, bottom = 235;
    const x = (index) => left + index / Math.max(1, points.length - 1) * (right - left);
    const y = (value) => bottom - value / ceiling * (bottom - top);
    const historyEnd = series.history.length - 1;
    if (series.forecast.length) {
      const boundary = historyEnd >= 0 ? (x(historyEnd) + x(historyEnd + 1)) / 2 : left;
      chart.append(svgElement('rect', { x: boundary, y: top, width: right - boundary, height: bottom - top, rx: 6, class: 'chart-forecast-area' }));
    }
    for (let tick = 0; tick <= 4; tick++) {
      const value = interval * tick;
      chart.append(svgElement('line', { x1: left, x2: right, y1: y(value), y2: y(value), class: 'chart-grid' }));
      chart.append(svgElement('text', { x: left - 12, y: y(value) + 4, 'text-anchor': 'end', class: 'chart-label' }, format.format(value)));
    }
    const labelStep = Math.max(1, Math.ceil((points.length - 1) / 7));
    points.forEach(([month], index) => {
      if ((index % labelStep === 0 && index < points.length - 1 - labelStep / 2) || index === points.length - 1) {
        chart.append(svgElement('text', { x: x(index), y: bottom + 27, 'text-anchor': index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle', class: 'chart-label' }, monthLabel(month)));
      }
    });
    const linePath = (list, offset) => list.map((point, index) => (index ? 'L' : 'M') + x(index + offset) + ',' + y(point[1])).join(' ');
    if (series.history.length) {
      const path = linePath(series.history, 0);
      chart.append(svgElement('path', { d: path + ' L' + x(historyEnd) + ',' + bottom + ' L' + left + ',' + bottom + ' Z', class: 'chart-history-area', opacity: '.6' }));
      chart.append(svgElement('path', { d: path, class: 'chart-line' }));
    }
    if (series.forecast.length) {
      const future = historyEnd >= 0 ? [series.history[historyEnd]].concat(series.forecast) : series.forecast;
      chart.append(svgElement('path', { d: linePath(future, Math.max(0, historyEnd)), class: 'chart-line forecast-line' }));
    }
    points.forEach(([month, value], index) => {
      const point = svgElement('circle', { cx: x(index), cy: y(value), r: index > historyEnd ? 4 : 3, class: 'chart-point' });
      point.append(svgElement('title', {}, monthLabel(month) + ': ' + format.format(value) + (index > historyEnd ? ' (прогноз)' : '')));
      chart.append(point);
    });
  }
  select.addEventListener('change', () => render(select.value));
  rows.forEach((row) => row.addEventListener('click', () => {
    render(row.dataset.category);
    document.getElementById('forecast').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  }));
  if (rows.length) render(rows[0].dataset.category);
  const form = document.getElementById('ai-form');
  const button = document.getElementById('ai-button');
  const originalButton = button.innerHTML;
  form.addEventListener('submit', () => {
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.textContent = 'Анализируем данные… до минуты';
  });
  window.addEventListener('pageshow', () => {
    button.disabled = false;
    button.removeAttribute('aria-busy');
    button.innerHTML = originalButton;
  });
})();
