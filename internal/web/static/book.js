// Remember the last opened chapter per book; mark it in the chapter list.
(function () {
  var main = document.querySelector('main[data-book]');
  if (!main) return;
  var key = 'lantern:ch:' + main.dataset.book;
  var store = { get: function () { try { return localStorage.getItem(key); } catch (e) { return null; } },
                set: function (v) { try { localStorage.setItem(key, v); } catch (e) {} } };
  if (main.dataset.chapter) { store.set(main.dataset.chapter); return; }
  var k = store.get();
  if (!k) return;
  var tiles = main.querySelectorAll('.tile');
  var t = tiles[parseInt(k, 10) - 1];
  if (t) t.classList.add('current');
})();
