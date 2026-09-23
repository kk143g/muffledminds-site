const toggle = document.querySelector('.menu-toggle');
const links = document.querySelector('.nav-links');
if (toggle && links) {
  toggle.addEventListener('click', () => links.classList.toggle('open'));
  links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));
}

const io = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.style.opacity = 1;
      e.target.style.transform = 'translateY(0)';
      io.unobserve(e.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll('.pillar, .ep-card, .guest-item, .social-card').forEach(el => {
  el.style.opacity = 0;
  el.style.transform = 'translateY(16px)';
  el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  io.observe(el);
});

document.querySelector('.year').textContent = new Date().getFullYear();
