/**
 * Dashboard — shows image name, buildings detected, and export format.
 */
export class Dashboard {
  constructor() {
    this._sessionStart  = Date.now();
    this._singleRecords = [];   // { imageName, count, format } — single processing
    this._batchRecords  = [];   // { imageName, count, format, itemId } — batch processing
    this._exports       = [];   // { filename, base, count, format } — downloads
    this._recordedIds   = new Set();
    this._timerInterval = null;
    this._visible       = false;
  }

  init() {
    this._injectHTML();
    this._bindEvents();
    this._startTimer();
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
    this._refreshIfVisible();
    window.dispatchEvent(new CustomEvent('dashboardStatsChanged'));
  }

  recordSave(filename, explicitFormat, itemId) {
    const format = explicitFormat || filename.split('.').pop().toUpperCase() || '—';
    const stem = filename.replace(/_output$/, '').replace(/\.[^/.]+$/, '');

    // If itemId provided, it's a batch item — search batch records only
    let detection = null;
    if (itemId) {
      detection = this._batchRecords.find(r => {
        const rStem = r.imageName.replace(/\.[^/.]+$/, '');
        return r.itemId === itemId || rStem === stem || r.imageName === filename;
      });
    } else {
      // Single processing — search single records first, then batch
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
}
