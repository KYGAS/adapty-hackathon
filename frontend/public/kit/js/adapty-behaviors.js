/* =====================================================================
   ADAPTY DASHBOARD — BEHAVIORS (vanilla JS, no deps)
   Reproduces how Adapty's UI *behaves*, observed on app.adapty.io:
   - Kebab / dropdown menus open on click, close on outside click or on
     choosing an item. (Escape does NOT close them in Adapty; we keep that.)
   - Hints: dotted-underlined text shows a white popover on hover
     (title 12/700 + text 12/400), no click needed.
   - Selects: react-select style, purple border while open, option hover gray.
   - Modals: dark 60% overlay, X top-right, footer Cancel + primary.
   - Sticky lavender form footer appears once a form becomes dirty.
   - Copy chips copy their value and confirm with a toast.
   All hooks are data-attributes so they work on any markup/framework.
   ===================================================================== */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* ---------- Menus: <div class="ad-menu-anchor"><button data-menu-trigger>…</button><ul class="ad-menu">…</ul></div> */
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-menu-trigger]');
    const inMenu = e.target.closest('.ad-menu');
    $$('.ad-menu.is-open').forEach((m) => {
      if (trigger && m.parentElement.contains(trigger)) return;
      if (inMenu === m && !e.target.closest('.ad-menu__item')) return;
      m.classList.remove('is-open');
      m.parentElement.querySelector('[data-menu-trigger]')?.classList.remove('is-open');
    });
    if (trigger) {
      const menu = trigger.parentElement.querySelector('.ad-menu');
      const open = !menu.classList.contains('is-open');
      menu.classList.toggle('is-open', open);
      trigger.classList.toggle('is-open', open);
    }
  });

  /* ---------- Selects: .ad-select > button.ad-select__control + .ad-select__menu > .ad-select__option[data-value] */
  document.addEventListener('click', (e) => {
    const control = e.target.closest('.ad-select__control');
    const option = e.target.closest('.ad-select__option');
    $$('.ad-select.is-open').forEach((s) => { if (!s.contains(e.target)) s.classList.remove('is-open'); });
    if (control) control.parentElement.classList.toggle('is-open');
    if (option) {
      const sel = option.closest('.ad-select');
      const label = sel.querySelector('.ad-select__value');
      label.textContent = option.textContent.trim();
      label.classList.remove('ad-select__placeholder');
      sel.dataset.value = option.dataset.value || option.textContent.trim();
      sel.querySelectorAll('.ad-select__option').forEach((o) => o.classList.toggle('is-selected', o === option));
      sel.classList.remove('is-open');
      sel.dispatchEvent(new CustomEvent('ad-change', { bubbles: true, detail: { value: sel.dataset.value } }));
    }
  });

  /* ---------- Filter dropdown buttons with a panel: [data-dropdown] > .ad-dropdown-btn + .ad-menu */
  // (reuses menu logic: give the button data-menu-trigger)

  /* ---------- Tabs & segmented: [data-tabs] > [data-tab="key"] ; panels [data-tab-panel="key"] in [data-tabs-for="group"] */
  document.addEventListener('click', (e) => {
    const tab = e.target.closest('[data-tab]');
    if (!tab) return;
    const group = tab.closest('[data-tabs]');
    if (!group) return;
    $$('[data-tab]', group).forEach((t) => t.classList.toggle('is-selected', t === tab));
    const name = group.dataset.tabs;
    if (name) $$(`[data-tabs-for="${name}"] > [data-tab-panel]`).forEach((p) => p.classList.toggle('u-hidden', p.dataset.tabPanel !== tab.dataset.tab));
    group.dispatchEvent(new CustomEvent('ad-tab', { bubbles: true, detail: { tab: tab.dataset.tab } }));
  });

  /* ---------- Hint popovers: [data-hint-title] and/or [data-hint] on any element */
  let pop;
  const showHint = (el) => {
    if (!pop) { pop = document.createElement('div'); pop.className = 'ad-popover'; document.body.appendChild(pop); }
    const t = el.dataset.hintTitle, d = el.dataset.hint;
    pop.className = 'ad-popover' + (el.dataset.hintDark !== undefined ? ' ad-popover--dark' : '');
    pop.innerHTML = (t ? `<span class="ad-popover__title">${t}</span>` : '') + (d ? `<span class="ad-popover__text">${d}</span>` : '');
    const r = el.getBoundingClientRect();
    pop.style.left = '0px'; pop.style.top = '0px';
    const pr = pop.getBoundingClientRect();
    let top = r.top + window.scrollY - pr.height - 8;
    if (top < window.scrollY + 8) top = r.bottom + window.scrollY + 8;
    let left = r.left + window.scrollX + r.width / 2 - pr.width / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - pr.width - 8));
    pop.style.left = left + 'px'; pop.style.top = top + 'px';
    requestAnimationFrame(() => pop.classList.add('is-visible'));
  };
  document.addEventListener('mouseover', (e) => { const el = e.target.closest('[data-hint],[data-hint-title]'); if (el) showHint(el); });
  const hideHint = () => pop && pop.classList.remove('is-visible');
  window.addEventListener('hashchange', hideHint);
  document.addEventListener('click', hideHint, true);
  window.addEventListener('scroll', hideHint, true);
  document.addEventListener('mouseout', (e) => { const el = e.target.closest('[data-hint],[data-hint-title]'); if (el && pop && !el.contains(e.relatedTarget)) pop.classList.remove('is-visible'); });

  /* ---------- Modals: [data-modal-open="id"] / [data-modal-close] / overlay id */
  window.adModal = {
    open(id) { const o = document.getElementById(id); if (o) { o.classList.add('is-open'); document.body.style.overflow = 'hidden'; } },
    close(id) { const o = id ? document.getElementById(id) : $('.ad-overlay.is-open'); if (o) { o.classList.remove('is-open'); document.body.style.overflow = ''; } }
  };
  document.addEventListener('click', (e) => {
    const opener = e.target.closest('[data-modal-open]');
    if (opener) { e.preventDefault(); adModal.open(opener.dataset.modalOpen); return; }
    const closer = e.target.closest('[data-modal-close]');
    if (closer) { adModal.close(closer.closest('.ad-overlay')?.id); return; }
    if (e.target.classList?.contains('ad-overlay')) adModal.close(e.target.id);
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') adModal.close(); });

  /* ---------- Toasts: adToast('Placement saved', 'success'|'error'|'info'|'warning') */
  window.adToast = (msg, type = 'success', ms = 4000) => {
    let wrap = $('.ad-toasts');
    if (!wrap) { wrap = document.createElement('div'); wrap.className = 'ad-toasts'; document.body.appendChild(wrap); }
    const icon = { success: 'check-circle', error: 'warning', info: 'info', warning: 'warning' }[type] || 'info';
    const t = document.createElement('div');
    t.className = `ad-toast ad-toast--${type}`;
    t.innerHTML = `${window.adIcon ? adIcon(icon, 'ad-icon ad-toast__icon') : ''}<span>${msg}</span><button class="ad-toast__close" aria-label="Close">${window.adIcon ? adIcon('x', 'ad-icon ad-icon--16') : '×'}</button>`;
    t.querySelector('.ad-toast__close').onclick = () => t.remove();
    wrap.appendChild(t);
    setTimeout(() => t.remove(), ms);
  };

  /* ---------- Copy chips: [data-copy="value"] */
  document.addEventListener('click', (e) => {
    const c = e.target.closest('[data-copy]');
    if (!c) return;
    navigator.clipboard?.writeText(c.dataset.copy).catch(() => {});
    adToast('Copied to clipboard', 'success', 2000);
  });

  /* ---------- Search clear button */
  document.addEventListener('input', (e) => {
    const s = e.target.closest('.ad-search');
    if (s) s.classList.toggle('has-value', !!e.target.value);
  });
  document.addEventListener('click', (e) => {
    const b = e.target.closest('.ad-search__clear');
    if (!b) return;
    const s = b.closest('.ad-search'); const i = s.querySelector('input');
    i.value = ''; s.classList.remove('has-value'); i.dispatchEvent(new Event('input', { bubbles: true })); i.focus();
  });

  /* ---------- Radio cards: .ad-radio-card containing an <input type=radio> */
  document.addEventListener('change', (e) => {
    if (e.target.type !== 'radio') return;
    const card = e.target.closest('.ad-radio-card');
    if (!card) return;
    $$(`input[name="${e.target.name}"]`).forEach((r) => r.closest('.ad-radio-card')?.classList.toggle('is-active', r.checked));
  });

  /* ---------- Dirty-form footer: <form data-dirty-footer="footerId"> */
  const markDirty = (e) => {
    const f = e.target.closest('[data-dirty-footer]');
    if (f) document.getElementById(f.dataset.dirtyFooter)?.classList.add('is-open');
  };
  document.addEventListener('input', markDirty);
  document.addEventListener('ad-change', markDirty);

  /* ---------- Pickers (Select placement / Select flow): [data-picker-trigger="id"] */
  document.addEventListener('click', (e) => {
    const trig = e.target.closest('[data-picker-trigger]');
    $$('.ad-picker.is-open').forEach((p) => { if (!p.contains(e.target) && (!trig || trig.dataset.pickerTrigger !== p.id)) p.classList.remove('is-open'); });
    if (trig) {
      const p = document.getElementById(trig.dataset.pickerTrigger);
      const r = trig.getBoundingClientRect();
      p.style.left = (r.left + window.scrollX) + 'px';
      const below = r.bottom + 4 + 380 < window.innerHeight;
      p.style.top = (below ? r.bottom + window.scrollY + 4 : r.top + window.scrollY - 4 - Math.min(380, p.scrollHeight || 380)) + 'px';
      p.classList.toggle('is-open');
      p.querySelector('input')?.focus();
      p._trigger = trig;
    }
    const item = e.target.closest('.ad-picker__item');
    if (item) {
      const p = item.closest('.ad-picker');
      p.classList.remove('is-open');
      p.dispatchEvent(new CustomEvent('ad-pick', { bubbles: true, detail: { value: item.dataset.value || item.firstChild.textContent.trim(), trigger: p._trigger } }));
    }
  });
  document.addEventListener('input', (e) => {
    const p = e.target.closest('.ad-picker');
    if (!p) return;
    const q = e.target.value.toLowerCase();
    $$('.ad-picker__item', p).forEach((i) => i.classList.toggle('u-hidden', !i.textContent.toLowerCase().includes(q)));
  });

  /* ---------- Sortable data-grid headers: th.is-sortable toggles caret state (visual only) */
  document.addEventListener('click', (e) => {
    const th = e.target.closest('th.is-sortable');
    if (!th) return;
    const table = th.closest('table');
    const dir = th.dataset.dir === 'desc' ? 'asc' : 'desc';
    $$('th.is-sortable', table).forEach((h) => { h.classList.remove('is-sorted'); delete h.dataset.dir; h.querySelectorAll('.ad-sort span').forEach((s) => s.classList.remove('is-active')); });
    th.classList.add('is-sorted'); th.dataset.dir = dir;
    th.querySelector(dir === 'desc' ? '.ad-sort span:last-child' : '.ad-sort span:first-child')?.classList.add('is-active');
    const idx = Array.from(th.parentElement.children).indexOf(th);
    $$('tbody tr', table).forEach((tr) => tr.children[idx]?.classList.add('is-sorted'));
    $$('tbody tr', table).forEach((tr) => Array.from(tr.children).forEach((td, i) => td.classList.toggle('is-sorted', i === idx)));
  });

  /* ---------- Callout dismiss */
  document.addEventListener('click', (e) => { const x = e.target.closest('.ad-callout__close'); if (x) x.closest('.ad-callout').remove(); });
})();
