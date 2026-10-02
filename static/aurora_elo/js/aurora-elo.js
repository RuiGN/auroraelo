/* Aurora Elo — comportamento do menu superior e do tema. Sem dependências.
   Liga-se sozinho a todo [data-ae-navbar] e [data-ae-theme-toggle] da página. */
(function () {
  'use strict';

  var COMPACT_MAX = 768; // mesmo limite do @container ae-navbar em aurora-elo.css

  function initNavbar(root) {
    if (!root || root.__aeNavbar) return;
    root.__aeNavbar = true;

    var toggle = root.querySelector('[data-ae-navbar-toggle]');
    var triggers = Array.prototype.slice.call(root.querySelectorAll('[data-ae-dropdown-trigger]'));

    function isCompact() { return root.getBoundingClientRect().width < COMPACT_MAX; }

    function setPanel(open) {
      root.classList.toggle('is-open', open);
      if (!toggle) return;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    }

    function setDropdown(trigger, open) { trigger.setAttribute('aria-expanded', String(open)); }

    function closeDropdowns(except) {
      triggers.forEach(function (t) { if (t !== except) setDropdown(t, false); });
    }

    if (toggle) {
      toggle.addEventListener('click', function () {
        var open = toggle.getAttribute('aria-expanded') !== 'true';
        setPanel(open);
        if (!open) closeDropdowns();
      });
    }

    triggers.forEach(function (t) {
      t.addEventListener('click', function () {
        var open = t.getAttribute('aria-expanded') !== 'true';
        // no desktop só um submenu aberto por vez; no mobile funcionam como sanfona
        if (!isCompact()) closeDropdowns(t);
        setDropdown(t, open);
      });
    });

    document.addEventListener('click', function (e) {
      if (root.contains(e.target)) return;
      if (!isCompact()) closeDropdowns();
      else if (root.classList.contains('is-open')) { setPanel(false); closeDropdowns(); }
    });

    root.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      var open = triggers.filter(function (t) { return t.getAttribute('aria-expanded') === 'true'; })[0];
      if (open && !isCompact()) { setDropdown(open, false); open.focus(); }
      else if (root.classList.contains('is-open')) { setPanel(false); closeDropdowns(); if (toggle) toggle.focus(); }
    });

    // voltando para a largura de desktop, fecha o painel mobile
    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        if (!isCompact() && root.classList.contains('is-open')) { setPanel(false); closeDropdowns(); }
      }).observe(root);
    }
  }

  function currentTheme() {
    var set = document.documentElement.getAttribute('data-theme');
    if (set) return set;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function initThemeToggle(btn) {
    if (!btn || btn.__aeTheme) return;
    btn.__aeTheme = true;
    btn.setAttribute('aria-pressed', String(currentTheme() === 'dark'));
    btn.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      btn.setAttribute('aria-pressed', String(next === 'dark'));
      try { localStorage.setItem('ae-theme', next); } catch (e) { /* armazenamento indisponível: vale só nesta página */ }
    });
  }

  function initAll(scope) {
    scope = scope || document;
    Array.prototype.forEach.call(scope.querySelectorAll('[data-ae-navbar]'), initNavbar);
    Array.prototype.forEach.call(scope.querySelectorAll('[data-ae-theme-toggle]'), initThemeToggle);
  }

  window.AuroraElo = { initNavbar: initNavbar, initThemeToggle: initThemeToggle, init: initAll };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { initAll(); });
  else initAll();
})();
