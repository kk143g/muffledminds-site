(function () {
  const root = document.getElementById('guest-carousel');
  if (!root) return;
  const data = JSON.parse(document.getElementById('gc-data').textContent);
  const pagesEl = root.querySelector('.gc-pages');
  const dotsEl = root.querySelector('.gc-dots');
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const OV = 0.02;
  let pages = [], current = 0, bucket = null;

  const perPage = () => (window.innerWidth >= 1100 ? 6 : window.innerWidth >= 760 ? 4 : 2);

  function figure(p, side, rank) {
    const f = document.createElement('figure');
    f.className = 'gc-person gc-' + side;
    f.tabIndex = 0;
    f.setAttribute('role', 'group');
    f.setAttribute('aria-label', p.name);
    f.style.setProperty('--il', p.il);
    f.style.setProperty('--ir', p.ir);
    f.style.setProperty('--wl', p.wl);
    f.style.setProperty('--z', 20 - rank);
    f.innerHTML =
      '<div class="gc-figure">' +
        '<img class="gc-reflect" data-src="assets/guests/' + (p.idleImg || p.img + '-idle') + '.webp" alt="" aria-hidden="true">' +
        '<img class="gc-idle" data-src="assets/guests/' + (p.idleImg || p.img + '-idle') + '.webp" alt="' + esc(p.name + ', ' + p.role) + '" width="558" height="900">' +
        '<img class="gc-wave" data-src="assets/guests/' + p.img + '-wave.webp" alt="" aria-hidden="true" width="558" height="900">' +
        '<span class="gc-hit"></span><span class="gc-arm"></span>' +
      '</div>' +
      '<figcaption class="gc-card">' +
        '<strong class="gc-name">' + esc(p.name) + '</strong>' +
        '<span class="gc-role">' + esc(p.role) + '</span>' +
        '<a class="gc-play" href="' + esc(p.url) + '" target="_blank" rel="noopener"><i class="fa-solid fa-play"></i> ' + esc(p.label) + '</a>' +
      '</figcaption>';
    return f;
  }

  function build() {
    const per = perPage();
    const chunks = [];
    for (let i = 0; i < data.guests.length; i += per) chunks.push(data.guests.slice(i, i + per));
    pagesEl.innerHTML = '';
    pages = chunks.map((chunk, pageIndex) => {
      const left = chunk.filter((_, i) => i % 2 === 0);
      const right = chunk.filter((_, i) => i % 2 === 1);
      const page = document.createElement('div');
      page.className = 'gc-page';
      left.slice().reverse().forEach((g, i) => page.appendChild(figure(g, 'left', left.length - i)));
      const hostPose = data.hostPoses ? data.hostPoses[pageIndex % data.hostPoses.length] : {};
      page.appendChild(figure(Object.assign({}, data.host, hostPose), 'host', 0));
      right.forEach((g, i) => page.appendChild(figure(g, 'right', i + 1)));
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
    dotsEl.style.display = pages.length > 1 && pages.length <= 6 ? '' : 'none';
    if (current >= pages.length) current = 0;
    fit();
    show(current);
  }

  function centerHost() {
    const box = pagesEl.getBoundingClientRect();
    pages.forEach(page => {
      page.style.transform = 'none';
      const hit = page.querySelector('.gc-host .gc-hit');
      if (!hit) return;
      const r = hit.getBoundingClientRect();
      const shift = (box.left + box.width / 2) - (r.left + r.width / 2);
      page.style.transform = 'translateX(' + Math.round(shift) + 'px)';
    });
  }

  function fit() {
    const n = Math.min(perPage(), data.guests.length) + 1;
    const all = data.guests.concat([data.host]);
    const body = all.reduce((s, p) => s + (1 - p.il - p.ir), 0) / all.length;
    const avail = pagesEl.clientWidth || window.innerWidth;
    const byWidth = avail / (n * (body - 2 * OV) * 0.62);
    const cap = window.innerWidth < 760 ? 300 : Math.min(580, window.innerHeight * 0.72);
    root.style.setProperty('--ph', Math.floor(Math.min(byWidth, cap)) + 'px');
    centerHost();
  }

  function load(page) {
    page.querySelectorAll('img[data-src]').forEach(img => { img.src = img.dataset.src; img.removeAttribute('data-src'); });
  }

  function show(i) {
    clearActive();
    current = (i + pages.length) % pages.length;
    pages.forEach((p, n) => p.classList.toggle('is-active', n === current));
    load(pages[current]);
    const next = pages[(current + 1) % pages.length];
    setTimeout(() => load(next), 600);
    [...dotsEl.children].forEach((d, n) => d.classList.toggle('is-on', n === current));
  }

  function clearActive() {
    root.querySelectorAll('.gc-person.is-active').forEach(p => p.classList.remove('is-active'));
  }

  function placeCard(person) {
    const card = person.querySelector('.gc-card');
    if (!card) return;
    card.style.setProperty('--shift', '0px');
    const r = card.getBoundingClientRect();
    const margin = 8;
    let shift = 0;
    if (r.left < margin) shift = margin - r.left;
    else if (r.right > window.innerWidth - margin) shift = window.innerWidth - margin - r.right;
    card.style.setProperty('--shift', Math.round(shift) + 'px');
  }

  root.addEventListener('mouseover', e => { const p = e.target.closest('.gc-person'); if (p) placeCard(p); });
  root.addEventListener('focusin', e => { const p = e.target.closest('.gc-person'); if (p) placeCard(p); });

  root.querySelector('.gc-prev').addEventListener('click', () => show(current - 1));
  root.querySelector('.gc-next').addEventListener('click', () => show(current + 1));

  const touchOnly = window.matchMedia('(hover: none)');
  root.addEventListener('click', e => {
    if (!touchOnly.matches) return;
    if (e.target.closest('.gc-play')) return;
    const person = e.target.closest('.gc-person');
    const wasActive = person && person.classList.contains('is-active');
    clearActive();
    if (person && !wasActive) { person.classList.add('is-active'); placeCard(person); }
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
