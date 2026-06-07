(function () {
  window.App.onReady(function () {
    document.documentElement.dataset.pageReady = 'product';

    const container = document.getElementById('hero-particles');
    if (container) {
      for (let i = 0; i < 15; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.top = Math.random() * 100 + '%';
        p.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(p);
      }
    }

    const reveals = document.querySelectorAll('.reveal');
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -50px 0px' });

    reveals.forEach((el, i) => {
      el.style.transitionDelay = (i % 3) * 0.1 + 's';
      observer.observe(el);
    });

    setTimeout(() => {
      document.querySelectorAll('.reveal').forEach((el, i) => {
        if (i < 4) el.classList.add('visible');
      });
    }, 200);
  });
})();
