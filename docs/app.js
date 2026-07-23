async function loadNews() {
  const res = await fetch('../data/articles.json');
  const data = await res.json();

  const meta = document.getElementById('meta');
  meta.textContent = `Τελευταία ενημέρωση: ${data.updated_at} | Άρθρα: ${data.count}`;

  const list = document.getElementById('news-list');
  const search = document.getElementById('search');

  function render(items) {
    list.innerHTML = '';
    for (const item of items) {
      const li = document.createElement('li');
      li.className = 'news-item';
      li.innerHTML = `
        <a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.title}</a>
        <div class="meta">${item.source} ${item.published ? '• ' + item.published : ''}</div>
      `;
      list.appendChild(li);
    }
  }

  render(data.articles);

  search.addEventListener('input', () => {
    const q = search.value.toLowerCase().trim();
    const filtered = data.articles.filter(x =>
      x.title.toLowerCase().includes(q) ||
      x.source.toLowerCase().includes(q)
    );
    render(filtered);
  });
}

loadNews().catch(err => {
  document.getElementById('meta').textContent = 'Σφάλμα φόρτωσης δεδομένων';
  console.error(err);
});