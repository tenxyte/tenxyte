/* Tenxyte API Docs — script.js */
'use strict';
 
// ── Theme toggle ──────────────────────────────────────────────────────
const THEME_KEY = 'tenxyte-theme';
const root = document.documentElement;
const themeBtn = document.getElementById('themeToggle');
 
function applyTheme(theme) {
  root.setAttribute('data-theme', theme);
  if (themeBtn) themeBtn.querySelector('span').textContent = theme === 'dark' ? '☀️' : '🌙';
}
 
(function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const preferred = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(preferred);
})();
 
if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem(THEME_KEY, next);
  });
}
 
// ── Endpoint accordion ────────────────────────────────────────────────
document.querySelectorAll('.endpoint__header').forEach(btn => {
  btn.addEventListener('click', () => {
    const expanded = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!expanded));
    const body = document.getElementById(btn.getAttribute('aria-controls'));
    if (body) body.hidden = expanded;
  });
});
 
// ── Tabs ──────────────────────────────────────────────────────────────
document.querySelectorAll('.tabs').forEach(tablist => {
  tablist.querySelectorAll('.tabs__btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const panelId = btn.getAttribute('aria-controls');
      const group   = btn.closest('.tabs').parentElement;
 
      tablist.querySelectorAll('.tabs__btn').forEach(b => {
        b.classList.remove('tabs__btn--active');
        b.setAttribute('aria-selected', 'false');
      });
      group.querySelectorAll('.tabs__panel').forEach(p => {
        p.classList.remove('tabs__panel--active');
        p.hidden = true;
      });
 
      btn.classList.add('tabs__btn--active');
      btn.setAttribute('aria-selected', 'true');
      const panel = document.getElementById(panelId);
      if (panel) { panel.classList.add('tabs__panel--active'); panel.hidden = false; }
    });
  });
});
 
// ── Copy code ─────────────────────────────────────────────────────────
document.querySelectorAll('[data-copy]').forEach(btn => {
  btn.addEventListener('click', () => {
    const code = btn.closest('.code-block').querySelector('code');
    if (!code) return;
    navigator.clipboard.writeText(code.textContent).then(() => {
      btn.textContent = 'Copié !';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = 'Copier'; btn.classList.remove('copied'); }, 2000);
    }).catch(() => {});
  });
});
 
// ── Search ────────────────────────────────────────────────────────────
const searchInput   = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');
let searchData = null;
 
function loadSearchData() {
  if (searchData) return searchData;
  searchData = (typeof window.__SEARCH_DATA__ !== 'undefined' && window.__SEARCH_DATA__)
    ? window.__SEARCH_DATA__
    : { pages: [] };
  return searchData;
}
 
if (searchInput) {
  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase();
    if (!q) { searchResults.hidden = true; return; }
    const data = loadSearchData();
    const hits = data.pages.filter(p =>
      p.title.toLowerCase().includes(q) || p.content.toLowerCase().includes(q)
    ).slice(0, 8);
    if (!hits.length) { searchResults.hidden = true; return; }
    searchResults.innerHTML = hits.map(p =>
      `<a class="search__result" href="${p.url}">${p.title}</a>`
    ).join('');
    searchResults.hidden = false;
  });
 
  document.addEventListener('click', e => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target))
      searchResults.hidden = true;
  });
 
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault(); searchInput.focus();
    }
    if (e.key === 'Escape') { searchResults.hidden = true; searchInput.blur(); }
  });
}
 
// ── Smooth scroll for anchor links ────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  });
});
