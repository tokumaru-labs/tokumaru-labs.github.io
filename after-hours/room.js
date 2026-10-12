/* Tiny canvas drawings, using an integer pixel grid and no external assets. */
(function () {
  'use strict';
  const room = document.getElementById('pixel-room');
  const nap = document.getElementById('nap-art');
  const chime = document.getElementById('chime-art');
  const button = document.getElementById('motion-toggle');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let motion = true, frame = null, lastDraw = -Infinity;
  const palettes = {
    room: { black: '#11151f', dark: '#302a32', edge: '#806849', soft: '#b79563', mid: '#73dbac', light: '#ffe8a3' },
    nap: { black: '#101a30', dark: '#283a54', edge: '#486484', soft: '#a3cddd', mid: '#b5d9ec', light: '#ffe5a1' },
    chime: { black: '#0d171d', dark: '#29393d', edge: '#a79e83', soft: '#d7c9a2', mid: '#ffc17d', light: '#b8f7a4' }
  };
  const books = ['#be765c', '#b69a56', '#639b9a', '#8a78a9', '#75947e'];
  function pixel(ctx, x, y, width, height, color) {
    ctx.fillStyle = color; ctx.fillRect(Math.round(x), Math.round(y), width, height);
  }
  function line(ctx, x1, y1, x2, y2, color) {
    const dx = Math.abs(x2 - x1), sx = x1 < x2 ? 1 : -1;
    const dy = -Math.abs(y2 - y1), sy = y1 < y2 ? 1 : -1;
    let error = dx + dy;
    for (;;) {
      pixel(ctx, x1, y1, 1, 1, color);
      if (x1 === x2 && y1 === y2) break;
      const twice = 2 * error;
      if (twice >= dy) { error += dy; x1 += sx; }
      if (twice <= dx) { error += dx; y1 += sy; }
    }
  }
  function moon(ctx, x, y, scale, palette) {
    const rows = ['0011100','0111110','1111000','1110000','1110000','0111000','0011110'];
    rows.forEach((row, yy) => [...row].forEach((p, xx) => { if (p === '1') pixel(ctx, x + xx * scale, y + yy * scale, scale, scale, palette.light); }));
  }
  function star(ctx, x, y, t, phase, palette) {
    const light = Math.sin(t * .7 + phase) > .35;
    pixel(ctx, x, y, 1, 1, light ? palette.mid : palette.edge);
    if (light && phase % 2 === 0) { pixel(ctx, x - 1, y, 3, 1, palette.soft); pixel(ctx, x, y - 1, 1, 3, palette.soft); }
  }
  function monitor(ctx, x, y, width, height, t, phase, palette) {
    pixel(ctx, x, y, width, height, palette.edge);
    pixel(ctx, x + 2, y + 2, width - 4, height - 5, palette.black);
    for (let xx = 0; xx < width - 6; xx++) {
      const yy = Math.round(Math.sin(xx * .32 + t * .5 + phase) * Math.max(1, (height - 8) * .2));
      pixel(ctx, x + 3 + xx, y + Math.floor(height / 2) + yy, 1, 1, palette.mid);
    }
    pixel(ctx, x + width - 4, y + height - 2, 1, 1, palette.light);
  }
  const digitRows = {
    '0':['111','101','101','101','111'], '3':['111','001','111','001','111'], ':':['0','1','0','1','0']
  };
  function digits(ctx, text, x, y, scale, palette) {
    for (const symbol of text) {
      const rows = digitRows[symbol];
      rows.forEach((row, yy) => [...row].forEach((p, xx) => { if (p === '1') pixel(ctx, x + xx * scale, y + yy * scale, scale, scale, palette.light); }));
      x += (rows[0].length + 1) * scale;
    }
  }
  function base(canvas, palette) {
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    pixel(ctx, 0, 0, canvas.width, canvas.height, palette.black);
    return ctx;
  }
  function drawRoom(t) {
    const palette = palettes.room;
    const ctx = base(room, palette);
    // A window, a desk, a shelf: a quiet, unoccupied observation room.
    pixel(ctx, 84, 4, 154, 51, palette.edge);
    pixel(ctx, 86, 6, 150, 47, '#172644');
    for (let i = 0; i < 25; i++) star(ctx, 91 + (i * 37 % 139), 9 + (i * 19 % 35), t, i, palette);
    moon(ctx, 199, 11, 2, palette);
    pixel(ctx, 154, 6, 2, 47, palette.edge);
    pixel(ctx, 86, 43, 150, 1, palette.edge);
    for (let i = 0; i < 13; i++) {
      const h = 3 + i * 7 % 14;
      pixel(ctx, 88 + i * 11, 52 - h, 8, h, '#263751');
      pixel(ctx, 91 + i * 11, 52 - h + 2, 1, 1, palette.soft);
    }
    pixel(ctx, 9, 7, 51, 68, palette.dark);
    for (let i = 0; i < 3; i++) {
      pixel(ctx, 10, 26 + i * 21, 49, 2, palette.edge);
      for (let j = 0; j < 7; j++) {
        const h = 9 + (i + j * 3) % 7;
        pixel(ctx, 14 + j * 6, 26 + i * 21 - h, 4, h, books[(i + j * 2) % books.length]);
      }
    }
    pixel(ctx, 73, 76, 207, 3, palette.soft);
    pixel(ctx, 82, 79, 3, 14, palette.edge);
    pixel(ctx, 267, 79, 3, 14, palette.edge);
    monitor(ctx, 106, 54, 39, 23, t, 0, palette);
    monitor(ctx, 150, 59, 27, 18, t, 2, palette);
    monitor(ctx, 190, 51, 43, 26, t, 4, palette);
    pixel(ctx, 236, 72, 12, 4, palette.edge);
    pixel(ctx, 238, 70, 8, 2, palette.soft);
    pixel(ctx, 257, 65, 8, 11, palette.edge);
    pixel(ctx, 259, 64, 4, 1, palette.soft);
    pixel(ctx, 94, 83, 42, 2, palette.dark);
    pixel(ctx, 174, 83, 59, 2, palette.dark);
    pixel(ctx, 289, 15, 18, 3, palette.edge);
    pixel(ctx, 297, 18, 2, 50, palette.edge);
    pixel(ctx, 286, 65, 23, 10, palette.edge);
    pixel(ctx, 288, 63, 19, 2, palette.mid);
    line(ctx, 0, 94, 319, 94, palette.edge);
  }
  function drawNap(t) {
    const palette = palettes.nap;
    const ctx = base(nap, palette);
    for (let i = 0; i < 16; i++) star(ctx, 10 + i * 19 % 108, 12 + i * 7 % 44, t, i, palette);
    moon(ctx, 55, 19, 3, palette);
    for (let i = 0; i < 7; i++) {
      const h = 9 + i * 7 % 17;
      pixel(ctx, 10 + i * 17, 62 - h, 14, h, palette.dark);
      pixel(ctx, 14 + i * 17, 64 - h, 2, 3, i % 3 ? palette.light : palette.soft);
    }
    pixel(ctx, 0, 62, 128, 1, palette.edge);
    pixel(ctx, 42, 65, 46, 1, palette.soft);
  }
  function drawChime(t) {
    const palette = palettes.chime;
    const ctx = base(chime, palette);
    pixel(ctx, 26, 15, 77, 44, palette.edge);
    pixel(ctx, 29, 18, 71, 36, palette.dark);
    pixel(ctx, 32, 21, 65, 30, palette.black);
    digits(ctx, '00:30', 37, 31, 2, palette);
    pixel(ctx, 57, 59, 16, 4, palette.edge);
    pixel(ctx, 44, 63, 41, 2, palette.soft);
    pixel(ctx, 94, 56, 2, 1, Math.sin(t * .6) > 0 ? palette.mid : palette.soft);
    pixel(ctx, 9, 59, 10, 1, palette.edge);
    pixel(ctx, 14, 54, 1, 11, palette.edge);
    pixel(ctx, 112, 22, 9, 1, palette.edge);
    pixel(ctx, 116, 18, 1, 9, palette.edge);
  }
  function draw(t) { drawRoom(t); drawNap(t); drawChime(t); }
  function enabled() { return motion && !reduced.matches && !document.hidden; }
  function animate(now) {
    frame = null;
    if (!enabled()) return;
    if (now - lastDraw >= 160) { draw(now / 1000); lastDraw = now; }
    frame = requestAnimationFrame(animate);
  }
  function update() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    const on = enabled();
    document.body.classList.toggle('still', !on);
    button.disabled = reduced.matches;
    button.setAttribute('aria-pressed', String(on));
    button.textContent = reduced.matches ? '動き：端末設定でオフ' : motion ? '動き：オン' : '動き：オフ';
    draw(0); lastDraw = -Infinity;
    if (on) frame = requestAnimationFrame(animate);
  }
  button.addEventListener('click', () => { motion = !motion; update(); });
  reduced.addEventListener('change', update);
  document.addEventListener('visibilitychange', update);
  window.addEventListener('pagehide', () => { if (frame !== null) cancelAnimationFrame(frame); frame = null; });
  window.addEventListener('pageshow', update);
  update();
})();
