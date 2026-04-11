/**
 * Dashboard stats — fetches /api/stats and renders Chart.js charts.
 * Called by index.js whenever the dashboard page is activated.
 */

let _modelChart = null;
let _timeChart = null;
let _exportChart = null;
let _singleChart = null;
let _batchChart = null;
let _sessionTimerInterval = null;
let _sessionStart = null;

// ── session tracking (localStorage) ──────────────────────────────────────────

const SESSION_KEY = 'bhumi_sessions_v1';

function _todayKey() {
  return new Date().toISOString().slice(0, 10); // "2026-04-10"
}

/** Load all sessions: { "2026-04-10": [{start: ms, end: ms}, ...], ... } */
function _loadSessions() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || '{}'); }
  catch { return {}; }
}

function _saveSessions(sessions) {
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(sessions)); }
  catch {}
}

/** Record that the current session is still alive (update end to now). */
function _tickSession() {
  if (!_sessionStart) return;
  const sessions = _loadSessions();
  const key = _todayKey();
  if (!sessions[key]) sessions[key] = [];
  // find the entry that matches this session start (within 2s tolerance)
  const entry = sessions[key].find(e => Math.abs(e.start - _sessionStart) < 2000);
  if (entry) {
    entry.end = Date.now();
  } else {
    sessions[key].push({ start: _sessionStart, end: Date.now() });
  }
  _saveSessions(sessions);
}

function _initSession() {
  if (_sessionStart) return;
  _sessionStart = Date.now();
  _tickSession();
  // persist every 10s so we don't lose time on hard close
  setInterval(_tickSession, 10_000);
}

const CYAN   = 'rgba(0, 217, 255, 0.85)';
const GREEN  = 'rgba(16, 185, 129, 0.85)';
const ORANGE = 'rgba(245, 158, 11, 0.85)';
const RED    = 'rgba(239, 68, 68, 0.85)';
const BLUE   = 'rgba(59, 130, 246, 0.85)';

// ── helpers ───────────────────────────────────────────────────────────────────

function _formatTs(isoStr) {
  if (!isoStr) return '—';
  try {
    return new Date(isoStr).toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
      hour12: false,
    });
  } catch { return isoStr; }
}

function _formatDuration(s) {
  if (!s) return '0s';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

// ── live session timer ────────────────────────────────────────────────────────

function _startSessionTimer(data) {
  if (_sessionTimerInterval) clearInterval(_sessionTimerInterval);
  _sessionTimerInterval = setInterval(() => {
    if (document.getElementById('timeChart')) {
      _buildTimeChart(data);
    } else {
      clearInterval(_sessionTimerInterval);
    }
  }, 1000);
}

// ── chart builders ────────────────────────────────────────────────────────────

function _buildModelChart(modelUsage) {
  const canvas = document.getElementById('modelChart');
  if (!canvas) return;

  const labels = Object.keys(modelUsage);
  const values = Object.values(modelUsage);

  if (_modelChart) _modelChart.destroy();

  if (!labels.length) {
    canvas.parentElement.innerHTML = '<p style="text-align:center;color:var(--text-tertiary);padding:2rem;">No model usage yet.</p>';
    return;
  }

  _modelChart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: [CYAN, GREEN, ORANGE, BLUE],
        borderWidth: 2,
        borderColor: '#151d2e',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#9ca3af', font: { size: 11 } } },
      },
    },
  });
}

