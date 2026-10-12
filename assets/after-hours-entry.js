/* A discoverable Easter egg, never an authentication mechanism. */
(function () {
  'use strict';
  const trigger = document.querySelector('[data-after-hours-trigger]');
  const door = document.getElementById('after-hours-door');
  if (!trigger || !door) return;
  let count = 0, lastTap = -Infinity;
  function reset() { count = 0; lastTap = -Infinity; }
  trigger.addEventListener('click', event => {
    if (!door.hidden) return;
    const now = performance.now();
    count = now - lastTap <= 2000 ? count + 1 : 1;
    lastTap = now;
    if (count < 5) return;
    door.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    if (event.detail === 0) door.focus();
    reset();
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) reset(); });
  window.addEventListener('blur', reset);
  window.addEventListener('pagehide', reset);
})();
