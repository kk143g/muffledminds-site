(function () {
  const STEP = 9;
  const tabs = Array.from(document.querySelectorAll('.ep-tab'));
  const panels = Array.from(document.querySelectorAll('.ep-panel'));
  if (!tabs.length) return;

  function sync(panel) {
    const cards = Array.from(panel.querySelectorAll('.ep-card'));
    const shown = Number(panel.dataset.shown || STEP);
    cards.forEach((c, i) => { c.hidden = i >= shown; });
    panel.querySelector('.ep-more-wrap').hidden = shown >= cards.length;
  }

  function select(key, updateHash) {
    tabs.forEach(t => {
      const on = t.dataset.tab === key;
      t.classList.toggle('is-active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    panels.forEach(p => { p.hidden = p.dataset.panel !== key; });
    if (updateHash) history.replaceState(null, '', key === tabs[0].dataset.tab ? location.pathname : '#' + key);
  }

  panels.forEach(p => {
    sync(p);
    p.querySelector('.ep-more').addEventListener('click', () => {
      p.dataset.shown = Number(p.dataset.shown || STEP) + STEP;
      sync(p);
    });
  });
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => select(t.dataset.tab, true));
    t.addEventListener('keydown', e => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!d) return;
      const n = tabs[(i + d + tabs.length) % tabs.length];
      n.focus(); select(n.dataset.tab, true);
    });
  });
  const want = location.hash.slice(1);
  if (tabs.some(t => t.dataset.tab === want)) select(want, false);
})();
