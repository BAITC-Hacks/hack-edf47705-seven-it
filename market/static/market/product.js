(() => {
  const chart = document.getElementById('price-chart');
  if (!chart) return;
  const data = JSON.parse(document.getElementById('product-chart-data').textContent);
  if (!data.prices.length) return;
  const element = (name, attrs, text = '') => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text) node.textContent = text;
    return node;
  };
  const max = Math.max(...data.prices) * 1.05;
  const fmt = new Intl.NumberFormat('ru-RU', { notation: 'compact', maximumFractionDigits: 1 });
  const dates = data.dates.map(value => Date.parse(value + 'T00:00:00Z'));
  const span = Math.max(1, dates[dates.length - 1] - dates[0]);
  const x = (i) => 75 + (dates[i] - dates[0]) / span * 850;
  const y = (value) => 230 - value / max * 205;
  chart.append(element('title', {}, 'История цены в тенге'));
  for (let i = 0; i <= 4; i++) {
    const value = max * i / 4;
    chart.append(element('line', { x1: 75, x2: 925, y1: y(value), y2: y(value), class: 'chart-grid' }));
    chart.append(element('text', { x: 62, y: y(value) + 4, class: 'chart-label', 'text-anchor': 'end' }, fmt.format(value)));
  }
  chart.append(element('path', { d: data.prices.map((value, i) => (i ? 'L' : 'M') + x(i) + ',' + y(value)).join(' '), class: 'product-chart-line' }));
  data.prices.forEach((value, i) => {
    const dot = element('circle', { cx: x(i), cy: y(value), r: 3, class: 'chart-point' });
    dot.append(element('title', {}, data.dates[i] + ': ' + value.toLocaleString('ru-RU') + ' ₸'));
    chart.append(dot);
    if (i === 0 || i === data.prices.length - 1) chart.append(element('text', { x: x(i), y: 258, class: 'chart-label', 'text-anchor': i === 0 ? 'start' : 'end' }, data.dates[i]));
  });
})();
