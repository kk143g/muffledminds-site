(function () {
  const frame = document.getElementById('ep-player');
  // Chapter and transcript timestamps seek the embedded player instead of leaving the page.
  if (frame) document.querySelectorAll('[data-seek]').forEach(a => {
    a.addEventListener('click', ev => {
      ev.preventDefault();
      const t = Number(a.dataset.seek);
      const send = (func, args) => frame.contentWindow.postMessage(JSON.stringify({ event: 'command', func, args }), '*');
      send('seekTo', [t, true]);
      send('playVideo', []);
      frame.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });

  // Section jump links: smooth scroll, and highlight the section being read.
  const links = Array.from(document.querySelectorAll('.ep-jump a'));
  if (!links.length) return;
  const targets = links.map(a => document.getElementById(a.getAttribute('href').slice(1)));
  links.forEach((a, i) => a.addEventListener('click', ev => {
    ev.preventDefault();
    targets[i].scrollIntoView({ behavior: 'smooth', block: 'start' });
    history.replaceState(null, '', '#' + targets[i].id);
  }));
  function spy() {
    const y = window.scrollY + 130;
    let cur = -1;
    targets.forEach((t, i) => { if (t.getBoundingClientRect().top + window.scrollY <= y) cur = i; });
    links.forEach((a, i) => a.classList.toggle('is-active', i === cur));
  }
  window.addEventListener('scroll', spy, { passive: true });
  spy();
})();
