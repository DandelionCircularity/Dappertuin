// Mobile menu and the submenus ("Over de stichting", "Workshops"). On small screens all submenu items are listed in the menu.
(function () {
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('hoofdmenu');
  var subs = Array.prototype.slice.call(document.querySelectorAll('.has-sub'));

  function setSub(sub, open) {
    sub.classList.toggle('open', open);
    sub.querySelector('.sub-toggle').setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  subs.forEach(function (sub) {
    sub.querySelector('.sub-toggle').addEventListener('click', function () {
      var open = !sub.classList.contains('open');
      subs.forEach(function (other) { if (other !== sub) setSub(other, false); });
      setSub(sub, open);
    });
    sub.addEventListener('focusout', function (e) {
      if (e.relatedTarget && !sub.contains(e.relatedTarget)) setSub(sub, false);
    });
  });
  document.addEventListener('click', function (e) {
    subs.forEach(function (sub) { if (!sub.contains(e.target)) setSub(sub, false); });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    subs.forEach(function (sub) {
      if (sub.classList.contains('open')) {
        setSub(sub, false);
        sub.querySelector('.sub-toggle').focus();
      }
    });
    if (nav && nav.classList.contains('open')) {
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    }
  });
})();

// Calendar: hide activities whose date has passed since the site was last rebuilt.
(function () {
  var d = new Date();
  var today = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  document.querySelectorAll('.agenda-item[data-datum]').forEach(function (item) {
    if (item.getAttribute('data-datum') < today) item.remove();
  });
  document.querySelectorAll('.agenda-upcoming').forEach(function (box) {
    if (!box.querySelector('.agenda-item')) box.remove();
  });
})();

// YouTube videos load only after a click, in privacy-enhanced mode. Without JavaScript the link opens YouTube.
(function () {
  document.querySelectorAll('.yt-play[data-yt]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      var frame = document.createElement('iframe');
      frame.src = 'https://www.youtube-nocookie.com/embed/' + link.getAttribute('data-yt') + '?autoplay=1&rel=0';
      frame.title = link.getAttribute('data-title');
      frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
      frame.allowFullscreen = true;
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      link.replaceWith(frame);
      frame.focus();
    });
  });
})();