function _buildTimeChart(_data) {
  const canvas = document.getElementById('timeChart');
  if (!canvas) return;

  // ── build 24 hourly buckets from today's sessions ─────────────────────
  const sessions = _loadSessions();
  const todaySessions = sessions[_todayKey()] || [];

  // minutesActive[h] = total minutes active in hour h (0–23)
  const minutesActive = new Array(24).fill(0);
  // tooltip: per-hour session ranges
  const hourRanges = Array.from({ length: 24 }, () => []);

  const now = Date.now();
  for (const s of todaySessions) {
    const start = s.start;
    const end   = Math.min(s.end || now, now);
    // walk through each minute of the session
    let cur = start;
    while (cur < end) {
      const d   = new Date(cur);
      const h   = d.getHours();
      const nextMin = new Date(cur);
      nextMin.setSeconds(0, 0);
      nextMin.setMinutes(nextMin.getMinutes() + 1);
      const chunk = Math.min(nextMin.getTime(), end) - cur;
      minutesActive[h] += chunk / 60000;
      cur = nextMin.getTime();
    }
    // record range label per hour
    const sh = new Date(start).getHours();
    const eh = new Date(end).getHours();
    const fmt = t => new Date(t).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
    for (let h = sh; h <= eh; h++) {
      if (minutesActive[h] > 0.1) {
        hourRanges[h].push(`${fmt(start)} – ${fmt(end)}`);
      }
    }
  }

  // detect light/dark theme
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const ACTIVE   = isLight ? 'rgba(2,132,199,0.85)' : CYAN;
  const INACTIVE = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.06)';
  const BORDER_ACTIVE   = isLight ? 'rgba(2,132,199,0.5)' : 'rgba(0,217,255,0.4)';
  const BORDER_INACTIVE = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.04)';

  const labels = Array.from({ length: 24 }, (_, h) => {
    const mins = Math.round(minutesActive[h]);
    return mins > 0
      ? `${String(h).padStart(2,'0')}:00  (${mins}m active)`
      : `${String(h).padStart(2,'0')}:00`;
  });

  const colors       = minutesActive.map(m => m > 0.1 ? ACTIVE   : INACTIVE);
  const borderColors = minutesActive.map(m => m > 0.1 ? BORDER_ACTIVE : BORDER_INACTIVE);

  if (_timeChart) _timeChart.destroy();

  _timeChart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: new Array(24).fill(1),   // equal slices — size = 1 hour each
        backgroundColor: colors,
        borderColor: borderColors,
        borderWidth: 1,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      rotation: -90,          // 12 o'clock = midnight (00:00)
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: ctx => labels[ctx[0].dataIndex],
            label: ctx => {
              const h = ctx.dataIndex;
              const mins = Math.round(minutesActive[h]);
              return mins > 0 ? ` Active: ${mins} min` : ' Not active';
            },
          },
        },
      },
    },
  });

  // ── legend: only active hours ─────────────────────────────────────────
  const legendEl = document.getElementById('timeChartLegend');
  if (!legendEl) return;

  const activeHours = minutesActive
    .map((m, h) => ({ h, mins: Math.round(m) }))
    .filter(x => x.mins > 0);

  if (!activeHours.length) {
    legendEl.innerHTML = '<span style="color:var(--text-tertiary);font-size:0.8rem;">No activity recorded today yet.</span>';
    return;
  }

  legendEl.innerHTML = activeHours.map(({ h, mins }) => {
    const dotColor = isLight ? 'rgba(2,132,199,0.85)' : CYAN;
    return `<span style="display:inline-flex;align-items:center;gap:5px;font-size:0.78rem;">
      <span style="width:10px;height:10px;border-radius:50%;background:${dotColor};flex-shrink:0;"></span>
      <strong style="color:var(--text-primary);">${String(h).padStart(2,'0')}:00</strong>
      <span style="color:var(--text-secondary);">${mins}m</span>
    </span>`;
  }).join('');
}

// ── export breakdown horizontal stacked bar ───────────────────────────────────

