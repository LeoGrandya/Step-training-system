/** 运行时必需（legacy iframe）。首页脚本。 */
(function () {
  function initHomeAnimation() {
    const container = document.getElementById('particles-container');
    if (container && container.children.length === 0) {
      for (let i = 0; i < 15; i++) {
        const p = document.createElement('div');
        p.className = 'particle-light';
        p.style.left = Math.random() * 100 + '%';
        p.style.top = Math.random() * 100 + '%';
        p.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(p);
      }
    }

    const statusLines = [1, 2, 3, 4];
    statusLines.forEach((num, index) => {
      const el = document.getElementById('status-' + num);
      if (el) {
        el.classList.remove('visible');
        setTimeout(() => {
          el.classList.add('visible');
        }, (index + 1) * 1200);
      }
    });
  }

  window.App.onReady/** 运行时必需（legacy iframe）。首页脚本。 */
(function () {
    document.documentElement.dataset.pageReady = 'home';
    initHomeAnimation();
  });
})();
