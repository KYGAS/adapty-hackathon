/* Adapty-style icon sprite.
   Adapty's icons are custom 20×20 outline glyphs: stroke 1.5, round caps
   and joins, stroke="currentColor", no fill. These are look-alike
   re-drawings (not Adapty's assets) so the kit is safe to share.
   Nearest open-source match if you need more: Lucide / Phosphor "regular"
   at size 20, strokeWidth 1.5.
   Usage: <svg class="ad-icon"><use href="#i-ab"></use></svg>            */
(function () {
  const P = {
    overview: '<path d="M2 13.5V12a8 8 0 0 1 16 0v1.5a.6.6 0 0 1-.6.6H2.6a.6.6 0 0 1-.6-.6Z"/><path d="M10 4v2.5M8.2 14.1 13 7.6M4.3 8.6l1.9 1M15.7 8.6l-1.9 1"/>',
    analytics: '<path d="M3 17h14M5 14V9M8.5 14V5M12 14v-6M15.5 14V3"/>',
    users: '<circle cx="7.5" cy="7" r="3"/><path d="M2.5 16.5c.6-2.6 2.6-4 5-4s4.4 1.4 5 4"/><path d="M12.5 4.2a3 3 0 0 1 0 5.6M14.5 12.8c1.4.5 2.5 1.7 3 3.7"/>',
    box: '<rect x="3" y="3" width="14" height="14" rx="2"/><path d="M3 7.5h14M8 11h4"/>',
    flows: '<rect x="3.5" y="2.5" width="9" height="15" rx="2"/><path d="M7 15h2M13.5 6.5h3l-1.5-1.5M16.5 6.5 15 8"/>',
    pin: '<path d="M10 17.5s5.5-4.8 5.5-9.3a5.5 5.5 0 1 0-11 0c0 4.5 5.5 9.3 5.5 9.3Z"/><circle cx="10" cy="8.2" r="2"/>',
    message: '<rect x="4" y="2.5" width="11" height="15" rx="2"/><path d="M7 6.5h5M7 9.5h5M7 12.5h3"/>',
    ab: '<path d="M15.8 4.2 4.2 15.8M2.8 5.2h3.4M1.7 7.5l2.4-5.3c.2-.4.6-.4.8 0l2.4 5.3M13.6 15.4h2.9a1.5 1.5 0 0 0 0-2.9h-2.9v2.9Zm0 0h3.3a1.5 1.5 0 0 1 0 2.9h-3.3v-2.9Z"/>',
    rocket: '<path d="M11.5 15.5 8 12l-3.5 3.5M8 12l-3.5-3.5L8 5c2.5-2.5 6-3 8.5-2.5.5 2.5 0 6-2.5 8.5L11.5 15.5 8 12Z"/><circle cx="12.5" cy="7.5" r="1.3"/><path d="M4.5 8.5H2.5l2-3h3M11.5 15.5v2l3-2v-3"/>',
    refund: '<rect x="2.5" y="4" width="15" height="12" rx="2"/><path d="M2.5 8h15M6 12h3M13 11l1.5 1.5L13 14"/>',
    dollar: '<circle cx="10" cy="10" r="7.5"/><path d="M12.3 7.6c-.3-.9-1.2-1.4-2.3-1.4-1.3 0-2.3.7-2.3 1.8 0 2.5 4.8 1.4 4.8 4 0 1.1-1.1 1.9-2.5 1.9-1.2 0-2.2-.6-2.5-1.6M10 5v1.2M10 13.8V15"/>',
    plug: '<path d="M7 3v3M13 3v3M5 6h10v3a5 5 0 0 1-10 0V6ZM10 14v3"/>',
    bell: '<path d="M5 8a5 5 0 0 1 10 0c0 5 2 6 2 6H3s2-1 2-6ZM8.3 17a1.8 1.8 0 0 0 3.4 0"/>',
    'chevron-down': '<path d="m5 7.5 5 5 5-5"/>',
    'chevron-up': '<path d="m5 12.5 5-5 5 5"/>',
    'chevron-right': '<path d="m7.5 5 5 5-5 5"/>',
    'chevron-left': '<path d="m12.5 5-5 5 5 5"/>',
    'chevrons-left': '<path d="m10 5-5 5 5 5M15 5l-5 5 5 5"/>',
    'arrow-left': '<path d="M16.5 10h-13M8.5 5l-5 5 5 5"/>',
    external: '<path d="M11.5 3h5.5v5.5M17 3l-7.5 7.5M14.5 11.5V16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6.5a1 1 0 0 1 1-1h4.5"/>',
    search: '<circle cx="8.8" cy="8.8" r="5.8"/><path d="m13 13 4 4"/>',
    x: '<path d="M15 5 5 15M5 5l10 10"/>',
    check: '<path d="m4 10.5 4 4 8-9"/>',
    'check-circle': '<circle cx="10" cy="10" r="7.5"/><path d="m6.8 10.2 2.2 2.2 4.2-4.6"/>',
    more: '<circle cx="10" cy="4.5" r="1" fill="currentColor"/><circle cx="10" cy="10" r="1" fill="currentColor"/><circle cx="10" cy="15.5" r="1" fill="currentColor"/>',
    metrics: '<path d="M3 3v14h14M7 13V9M10.5 13V6M14 13v-3"/>',
    trend: '<path d="M2.5 15.5 7.5 10l3 3 7-7.5M13.5 5.5h4v4"/><path d="M2.5 17.5h15"/>',
    stop: '<circle cx="10" cy="10" r="7.5"/><rect x="7.5" y="7.5" width="5" height="5" rx=".8"/>',
    play: '<path d="M6 4.5v11a.6.6 0 0 0 .9.5l8.6-5.5a.6.6 0 0 0 0-1L6.9 4a.6.6 0 0 0-.9.5Z"/>',
    pencil: '<path d="M3 17h3.5L16 7.5a2.1 2.1 0 0 0-3-3L3.5 14 3 17ZM11.5 6l2.5 2.5"/>',
    copy: '<rect x="6.5" y="6.5" width="10" height="10" rx="1.5"/><path d="M13.5 6.5V4.5a1 1 0 0 0-1-1h-8a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h2"/>',
    branch: '<circle cx="5.5" cy="4.5" r="2"/><circle cx="5.5" cy="15.5" r="2"/><circle cx="14.5" cy="6.5" r="2"/><path d="M5.5 6.5v7M14.5 8.5c0 3-4 3-8.2 5.6"/>',
    archive: '<rect x="3" y="3.5" width="14" height="13" rx="1.5"/><path d="M3 12.5h3.5l1 1.5h5l1-1.5H17M10 6.5V10m-2-1.5 2 2 2-2"/>',
    trash: '<path d="M3.5 5.5h13M8 5.5V4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1.5M5 5.5l.8 10.6a1 1 0 0 0 1 .9h6.4a1 1 0 0 0 1-.9L15 5.5M8.5 9v5M11.5 9v5"/>',
    plus: '<path d="M10 4v12M4 10h12"/>',
    calendar: '<rect x="3" y="4" width="14" height="13" rx="1.5"/><path d="M3 8h14M7 2.5v3M13 2.5v3"/>',
    download: '<path d="M10 3v10M6 9.5l4 4 4-4M3.5 15v1.5a.5.5 0 0 0 .5.5h12a.5.5 0 0 0 .5-.5V15"/>',
    file: '<path d="M11.5 2.5H5.5a1 1 0 0 0-1 1v13a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-10l-4-4ZM11.5 2.5v4h4M7.5 10.5h5M7.5 13.5h3"/>',
    sliders: '<path d="M3 6h7M14 6h3M3 14h3M10 14h7"/><circle cx="12" cy="6" r="2"/><circle cx="8" cy="14" r="2"/>',
    'user-plus': '<circle cx="8" cy="7" r="3"/><path d="M2.5 16.5c.6-2.6 2.8-4 5.5-4 1 0 2 .2 2.8.6M15 11v6M12 14h6"/>',
    hash: '<path d="M4 7.5h13M3 12.5h13M8.5 3 7 17M13 3l-1.5 14"/>',
    sync: '<path d="M16.5 8A6.7 6.7 0 0 0 4.3 6.2L3 8M3.5 12a6.7 6.7 0 0 0 12.2 1.8L17 12M3 3.5V8h4.5M17 16.5V12h-4.5"/>',
    clock: '<circle cx="10" cy="11" r="6.5"/><path d="M10 7.5V11l2 1.5M8 2.5h4"/>',
    image: '<rect x="3" y="3.5" width="14" height="13" rx="1.5"/><circle cx="7.5" cy="8" r="1.3"/><path d="m3 14 4-4 3.5 3.5 2-2L17 15"/>',
    info: '<circle cx="10" cy="10" r="7.5"/><path d="M10 9v5M10 6.2v.1"/>',
    warning: '<circle cx="10" cy="10" r="7.5"/><path d="M10 6v4.5M10 13.6v.1"/>',
    help: '<circle cx="10" cy="10" r="7.5"/><path d="M8 7.8a2 2 0 1 1 2.6 1.9c-.4.2-.6.5-.6.9v.6M10 13.6v.1"/>',
    sparkle: '<path d="M10 2.5c.5 3.8 1.7 5 5.5 5.5-3.8.5-5 1.7-5.5 5.5-.5-3.8-1.7-5-5.5-5.5 3.8-.5 5-1.7 5.5-5.5ZM15.5 13c.2 1.5.8 2.1 2.2 2.2-1.4.2-2 .8-2.2 2.3-.2-1.5-.8-2.1-2.3-2.3 1.5-.1 2.1-.7 2.3-2.2Z"/>',
    upload: '<path d="M10 13V3M6 7l4-4 4 4M3.5 15v1.5a.5.5 0 0 0 .5.5h12a.5.5 0 0 0 .5-.5V15"/>',
    eye: '<path d="M1.5 10S4.5 4 10 4s8.5 6 8.5 6-3 6-8.5 6-8.5-6-8.5-6Z"/><circle cx="10" cy="10" r="2.5"/>',
    grip: '<circle cx="7.5" cy="5" r="1" fill="currentColor"/><circle cx="12.5" cy="5" r="1" fill="currentColor"/><circle cx="7.5" cy="10" r="1" fill="currentColor"/><circle cx="12.5" cy="10" r="1" fill="currentColor"/><circle cx="7.5" cy="15" r="1" fill="currentColor"/><circle cx="12.5" cy="15" r="1" fill="currentColor"/>',
    flask: '<path d="M7.5 2.5h5M8.5 2.5v5L3.8 15.3A1.5 1.5 0 0 0 5.1 17.5h9.8a1.5 1.5 0 0 0 1.3-2.2L11.5 7.5v-5M5.5 12.5h9"/>'
  };
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">' +
    Object.entries(P).map(([k, v]) => `<symbol id="i-${k}" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${v}</symbol>`).join('') +
    '</svg>';
  const inject = () => document.body.insertAdjacentHTML('afterbegin', svg);
  if (document.body) inject(); else document.addEventListener('DOMContentLoaded', inject);
  window.adIcon = (name, cls = 'ad-icon') => `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
  window.AD_ICON_NAMES = Object.keys(P);
})();
