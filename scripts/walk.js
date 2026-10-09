// Paste into the browser console on a Facebook photo viewer page for the dam's photo
// stream (a /photo/?fbid=...&set=pb.<page id>... URL). Walks "Next photo" back through
// every photo, saving full-size images as ~/Downloads/maengad_batch_p<time>.json
// (10 photos per file) for scripts/unpack.py. Chrome must allow automatic downloads
// for facebook.com.
//
// Facebook occasionally does a full page reload, which kills this script: check
// window.__dl ({count, failed, done, why}) now and then; if it's gone or done with
// why="stuck", paste the script again - it resumes from the photo on screen.
(() => {
  if (window.__dl && !window.__dl.done) return 'already running';
  const S = (window.__dl = { count: 0, failed: 0, done: false, why: '', seen: new Set(), batch: [] });
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fbid = () => (location.href.match(/fbid=(\d+)/) || [])[1];
  const shownImage = () =>
    [...document.querySelectorAll('img')]
      .filter((i) => i.naturalWidth > 300 && i.getBoundingClientRect().width > 300)
      .sort((a, b) => b.naturalWidth - a.naturalWidth)[0];
  const toDataUrl = (blob) => new Promise((r) => { const f = new FileReader(); f.onload = () => r(f.result); f.readAsDataURL(blob); });
  const flush = () => {
    if (!S.batch.length) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(S.batch)], { type: 'application/json' }));
    a.download = `maengad_batch_p${Date.now()}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 60000);  // free the batch once Chrome has saved it
    S.batch = [];
  };
  // Best effort only: browsers often drop downloads started during unload, so a reload can
  // lose up to 9 unsaved photos. After re-pasting, go back ~10 photos before restarting.
  window.addEventListener('pagehide', flush);

  (async () => {
    let prevSrc = window.__prevSrc || '';
    while (true) {
      const id = fbid();
      if (!id) { S.why = 'left viewer'; break; }
      if (S.seen.has(id)) { S.why = 'cycled'; break; }
      S.seen.add(id);

      let im;
      for (let t = 0; t < 60; t++) { im = shownImage(); if (im && im.src !== prevSrc && im.complete) break; await sleep(150); }
      let data = null;
      if (im && im.src !== prevSrc) {
        prevSrc = window.__prevSrc = im.src;
        try { data = await toDataUrl(await (await fetch(im.src)).blob()); } catch {}
      }
      S.batch.push({ id, data });  // data: null marks a photo the browser couldn't fetch
      data ? S.count++ : S.failed++;
      if (S.batch.length >= 10) flush();

      // The viewer is sometimes slow to advance; re-click Next every 5s, give up after 25s.
      let moved = false;
      for (let t = 0; t < 250 && !moved; t++) {
        if (t % 50 === 0) document.querySelector('[aria-label="Next photo"]')?.click();
        await sleep(100);
        moved = fbid() !== id;
      }
      if (!moved) { S.why = 'stuck'; break; }
    }
    flush();
    S.done = true;
  })();
  return 'started';
})();
