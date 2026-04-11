/**
 * Dashboard — shows image name, buildings detected, and export format.
 * Records are persisted to localStorage so they survive page refreshes.
 */

const STORAGE_KEY = 'bhumi_dashboard_v1';

export class Dashboard {
  constructor() {
    this._sessionStart  = Date.now();
    this._singleRecords = [];
    this._batchRecords  = [];
    this._exports       = [];
    this._recordedIds   = new Set();
    this._timerInterval = null;
    this._visible       = false;
    this._load();   // restore from localStorage on construction
  }

  // ── Persistence ───────────────────────────────────────────────────────────

  _load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      this._singleRecords = data.singleRecords || [];
      this._batchRecords  = data.batchRecords  || [];
      this._exports       = data.exports       || [];
      // Rebuild the dedup set from loaded records
      this._singleRecords.forEach(r => { if (r.itemId) this._recordedIds.add(r.itemId); });
      this._batchRecords.forEach(r  => { if (r.itemId) this._recordedIds.add(r.itemId); });
    } catch (e) {
      console.warn('Dashboard: failed to load from localStorage', e);
    }
  }

  _save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        singleRecords: this._singleRecords,
        batchRecords:  this._batchRecords,
        exports:       this._exports,
      }));
    } catch (e) {
      console.warn('Dashboard: failed to save to localStorage', e);
    }
  }

  // ── Public API ────────────────────────────────────────────────────────────

  recordDetection(imageName, count, itemId, source = 'single') {
    if (itemId && this._recordedIds.has(itemId)) return;
    if (itemId) this._recordedIds.add(itemId);

    const list = source === 'batch' ? this._batchRecords : this._singleRecords;
    const existing = list.find(r => r.imageName === imageName);
    if (existing) {
      existing.count = count;
    } else {
      list.push({ imageName, count, format: '—', itemId: itemId || null });
    }
    this._save();
    this._refreshIfVisible();
    window.dispatchEvent(new CustomEvent('dashboardStatsChanged'));
  }

  recordSave(filename, explicitFormat, itemId) {
    const format = explicitFormat || filename.split('.').pop().toUpperCase() || '—';
    const stem = filename.replace(/_output$/, '').replace(/\.[^/.]+$/, '');

    let detection = null;
    if (itemId) {
      detection = this._batchRecords.find(r => {
        const rStem = r.imageName.replace(/\.[^/.]+$/, '');
        return r.itemId === itemId || rStem === stem || r.imageName === filename;
      });
    } else {
      detection = this._singleRecords.find(r => {
        const rStem = r.imageName.replace(/\.[^/.]+$/, '');
        return r.imageName === filename || rStem === stem;
      }) || this._batchRecords.find(r => {
        const rStem = r.imageName.replace(/\.[^/.]+$/, '');
        return r.imageName === filename || rStem === stem;
      });
    }

    const count = detection ? detection.count : '—';
    if (detection) detection.format = format;
    this._exports.push({ filename, stem, count, format, timestamp: Date.now() });
    this._save();
    this._refreshIfVisible();
    window.dispatchEvent(new CustomEvent('dashboardStatsChanged'));
  }

  clearAll() {
    this._singleRecords = [];
    this._batchRecords  = [];
    this._exports       = [];
    this._recordedIds   = new Set();
    localStorage.removeItem(STORAGE_KEY);
    this._refreshIfVisible();
    window.dispatchEvent(new CustomEvent('dashboardStatsChanged'));
  }

  getStats() {
    const allRecords = [...this._singleRecords, ...this._batchRecords];
    const totalBuildings = allRecords.reduce(
      (s, r) => s + (typeof r.count === 'number' ? r.count : 0), 0
    );
    return {
      totalImages:   allRecords.length,
      activeBatches: 0,
      totalBuildings,
      totalExports:  this._exports.length
    };
  }

  // ── HTML ──────────────────────────────────────────────────────────────────

  _injectHTML() {
    try {
      const backdrop = document.createElement('div');
      backdrop.id = 'dashboard-backdrop';
      document.body.appendChild(backdrop);

      const panel = document.createElement('div');
      panel.id = 'dashboard-panel';
      panel.innerHTML = `
        <div class="db-header">
          <span class="db-title">Processing Log</span>
          <div style="display:flex;gap:8px;align-items:center;">
            <span id="db-session-time" style="font-size:0.8rem;color:#aaa;"></span>
            <button class="db-close" id="dashboard-close">&times;</button>
          </div>
        </div>
        <div class="db-body">
          <div id="db-records-list" class="db-list">
            <div class="db-empty">No images processed yet.</div>
          </div>
        </div>`;
      document.body.appendChild(panel);
    } catch (e) {
      console.error('Dashboard inject error:', e);
    }
  }

  _bindEvents() {
    try {
      const close    = document.getElementById('dashboard-close');
      const backdrop = document.getElementById('dashboard-backdrop');
      if (close)    close.addEventListener('click',    () => this._close());
      if (backdrop) backdrop.addEventListener('click', () => this._close());
    } catch (e) {
      console.error('Dashboard bind error:', e);
    }
  }

  // ── Timer ─────────────────────────────────────────────────────────────────

  _startTimer() {
    this._timerInterval = setInterval(() => {
      if (this._visible) this._updateTimer();
    }, 1000);
  }

  _updateTimer() {
    const el = document.getElementById('db-session-time');
    if (!el) return;
    const secs = Math.floor((Date.now() - this._sessionStart) / 1000);
    const h = String(Math.floor(secs / 3600)).padStart(2, '0');
    const m = String(Math.floor((secs % 3600) / 60)).padStart(2, '0');
    const s = String(secs % 60).padStart(2, '0');
    el.textContent = `${h}:${m}:${s}`;
  }

  // ── Open / Close ──────────────────────────────────────────────────────────

  _open() {
    this._visible = true;
    this._render();
    document.getElementById('dashboard-panel').classList.add('db-open');
    document.getElementById('dashboard-backdrop').classList.add('db-open');
  }

  _close() {
    this._visible = false;
    document.getElementById('dashboard-panel').classList.remove('db-open');
    document.getElementById('dashboard-backdrop').classList.remove('db-open');
  }

  _refreshIfVisible() { if (this._visible) this._render(); }

  // ── Render ────────────────────────────────────────────────────────────────

  _render() {
    this._updateTimer();
    const list = document.getElementById('db-records-list');
    if (!list) return;

    const renderTable = (records, emptyMsg) => {
      if (!records.length) return `<div class="db-empty">${emptyMsg}</div>`;
      return `
        <div class="db-table-header">
          <span>Image</span><span>Buildings</span><span>Export</span>
        </div>
        ${[...records].reverse().map(r => `
          <div class="db-list-row">
            <span class="db-list-name" title="${r.imageName}">${r.imageName}</span>
            <span class="db-list-badge">${r.count}</span>
            <span class="db-list-format db-list-format--${(r.format||'—').toLowerCase()}">${r.format}</span>
          </div>`).join('')}`;
    };

    list.innerHTML = `
      <div class="db-section-title" style="margin-top:0;">Single Processing</div>
      <div class="db-list" style="margin-bottom:12px;">
        ${renderTable(this._singleRecords, 'No single images processed yet.')}
      </div>
      <div class="db-section-title">Batch Processing</div>
      <div class="db-list">
        ${renderTable(this._batchRecords, 'No batch images processed yet.')}
      </div>`;
  }

  init() {
    this._injectHTML();
    this._bindEvents();
    this._startTimer();
  }
}
