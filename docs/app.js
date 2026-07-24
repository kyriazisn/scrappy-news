const listEl = document.getElementById("news-list");
const searchEl = document.getElementById("search");
const metaEl = document.getElementById("meta");
const updatedEl = document.getElementById("updated-at");
const countEl = document.getElementById("article-count");

let allArticles = [];

function formatDate(value) {
  if (!value) return "Χωρίς ημερομηνία";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("el-GR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function render(items) {
  countEl.textContent = allArticles.length;
  metaEl.textContent = `Εμφανίζονται ${items.length} από ${allArticles.length} άρθρα`;

  if (!items.length) {
    listEl.innerHTML = `<li class="empty-state">Δεν βρέθηκαν άρθρα για αυτό το φίλτρο.</li>`;
    return;
  }

  listEl.innerHTML = items.map(article => {
    const title = escapeHtml(article.title || "Χωρίς τίτλο");
    const source = escapeHtml(article.source || "Άγνωστη πηγή");
    const keyword = escapeHtml(article.keyword || "-");
    const published = escapeHtml(formatDate(article.published));
    const url = article.url || "#";
    const safeUrl = /^https?:\/\//i.test(url) ? url : "#";
    const displayUrl = escapeHtml(safeUrl === "#" ? "Μη διαθέσιμο link" : url);

    return `
      <li class="news-item">
        <a class="news-link" href="${safeUrl}" target="_blank" rel="noopener noreferrer">
          <div class="news-chips">
            <span class="chip source">${source}</span>
            <span class="chip keyword">${keyword}</span>
            <span class="chip">${published}</span>
          </div>
          <h3 class="news-title">${title}</h3>
          <div class="news-url">${displayUrl}</div>
        </a>
      </li>
    `;
  }).join("");
}

function applyFilter() {
  const q = searchEl.value.trim().toLowerCase();
  if (!q) {
    render(allArticles);
    return;
  }

  const filtered = allArticles.filter(article => {
    return [article.title, article.source, article.keyword]
      .filter(Boolean)
      .some(value => value.toLowerCase().includes(q));
  });

  render(filtered);
}

async function init() {
  try {
    const res = await fetch("./articles.json", { cache: "no-store" });
    const data = await res.json();

    allArticles = Array.isArray(data.articles) ? data.articles : [];
    updatedEl.textContent = formatDate(data.updated_at);
    countEl.textContent = String(allArticles.length);

    render(allArticles);
  } catch (err) {
    metaEl.textContent = "Σφάλμα φόρτωσης δεδομένων.";
    listEl.innerHTML = `<li class="empty-state">Δεν ήταν δυνατή η φόρτωση των άρθρων.</li>`;
  }
}

searchEl.addEventListener("input", applyFilter);
init();