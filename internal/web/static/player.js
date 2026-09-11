// Lantern player: one <audio>/<video> element, a playlist of siblings, autoplay next,
// position memory in localStorage, Media Session on the lock screen.
(function () {
  var main = document.querySelector('main.player');
  var media = document.getElementById('media');
  var tracks = JSON.parse(main.dataset.tracks || '[]');
  var idx = parseInt(main.dataset.index || '0', 10);
  var isVideo = media.tagName === 'VIDEO';
  var $ = function (id) { return document.getElementById(id); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) {} }
  };
  function posKey(t) { return 'lantern:pos:' + t.path; }
  function fmt(s) { if (!isFinite(s)) return '–:––'; s = Math.floor(s); return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }
  function cur() { return tracks[idx]; }

  function applyTrack(autoplay) {
    var t = cur();
    if (!t) return;
    media.src = t.file;
    if (isVideo) { if (t.cover) media.poster = t.cover; }
    else {
      var big = main.querySelector('.big');
      if (t.cover) big.innerHTML = '<img class="cover" src="' + t.cover + '" alt="">';
    }
    var title = $('title'); if (title) title.textContent = t.title;
    var p = tracks[idx - 1], n = tracks[idx + 1];
    var prev = $('prev'), next = $('next');
    if (isVideo) {
      prev.hidden = !p; next.hidden = !n;
      if (p) $('prev-title').textContent = p.title;
      if (n) $('next-title').textContent = n.title;
      var sub = main.querySelector('.sub'); if (sub) sub.hidden = !n;
    } else {
      prev.disabled = !p; next.disabled = !n;
    }
    document.title = t.title + ' — Фонарик';
    history.replaceState(null, '', t.url);
    var saved = parseFloat(store.get(posKey(t)) || '0');
    media.addEventListener('loadedmetadata', function once() {
      media.removeEventListener('loadedmetadata', once);
      if (saved > 3 && saved < media.duration - 3) media.currentTime = saved;
      if ($('dur')) $('dur').textContent = fmt(media.duration);
    });
    media.load();
    if (autoplay) media.play().catch(function () {});
    if ('mediaSession' in navigator) {
      var parent = main.querySelector('.sub') && !isVideo ? main.querySelector('.sub').textContent : '';
      navigator.mediaSession.metadata = new MediaMetadata({ title: t.title, artist: parent, album: 'Фонарик',
        artwork: t.cover ? [{ src: t.cover, sizes: '512x512', type: 'image/jpeg' }] : [] });
    }
  }
  function go(d, autoplay) {
    var j = idx + d;
    if (j < 0 || j >= tracks.length) return;
    idx = j; applyTrack(autoplay);
  }

  $('prev').addEventListener('click', function () { go(-1, !media.paused || isVideo); });
  $('next').addEventListener('click', function () { go(1, !media.paused || isVideo); });
  media.addEventListener('ended', function () {
    store.del(posKey(cur()));
    if (idx + 1 < tracks.length) go(1, true);
  });
  var lastSave = 0;
  media.addEventListener('timeupdate', function () {
    var now = Date.now();
    if (now - lastSave > 3000) { lastSave = now; store.set(posKey(cur()), String(media.currentTime)); }
    if (!isVideo && media.duration) {
      var pct = (media.currentTime / media.duration * 100) + '%';
      $('fill').style.width = pct; $('knob').style.left = pct; $('cur').textContent = fmt(media.currentTime);
    }
  });

  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('play', function () { media.play(); });
    navigator.mediaSession.setActionHandler('pause', function () { media.pause(); });
    navigator.mediaSession.setActionHandler('previoustrack', function () { go(-1, true); });
    navigator.mediaSession.setActionHandler('nexttrack', function () { go(1, true); });
  }

  if (!isVideo) {
    var play = $('play');
    play.addEventListener('click', function () { if (media.paused) media.play(); else media.pause(); });
    media.addEventListener('play', function () { main.classList.add('playing'); });
    media.addEventListener('pause', function () { main.classList.remove('playing'); });
    var seek = $('seek');
    function seekTo(ev) {
      var r = seek.getBoundingClientRect();
      var x = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
      var f = Math.max(0, Math.min(1, x / r.width));
      if (media.duration) media.currentTime = f * media.duration;
    }
    seek.addEventListener('pointerdown', function (ev) { seekTo(ev); seek.setPointerCapture(ev.pointerId); seek.dragging = true; });
    seek.addEventListener('pointermove', function (ev) { if (seek.dragging) seekTo(ev); });
    seek.addEventListener('pointerup', function () { seek.dragging = false; });
  }

  // initial: restore position without autoplay (iOS needs a gesture)
  applyTrack(false);
})();
