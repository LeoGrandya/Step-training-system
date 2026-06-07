(function () {
  if (new URLSearchParams(window.location.search).get('embedded') === '1') {
    document.documentElement.dataset.embedded = '1';
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function onReady(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback, { once: true });
      return;
    }
    callback();
  }

  function ensureToastHost() {
    let host = qs('#toastHost');
    if (!host) {
      host = document.createElement('div');
      host.id = 'toastHost';
      host.className = 'toast-host';
      document.body.appendChild(host);
    }
    return host;
  }

  function showToast(message, type) {
    const host = ensureToastHost();
    const toast = document.createElement('div');
    toast.className = 'toast-item ' + (type || 'info');
    toast.textContent = message;
    host.appendChild(toast);
    window.setTimeout(function () {
      toast.remove();
    }, 3000);
  }

  window.App = {
    qs: qs,
    qsa: qsa,
    onReady: onReady,
    showToast: showToast
  };
})();
