(function () {
  const items = [
    { href: 'home.html', label: '首页' },
    { href: 'product.html', label: '产品介绍' },
    { href: '/#/training', label: '训练模式', top: true },
    { href: '/#/analysis', label: '视频上传分析', top: true, activeFor: ['upload.html'] },
    { href: 'team.html', label: '团队介绍' },
    { href: '/#/auth', label: '登录/注册', auth: true, top: true }
  ];

  function currentPage() {
    const name = window.location.pathname.split('/').pop();
    return name || 'home.html';
  }

  function isActive(item, page) {
    return item.href === page || (item.activeFor || []).includes(page);
  }

  function renderNav() {
    const mount = document.getElementById('site-nav');
    if (!mount) return;

    const page = currentPage();
    const links = items.map(function (item) {
      const classes = ['site-nav__link'];
      if (item.auth) classes.push('site-nav__auth');
      if (isActive(item, page)) classes.push('is-active');
      const target = item.top ? ' target="_top"' : '';
      return '<a href="' + item.href + '" class="' + classes.join(' ') + '"' + target + '>' + item.label + '</a>';
    }).join('');

    mount.innerHTML =
      '<nav class="site-nav">' +
        '<div class="site-nav__brand">' +
          '<div class="site-nav__mark"></div>' +
          '<span class="site-nav__name">AI-Sport Lab</span>' +
        '</div>' +
        '<div class="site-nav__links">' + links + '</div>' +
      '</nav>';
  }

  window.App.onReady(renderNav);
})();
