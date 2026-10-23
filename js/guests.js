(function () {
  const root = document.getElementById('guest-carousel');
  if (!root) return;
  const pagesEl = root.querySelector('.gc-pages');
  const dotsEl = root.querySelector('.gc-dots');
  const people = [...pagesEl.querySelectorAll('.gc-person')].map(p => p.cloneNode(true));
  const host = people.find(p => p.hasAttribute('data-host'));
  const guests = people.filter(p => p !== host);
  let pages = [], current = 0, bucket = null;

  const perPage = () => (window.innerWidth >= 1100 ? 7 : window.innerWidth >= 760 ? 5 : 3);

  function fit() {
    const n = Math.min(perPage(), guests.length + 1);
    const avail = pagesEl.clientWidth || window.innerWidth;
    const byWidth = avail / (0.535 * n + 0.09);
    const cap = window.innerWidth < 760 ? 300 : Math.min(560, window.innerHeight * 0.7);
    root.style.setProperty('--ph', Math.floor(Math.min(byWidth, cap)) + 'px');
  }

  function build() {
    fit();
    const per = perPage() - 1;
    const chunks = [];
    for (let i = 0; i < guests.length; i += per) chunks.push(guests.slice(i, i + per));
    if (!chunks.length) chunks.push([]);
    pagesEl.innerHTML = '';
    pages = chunks.map(chunk => {
      const page = document.createElement('div');
      page.className = 'gc-page';
      const left = Math.ceil(chunk.length / 2);
      chunk.slice(0, left).forEach(g => page.appendChild(g.cloneNode(true)));
      if (host) page.appendChild(host.cloneNode(true));
      chunk.slice(left).forEach(g => page.appendChild(g.cloneNode(true)));
      pagesEl.appendChild(page);
      return page;
    });
    dotsEl.innerHTML = '';
    pages.forEach((_, i) => {
      const d = document.createElement('button');
      d.type = 'button'; d.className = 'gc-dot'; d.setAttribute('aria-label', 'Page ' + (i + 1));
      d.addEventListener('click', () => show(i));
      dotsEl.appendChild(d);
    });
    dotsEl.style.display = pages.length > 1 ? '' : 'none';
    if (current >= pages.length) current = 0;
    show(current);
  }

  function show(i) {
    clearActive();
    current = (i + pages.length) % pages.length;
    pages.forEach((p, n) => p.classList.toggle('is-active', n === current));
    [...dotsEl.children].forEach((d, n) => d.classList.toggle('is-on', n === current));
  }

  function clearActive() {
    root.querySelectorAll('.gc-person.is-active').forEach(p => p.classList.remove('is-active'));
  }

  root.querySelector('.gc-prev').addEventListener('click', () => show(current - 1));
  root.querySelector('.gc-next').addEventListener('click', () => show(current + 1));

  const touchOnly = window.matchMedia('(hover: none)');
  root.addEventListener('click', e => {
    if (!touchOnly.matches) return;
    if (e.target.closest('.gc-play')) return;
    const person = e.target.closest('.gc-person');
    const wasActive = person && person.classList.contains('is-active');
    clearActive();
    if (person && !wasActive) person.classList.add('is-active');
  });
  document.addEventListener('click', e => { if (!root.contains(e.target)) clearActive(); });

  let sx = null;
  root.addEventListener('touchstart', e => { sx = e.touches[0].clientX; }, { passive: true });
  root.addEventListener('touchend', e => {
    if (sx === null) return;
    const dx = e.changedTouches[0].clientX - sx; sx = null;
    if (Math.abs(dx) > 60) show(current + (dx < 0 ? 1 : -1));
  });

  window.addEventListener('resize', () => {
    const b = perPage();
    if (b !== bucket) { bucket = b; build(); } else { fit(); }
  });
  bucket = perPage();
  build();
})();