function _buildExportChart(breakdown) {
  const wrapper = document.getElementById('exportChartWrapper');
  const legendEl = document.getElementById('exportLegend');
  if (!wrapper) return;

  if (_exportChart) { _exportChart.destroy(); _exportChart = null; }

  const FORMAT_COLORS = {
    json:    '#4caf50',
    geojson: '#ab47bc',
    png:     '#42a5f5',
    jpeg:    '#26c6da',
    jpg:     '#26c6da',
  };

  const entries = Object.entries(breakdown).filter(([, v]) => v > 0);

  if (!entries.length) {
    wrapper.innerHTML = '<p style="text-align:center;color:var(--text-tertiary);font-size:0.8rem;padding:1.5rem 0;">No exports yet.</p>';
    if (legendEl) legendEl.innerHTML = '';
    return;
  }

  // always recreate canvas so we never lose it
  wrapper.innerHTML = '<canvas id="exportCanvas"></canvas>';
  const canvas = document.getElementById('exportCanvas');

  const total = entries.reduce((s, [, v]) => s + v, 0);

  _exportChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: [''],
      datasets: entries.map(([fmt, count]) => ({
        label: fmt.toUpperCase(),
        data: [count],
        backgroundColor: FORMAT_COLORS[fmt] || 'rgba(156,163,175,0.7)',
        borderRadius: 4,
        borderSkipped: false,
      })),
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} (${Math.round(ctx.raw / total * 100)}%)`,
          },
        },
      },
      scales: {
        x: { stacked: true, display: false },
        y: { stacked: true, display: false },
      },
    },
  });

  if (legendEl) {
    legendEl.innerHTML = entries.map(([fmt, count]) => {
      const color = FORMAT_COLORS[fmt] || 'rgba(156,163,175,0.7)';
      const pct   = Math.round(count / total * 100);
      return `<span style="display:inline-flex;align-items:center;gap:5px;">
        <span style="width:10px;height:10px;border-radius:2px;background:${color};flex-shrink:0;"></span>
        <span style="color:var(--text-secondary);">${fmt.toUpperCase()}</span>
        <strong style="color:var(--text-primary);">${count}</strong>
        <span style="color:var(--text-tertiary);">(${pct}%)</span>
      </span>`;
    }).join('');
  }
}

// ── single / batch bar charts ─────────────────────────────────────────────────

function _buildProcessingChart(canvasId, rows, chartRef, color, emptyMsg) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return chartRef;

  if (chartRef) chartRef.destroy();

  if (!rows.length) {
    canvas.parentElement.innerHTML =
      `<p style="text-align:center;color:var(--text-tertiary);padding:3rem 1rem;font-size:0.85rem;">${emptyMsg}</p>`;
    return null;
  }

  const labels = rows.map(r => {
    const name = r.filename.replace(/\.[^.]+$/, ''); // strip extension
    return name.length > 14 ? name.slice(0, 12) + '…' : name;
  });
  const values = rows.map(r => r.building_count);

  return new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Buildings',
        data: values,
        backgroundColor: color,
        borderRadius: 4,
        borderSkipped: false,
        barThickness: 40,
        maxBarThickness: 60,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (ctx) => rows[ctx[0].dataIndex].filename,
            label: (ctx) => ` ${ctx.raw} buildings`,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: '#6b7280', font: { size: 10 }, maxRotation: 45 },
          grid: { display: false },
        },
        y: {
          beginAtZero: true,
          ticks: { color: '#6b7280', stepSize: 1 },
          grid: { color: 'rgba(128,128,128,0.1)' },
        },
      },
    },
  });
}

// ── per-image table ───────────────────────────────────────────────────────────

const FMT_COLORS = {
  json:    { bg: 'rgba(46,125,50,0.15)',   color: '#4caf50' },
  geojson: { bg: 'rgba(2,119,189,0.15)',   color: '#29b6f6' },
  png:     { bg: 'rgba(21,101,192,0.15)',  color: '#42a5f5' },
  jpeg:    { bg: 'rgba(230,81,0,0.15)',    color: '#ffa726' },
  jpg:     { bg: 'rgba(230,81,0,0.15)',    color: '#ffa726' },
};

function _fmtBadge(fmt) {
  if (!fmt || fmt === '—') return '<span style="color:var(--text-tertiary);">—</span>';
  const key = fmt.toLowerCase();
  const c = FMT_COLORS[key] || { bg: 'rgba(255,255,255,0.08)', color: 'var(--text-secondary)' };
  return `<span style="background:${c.bg};color:${c.color};padding:2px 8px;border-radius:8px;font-size:0.75rem;font-weight:700;text-transform:uppercase;">${fmt}</span>`;
}

function _renderImageRows(rows) {
  const tbody = document.getElementById('activityFeed');
  if (!tbody) return;

  if (!rows || !rows.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-tertiary);">No images processed yet.</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td style="color:var(--text-tertiary);white-space:nowrap;font-size:0.8rem;">${_formatTs(r.ts)}</td>
      <td style="font-weight:500;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${r.filename}">${r.filename}</td>
      <td style="color:var(--text-secondary);font-size:0.8rem;">${r.model || '—'}</td>
      <td style="color:var(--primary-cyan);font-weight:700;">${r.building_count}</td>
      <td>${_fmtBadge(r.export_format)}</td>
    </tr>`).join('');
}

// ── stat cards ────────────────────────────────────────────────────────────────

function _renderStats(data) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('statTotalImages',   data.total_images_processed ?? '—');
  set('statAvgTime',       data.avg_processing_time_s != null ? `${data.avg_processing_time_s}s` : '—');
  set('statTotalAppTime',  _formatDuration(data.total_app_time_s));
  const rangeEl = document.getElementById('statAppTimeRange');
  if (rangeEl) rangeEl.textContent = data.first_seen && data.last_seen
    ? `${_formatTs(data.first_seen)} → ${_formatTs(data.last_seen)}`
    : '';
}

// ── public ────────────────────────────────────────────────────────────────────

export async function loadDashboardStats() {
  _initSession();

  // redraw the clock chart every minute so the current session arc grows
  if (!_sessionTimerInterval) {
    _sessionTimerInterval = setInterval(() => {
      _tickSession();
      _buildTimeChart(null);
    }, 60_000);
  }

  try {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    _renderStats(data);
    _buildModelChart(data.model_usage || {});
    _buildTimeChart(data);
    _buildExportChart(data.export_breakdown || {});

    const singleRows = (data.image_rows || []).filter(r => r.source === 'single');
    const batchRows  = (data.image_rows || []).filter(r => r.source === 'batch');

    // deduplicate by filename — keep the entry with the highest building_count
    const dedupe = rows => {
      const map = new Map();
      for (const r of rows) {
        const key = r.filename;
        if (!map.has(key) || r.building_count > map.get(key).building_count) {
          map.set(key, r);
        }
      }
      return [...map.values()];
    };

    _singleChart = _buildProcessingChart('singleChart', dedupe(singleRows), _singleChart, GREEN,  'No single images processed yet.');
    _batchChart  = _buildProcessingChart('batchChart',  dedupe(batchRows),  _batchChart,  CYAN,   'No batch images processed yet.');

    _renderImageRows(data.image_rows || []);
  } catch (err) {
    console.warn('Dashboard stats fetch failed:', err);
    const tbody = document.getElementById('activityFeed');
    if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--status-error);">Could not load stats: ${err.message}</td></tr>`;
  }
}
