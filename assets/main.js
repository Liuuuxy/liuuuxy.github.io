/* Xinyuan Liu — site behaviour: theme toggle, publication tabs, BibTeX.
   No dependencies. Without JavaScript every publication stays visible and
   BibTeX blocks stay in the DOM, which is also what crawlers see. */
(function () {
  'use strict';

  /* ------------------------------------------------------------- theme --- */

  // The initial theme is applied in <head>; this only wires up the toggle.
  var toggle = document.getElementById('theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var dark = document.documentElement.classList.toggle('dark');
      try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (e) {}
    });
  }

  /* -------------------------------------------------- publication tabs --- */

  var TABS = { all: 'all', conferences: 'conference', preprints: 'preprint' };
  var list = document.getElementById('pub-list');
  var buttons = Array.prototype.slice.call(document.querySelectorAll('.tab-button'));

  function activate(name, updateHash) {
    if (!list || !TABS.hasOwnProperty(name)) return;
    list.setAttribute('data-filter', TABS[name]);
    buttons.forEach(function (b) {
      var on = b.getAttribute('data-tab') === name;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.setAttribute('tabindex', on ? '0' : '-1');
      if (on) list.setAttribute('aria-labelledby', b.id);
    });
    if (updateHash && window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#' + name);
    }
  }

  buttons.forEach(function (b, i) {
    b.addEventListener('click', function (e) {
      e.preventDefault();
      activate(b.getAttribute('data-tab'), true);
    });
    // Arrow keys move between tabs, per the ARIA tabs pattern.
    b.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      var next = buttons[(i + (e.key === 'ArrowRight' ? 1 : buttons.length - 1)) % buttons.length];
      activate(next.getAttribute('data-tab'), true);
      next.focus();
    });
  });

  function fromHash() {
    var h = (window.location.hash || '').slice(1);
    if (TABS.hasOwnProperty(h)) activate(h, false);
  }
  window.addEventListener('hashchange', fromHash);
  fromHash();

  /* ------------------------------------------------------------ BibTeX --- */

  document.querySelectorAll('[data-bibtex-toggle]').forEach(function (b) {
    b.addEventListener('click', function () {
      var box = document.getElementById(b.getAttribute('data-bibtex-toggle'));
      if (!box) return;
      var shown = box.classList.toggle('show');
      b.setAttribute('aria-expanded', shown ? 'true' : 'false');
    });
  });

  document.querySelectorAll('[data-copy-target]').forEach(function (b) {
    b.addEventListener('click', function () {
      var src = document.getElementById(b.getAttribute('data-copy-target'));
      var label = b.querySelector('span');
      if (!src || !navigator.clipboard) return;
      navigator.clipboard.writeText(src.textContent).then(function () {
        if (!label) return;
        var old = label.textContent;
        label.textContent = 'Copied';
        setTimeout(function () { label.textContent = old; }, 1600);
      });
    });
  });
})();
