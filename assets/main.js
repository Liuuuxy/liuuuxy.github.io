/* Xinyuan Liu — site behaviour: theme toggle, publication tabs, BibTeX,
   demo videos. No dependencies. Without JavaScript every publication and
   BibTeX entry stays visible (the .js class gates the collapsing), which is
   also what crawlers see. */
(function () {
  'use strict';

  var root = document.documentElement;

  /* ------------------------------------------------------------- theme --- */

  // The initial theme is applied in <head>; this syncs the toggle and the
  // browser chrome colour, and handles clicks.
  var toggle = document.getElementById('theme-toggle');
  var themeMetas = document.querySelectorAll('meta[name="theme-color"]');

  function syncTheme() {
    var dark = root.classList.contains('dark');
    if (toggle) toggle.setAttribute('aria-pressed', dark ? 'true' : 'false');
    var bg = getComputedStyle(root).getPropertyValue('--bg').trim();
    for (var i = 0; i < themeMetas.length; i++) {
      if (bg) themeMetas[i].setAttribute('content', bg);
    }
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      var dark = root.classList.toggle('dark');
      try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (e) {}
      syncTheme();
    });
  }
  syncTheme();

  /* -------------------------------------------------- publication tabs --- */

  var TABS = { all: 'all', conferences: 'conference', preprints: 'preprint' };
  var list = document.getElementById('pub-list');
  var panel = document.getElementById('pub-panel');
  var buttons = Array.prototype.slice.call(document.querySelectorAll('.tab-button'));

  function activate(name, updateHash) {
    if (!list || !TABS.hasOwnProperty(name)) return false;
    list.setAttribute('data-filter', TABS[name]);
    buttons.forEach(function (b) {
      var on = b.getAttribute('data-tab') === name;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.setAttribute('tabindex', on ? '0' : '-1');
      if (on && panel) panel.setAttribute('aria-labelledby', b.id);
    });
    if (updateHash && window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#' + name);
    }
    return true;
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

  // A shared link such as /#conferences opens with that filter and scrolls to
  // the list; no element carries those ids, so the browser would not scroll.
  function fromHash() {
    var h = (window.location.hash || '').slice(1);
    if (activate(h, false) && h !== 'all') {
      var section = document.getElementById('publications');
      if (section) section.scrollIntoView();
    }
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
    var label = b.querySelector('span');
    var original = label ? label.textContent : '';
    function say(text) {
      if (!label) return;
      label.textContent = text;
      setTimeout(function () { label.textContent = original; }, 1800);
    }
    b.addEventListener('click', function () {
      var src = document.getElementById(b.getAttribute('data-copy-target'));
      if (!src) return;
      function selectFallback() {
        var range = document.createRange();
        range.selectNodeContents(src);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        say('Selected — press Ctrl/Cmd+C');
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(src.textContent).then(function () { say('Copied'); }, selectFallback);
      } else {
        selectFallback();
      }
    });
  });

  /* ------------------------------------------------------- demo videos --- */

  // Looping demos autoplay muted; visitors who ask for reduced motion get
  // the poster frame and the play control instead.
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('video[autoplay]').forEach(function (v) {
      v.removeAttribute('autoplay');
      v.pause();
    });
  }
})();
