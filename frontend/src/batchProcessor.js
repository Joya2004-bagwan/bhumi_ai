/**
 * BatchProcessor — ZIP upload, batch segmentation, per-image polygon editing, bulk download.
 * Follows the same patterns as imageUploader.js, segmentationRunner.js, gptBoundaryDetector.js
 */
import { BatchItemEditor } from './batchPolygonEditor.js';

export class BatchProcessor {
  constructor(modelSelector) {
    this._modelSelector = modelSelector;
    this._batchId       = null;
    this._items         = [];
    this._pollTimer     = null;
    this._editedItems   = new Set();
    this._activeEditor  = null;
    this._selectedModel = null;
    this._hasWorldfiles = false;
  }

  init() {
    console.log('🔄 BatchProcessor.init() - VERSION 2.0 - COMPACT GRID');
    this._section = document.getElementById('batchProcessingContent');
    if (!this._section) {
      // Fallback to old ID for compatibility
      this._section = document.getElementById('batch-content');
    }
    if (!this._section) return;
    this._section.innerHTML = this._html();
    this._bindEvents();
  }

  _html() {
    return `
      <!-- Step 1: Upload Images -->
      <div class="bp-step-card" id="bp-step-images">
        <div class="bp-step-header">
          <div class="bp-step-number">1</div>
          <div class="bp-step-info">
            <span class="bp-step-title">Images ZIP</span>
            <span class="bp-step-hint">Max 50 images · 500 MB · JPG, PNG, TIFF</span>
          </div>
          <div id="bp-images-badge" class="bp-step-badge" style="display:none;"></div>
        </div>
        <div class="bp-dropzone" id="bp-images-dropzone">
          <div class="bp-dropzone-icon">🗂️</div>
          <div class="bp-dropzone-text">Drop your images ZIP here</div>
          <div class="bp-dropzone-sub">or</div>
          <label class="bp-file-label">
            Browse File
            <input type="file" id="batch-zip-input" accept=".zip" style="display:none;" />
          </label>
        </div>
        <div id="batch-upload-status" class="bp-status"></div>
        <div id="batch-file-list" class="batch-file-list" style="display:none;"></div>
        <button id="batch-upload-btn" class="bp-upload-btn" style="display:none;">Upload ZIP</button>
      </div>

      <!-- Step 2: World Files (revealed after images upload) -->
      <div class="bp-step-card bp-step-optional" id="batch-worldfiles-row" style="display:none;">
        <div class="bp-step-header">
          <div class="bp-step-number bp-step-number--opt">2</div>
          <div class="bp-step-info">
            <span class="bp-step-title">World Files ZIP <span class="bp-optional-tag">optional</span></span>
            <span class="bp-step-hint">.pgw / .tfw / .jgw / .wld — enables GeoJSON export</span>
          </div>
          <div id="bp-wf-badge" class="bp-step-badge" style="display:none;"></div>
        </div>
        <div class="bp-dropzone bp-dropzone--secondary" id="bp-wf-dropzone">
          <div class="bp-dropzone-icon">🌐</div>
          <div class="bp-dropzone-text">Drop world files ZIP here</div>
          <div class="bp-dropzone-sub">or</div>
          <label class="bp-file-label bp-file-label--secondary">
            Browse File
            <input type="file" id="batch-wf-zip-input" accept=".zip" style="display:none;" />
          </label>
        </div>
        <div id="batch-wf-status" class="bp-status"></div>
        <button id="batch-wf-upload-btn" class="bp-upload-btn bp-upload-btn--secondary" style="display:none;">Upload World Files</button>
      </div>

      <!-- Step 3: Model -->
      <div class="bp-step-card" id="bp-step-model">
        <div class="bp-step-header">
          <div class="bp-step-number">3</div>
          <div class="bp-step-info">
            <span class="bp-step-title">Select Model</span>
            <span class="bp-step-hint">Choose the AI model for building detection</span>
          </div>
        </div>
        <div class="bp-model-grid">
          <div class="bp-model-card" data-model="yolov8m-custom">
            <div class="bp-model-icon">⚡</div>
            <div class="bp-model-body">
              <div class="bp-model-name">YOLOv8</div>
              <div class="bp-model-desc">Fast · Dense urban areas</div>
            </div>
            <div class="bp-model-radio"></div>
          </div>
          <div class="bp-model-card" data-model="maskrcnn-custom">
            <div class="bp-model-icon">🔬</div>
            <div class="bp-model-body">
              <div class="bp-model-name">Mask R-CNN</div>
              <div class="bp-model-desc">Precise · Complex boundaries</div>
            </div>
            <div class="bp-model-radio"></div>
          </div>
        </div>
        <!-- hidden select kept for JS compatibility -->
        <select id="batch-model-select" style="display:none;">
          <option value="">-- Choose a model --</option>
          <option value="yolov8m-custom">YOLOv8</option>
          <option value="maskrcnn-custom">Mask R-CNN</option>
        </select>
      </div>

      <!-- Run -->
      <div class="bp-run-row">
        <button id="batch-run-btn" class="bp-run-btn" disabled>
          <span class="bp-run-icon">🏗️</span> Detect Buildings
        </button>
        <div id="batch-run-status" class="bp-status"></div>
      </div>

      <!-- Loading bar -->
      <div id="batch-loading" class="bp-loading" style="display:none;">
        <div class="bp-loading-bar"><div class="bp-loading-fill"></div></div>
        <span id="batch-loading-text" class="bp-loading-text">Processing images...</span>
      </div>

      <!-- Results grid -->
      <div id="batch-grid" class="batch-grid" style="display:none;"></div>
      <div id="batch-editor-area"></div>

      <!-- Download row -->
      <div class="bp-download-row" id="batch-download-row" style="display:none;">
        <span class="bp-download-label">Export as</span>
        <div class="bp-format-pills">
          <label class="bp-format-pill">
            <input type="radio" name="bp-format" value="json" checked /> JSON
          </label>
          <label class="bp-format-pill">
            <input type="radio" name="bp-format" value="png" /> PNG
          </label>
          <label class="bp-format-pill">
            <input type="radio" name="bp-format" value="jpeg" /> JPEG
          </label>
          <label class="bp-format-pill" id="bp-geojson-pill">
            <input type="radio" name="bp-format" value="geojson" id="batch-geojson-option" disabled /> GeoJSON
          </label>
        </div>
        <!-- hidden select kept for JS compat -->
        <select id="batch-format-select" style="display:none;">
          <option value="json">JSON</option>
          <option value="png">PNG</option>
          <option value="jpeg">JPEG</option>
          <option value="geojson">GeoJSON</option>
        </select>
        <button id="batch-download-btn" class="bp-dl-btn" disabled>
          ⬇ Download All
        </button>
      </div>

      <div id="batch-error" class="batch-error" style="display:none;"></div>`;
  }

  _bindEvents() {
    // ── Images ZIP ──────────────────────────────────────────────────────
    const imgInput = document.getElementById('batch-zip-input');
    const imgDropzone = document.getElementById('bp-images-dropzone');

    imgInput.onchange = () => { if (imgInput.files[0]) this._uploadZip(imgInput.files[0]); };
    document.getElementById('batch-upload-btn').onclick = () => { if (imgInput.files[0]) this._uploadZip(imgInput.files[0]); };

    imgDropzone.addEventListener('dragover', e => { e.preventDefault(); imgDropzone.classList.add('bp-dropzone--over'); });
    imgDropzone.addEventListener('dragleave', () => imgDropzone.classList.remove('bp-dropzone--over'));
    imgDropzone.addEventListener('drop', e => {
      e.preventDefault(); imgDropzone.classList.remove('bp-dropzone--over');
      const f = e.dataTransfer.files[0]; if (f) this._uploadZip(f);
    });

    // ── World Files ZIP ─────────────────────────────────────────────────
    const wfInput = document.getElementById('batch-wf-zip-input');
    const wfDropzone = document.getElementById('bp-wf-dropzone');

    wfInput.onchange = () => { if (wfInput.files[0]) this._uploadWorldfilesZip(wfInput.files[0]); };
    document.getElementById('batch-wf-upload-btn').onclick = () => { if (wfInput.files[0]) this._uploadWorldfilesZip(wfInput.files[0]); };

    wfDropzone.addEventListener('dragover', e => { e.preventDefault(); wfDropzone.classList.add('bp-dropzone--over'); });
    wfDropzone.addEventListener('dragleave', () => wfDropzone.classList.remove('bp-dropzone--over'));
    wfDropzone.addEventListener('drop', e => {
      e.preventDefault(); wfDropzone.classList.remove('bp-dropzone--over');
      const f = e.dataTransfer.files[0]; if (f) this._uploadWorldfilesZip(f);
    });

    // ── Model cards ─────────────────────────────────────────────────────
    document.querySelectorAll('.bp-model-card').forEach(card => {
      card.addEventListener('click', () => {
        document.querySelectorAll('.bp-model-card').forEach(c => c.classList.remove('bp-model-card--selected'));
        card.classList.add('bp-model-card--selected');
        this._selectedModel = card.dataset.model;
        // keep hidden select in sync
        const sel = document.getElementById('batch-model-select');
        if (sel) sel.value = this._selectedModel;
        this._updateRunBtn();
      });
    });

    // ── Format pills → keep hidden select in sync ───────────────────────
    document.querySelectorAll('input[name="bp-format"]').forEach(radio => {
      radio.addEventListener('change', () => {
        const sel = document.getElementById('batch-format-select');
        if (sel) sel.value = radio.value;
      });
    });

    document.getElementById('batch-run-btn').onclick = () => this._runBatch();
    document.getElementById('batch-download-btn').onclick = () => {
      const checked = document.querySelector('input[name="bp-format"]:checked');
      this._downloadAll(checked ? checked.value : 'json');
    };
    window.addEventListener('modelSelected', () => this._updateRunBtn());
  }

  // ── Upload ────────────────────────────────────────────────────────────────

  async _uploadZip(file) {
    if (!file.name.toLowerCase().endsWith('.zip')) {
      return this._showError('Please select a .zip file.');
    }
    this._setUploadStatus(`Uploading ${file.name} (${this._fmtSize(file.size)})…`);

    const fd = new FormData();
    fd.append('file', file);
    try {
      const res  = await fetch('/api/batch/upload-zip', { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      this._batchId = data.batch_id;
      this._setUploadStatus('');
      // Update badge
      const badge = document.getElementById('bp-images-badge');
      if (badge) { badge.textContent = `✓ ${data.total} image${data.total !== 1 ? 's' : ''}`; badge.style.display = 'inline-flex'; }
      // Collapse dropzone, show file chips
      const dz = document.getElementById('bp-images-dropzone');
      if (dz) dz.style.display = 'none';
      this._renderFileList(data.filenames);
      // Reveal world files row
      const wfRow = document.getElementById('batch-worldfiles-row');
      if (wfRow) wfRow.style.display = 'block';
      this._updateRunBtn();
    } catch (e) {
      this._setUploadStatus('');
      this._showError(`Upload failed: ${e.message}`);
    }
  }

  async _uploadWorldfilesZip(file) {
    if (!file.name.toLowerCase().endsWith('.zip')) {
      return this._showError('Please select a .zip file for world files.');
    }
    if (!this._batchId) {
      return this._showError('Upload an images ZIP first.');
    }
    this._setWfStatus(`Uploading ${file.name}…`);
    document.getElementById('batch-wf-upload-btn').disabled = true;

    const fd = new FormData();
    fd.append('file', file);
    try {
      const res  = await fetch(`/api/batch/${this._batchId}/upload-worldfiles-zip`, { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'World files upload failed');
      this._hasWorldfiles = true;
      this._setWfStatus('');
      // Update badge
      const badge = document.getElementById('bp-wf-badge');
      if (badge) {
        badge.textContent = data.unmatched > 0
          ? `✓ ${data.matched} matched · ${data.unmatched} unmatched`
          : `✓ ${data.matched} matched`;
        badge.style.display = 'inline-flex';
      }
      // Collapse dropzone
      const dz = document.getElementById('bp-wf-dropzone');
      if (dz) dz.style.display = 'none';
      // Enable GeoJSON pill
      const geoInput = document.getElementById('batch-geojson-option');
      if (geoInput) geoInput.disabled = false;
      const geoPill = document.getElementById('bp-geojson-pill');
      if (geoPill) geoPill.classList.remove('bp-format-pill--disabled');
    } catch (e) {
      this._setWfStatus('');
      this._showError(`World files upload failed: ${e.message}`);
    } finally {
      document.getElementById('batch-wf-upload-btn').disabled = false;
    }
  }

  _renderFileList(filenames) {
    const el = document.getElementById('batch-file-list');
    el.style.display = 'block';
    el.innerHTML = filenames.map(f => `<span class="batch-file-chip">${f}</span>`).join('');
  }

  // ── Run ───────────────────────────────────────────────────────────────────

  async _runBatch() {
    const model = this._selectedModel;
    if (!model || !this._batchId) {
      this._showError('Please select a model and upload a ZIP file first.');
      return;
    }
    document.getElementById('batch-run-btn').disabled = true;
    this._setRunStatus('');
    this._showBatchLoading(true, 'Starting detection...');
    this._hideError();
    try {
      const res  = await fetch(`/api/batch/${this._batchId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start batch');
      this._startPolling();
    } catch (e) {
      this._showError(`Failed to start: ${e.message}`);
      this._showBatchLoading(false);
      document.getElementById('batch-run-btn').disabled = false;
    }
  }

  // ── Polling ───────────────────────────────────────────────────────────────

  _startPolling() {
    if (this._pollTimer) clearInterval(this._pollTimer);
    this._pollFailures = 0;
    this._pollTimer = setInterval(() => this._pollStatus(), 2000);
  }

  async _pollStatus() {
    if (!this._batchId) return;
    try {
      const res  = await fetch(`/api/batch/${this._batchId}/status`);
      const data = await res.json();
      if (!res.ok) return;
      this._pollFailures = 0;
      this._items = data.items;
      if (data.has_worldfiles) this._hasWorldfiles = true;
      const done = data.done, total = data.total;
      this._showBatchLoading(true, `Detecting buildings… ${done}/${total} images`);
      this._renderGrid(data.items);
      if (data.status === 'complete' || data.status === 'failed') {
        clearInterval(this._pollTimer);
        this._pollTimer = null;
        this._showBatchLoading(false);
        this._setRunStatus(`Done — ${data.done} succeeded, ${data.failed} failed`);
        this._showDownloadRow(data.done > 0);
        // Notify dashboard for each completed item (only once, on job finish)
        data.items.filter(i => i.status === 'done').forEach(i => {
          window.dispatchEvent(new CustomEvent('gptDetectionComplete', {
            detail: { imageName: i.original_filename, count: i.building_count, itemId: i.item_id }
          }));
        });
      }
    } catch (_) {
      this._pollFailures++;
      if (this._pollFailures >= 3) {
        clearInterval(this._pollTimer);
        this._pollTimer = null;
        this._showBatchLoading(false);
        this._showError('Lost connection to server. Please check the backend is running and refresh.');
      }
    }
  }

  // ── Thumbnail grid ────────────────────────────────────────────────────────

  _renderGrid(items) {
    console.log('🎨 Rendering grid with', items.length, 'items - COMPACT VERSION 2.0');
    const grid = document.getElementById('batch-grid');
    grid.style.display = 'grid';
    const scrollY = grid.scrollTop;
    grid.innerHTML = '';
    items.forEach(item => {
      const edited = this._editedItems.has(item.item_id);
      const card   = document.createElement('div');
      card.className = `batch-card batch-card--${item.status}`;

      // Filename header
      const nameHeader = document.createElement('div');
      nameHeader.className = 'batch-card-name';
      nameHeader.textContent = item.original_filename;
      nameHeader.title = item.original_filename;
      card.appendChild(nameHeader);

      // Thumbnail canvas (only for done items)
      const thumbWrap = document.createElement('div');
      thumbWrap.className = 'batch-card-thumb';
      if (item.status === 'done') {
        const canvas = document.createElement('canvas');
        // Don't set CSS width/height - let the container control size via CSS
        thumbWrap.appendChild(canvas);
        this._drawThumb(canvas, item);
        
        // Add click to expand functionality
        thumbWrap.onclick = (e) => {
          e.stopPropagation();
          this._expandImage(item);
        };
      } else {
        const statusLabel = document.createElement('div');
        statusLabel.style.cssText = 'color: var(--text-light); font-size: 0.8rem; text-align: center;';
        statusLabel.textContent = item.status === 'processing' ? 'Processing...' : 'Pending';
        thumbWrap.appendChild(statusLabel);
      }
      card.appendChild(thumbWrap);

      const footer = document.createElement('div');
      footer.className = 'batch-card-footer';
      footer.innerHTML = `
        <span class="batch-status-badge batch-status--${item.status}">${item.status}</span>
        ${edited ? '<span class="batch-edited-badge">edited</span>' : ''}
        ${item.status === 'done' ? `<span class="batch-building-count">${item.building_count} bldg</span>` : ''}
        ${item.status === 'done' ? `<button class="batch-edit-btn">Edit</button>` : ''}
        ${item.status === 'failed' ? `<button class="batch-retry-btn">Retry</button>` : ''}`;
      card.appendChild(footer);

      if (item.status === 'failed') {
        const errDiv = document.createElement('div');
        errDiv.className = 'batch-item-error';
        errDiv.textContent = item.error;
        card.appendChild(errDiv);
      }

      if (item.status === 'done')
        footer.querySelector('.batch-edit-btn').onclick  = () => this._openEditor(item);
      if (item.status === 'failed')
        footer.querySelector('.batch-retry-btn').onclick = () => this._retryItem(item.item_id);

      grid.appendChild(card);
    });
    grid.scrollTop = scrollY;
  }

  _drawThumb(canvas, item) {
    const imageUrl = `/api/batch/${this._batchId}/items/${item.item_id}/image`;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      // Use a higher resolution for sharper thumbnails
      const maxSize = 500;
      const scale = Math.min(maxSize / img.naturalWidth, maxSize / img.naturalHeight);
      canvas.width = img.naturalWidth * scale;
      canvas.height = img.naturalHeight * scale;
      
      const ctx = canvas.getContext('2d');
      // Enable image smoothing for better quality
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Draw polygons scaled to thumbnail size
      const polygons = item.polygons || [];
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = Math.max(2, canvas.width / 150);
      ctx.fillStyle = 'rgba(0,255,0,0.15)';
      polygons.forEach(poly => {
        const pts = poly.points || poly.coordinates || (Array.isArray(poly[0]) ? poly : []);
        if (!pts || pts.length < 2) return;
        ctx.beginPath();
        ctx.moveTo(pts[0][0] * scale, pts[0][1] * scale);
        for (let i = 1; i < pts.length; i++) {
          ctx.lineTo(pts[i][0] * scale, pts[i][1] * scale);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      });
    };
    img.src = imageUrl;
  }

  // ── Per-image inline editor (same pattern as gptBoundaryDetector.js) ──────

  _expandImage(item) {
    // Create modal overlay for full-size preview
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.95);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    `;
    
    const container = document.createElement('div');
    container.style.cssText = `
      position: relative;
      max-width: 95vw;
      max-height: 95vh;
      display: flex;
      flex-direction: column;
      background: white;
      border-radius: 8px;
      overflow: hidden;
    `;
    
    // Header with filename and close button
    const header = document.createElement('div');
    header.style.cssText = `
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: var(--geo-navy);
      color: white;
    `;
    header.innerHTML = `
      <span style="font-weight: 600; font-size: 0.9rem;">${item.original_filename} - ${item.building_count} buildings</span>
      <button id="modal-close-btn" style="background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; padding: 0 8px; line-height: 1;">✕</button>
    `;
    
    // Image container
    const imgContainer = document.createElement('div');
    imgContainer.style.cssText = `
      flex: 1;
      overflow: auto;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #111;
      padding: 20px;
    `;
    
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'max-width: 100%; max-height: 80vh; object-fit: contain;';
    imgContainer.appendChild(canvas);
    
    container.appendChild(header);
    container.appendChild(imgContainer);
    modal.appendChild(container);
    document.body.appendChild(modal);
    
    // Draw full-size image with polygons
    const imageUrl = `/api/batch/${this._batchId}/items/${item.item_id}/image`;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      
      // Draw polygons
      const polygons = item.polygons || [];
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = Math.max(3, img.naturalWidth / 300);
      ctx.fillStyle = 'rgba(0,255,0,0.2)';
      polygons.forEach(poly => {
        const pts = poly.points || poly.coordinates || (Array.isArray(poly[0]) ? poly : []);
        if (!pts || pts.length < 2) return;
        ctx.beginPath();
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (let i = 1; i < pts.length; i++) {
          ctx.lineTo(pts[i][0], pts[i][1]);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      });
    };
    img.src = imageUrl;
    
    // Close handlers
    const closeModal = () => modal.remove();
    header.querySelector('#modal-close-btn').onclick = closeModal;
    modal.onclick = (e) => {
      if (e.target === modal) closeModal();
    };
    document.addEventListener('keydown', function escHandler(e) {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', escHandler);
      }
    });
  }

  _openEditor(item) {
    // Close any existing editor
    const area = document.getElementById('batch-editor-area');
    area.innerHTML = '';
    this._activeEditor = null;

    // Show the editor area (full screen overlay)
    area.classList.add('active');
    
    // Hide the grid while editing
    const grid = document.getElementById('batch-grid');
    if (grid) grid.style.display = 'none';

    const imageUrl = `/api/batch/${this._batchId}/items/${item.item_id}/image`;
    const editor   = new BatchItemEditor({
      container : area,
      imageUrl,
      polygons  : (item.polygons || []).map(p => {
        // normalise: support {points:[...]}, {coordinates:[...]}, or raw [[x,y],...]
        if (Array.isArray(p) && Array.isArray(p[0])) return [...p];
        return (p.points || p.coordinates || []).map(pt => [...pt]);
      }),
      filename  : item.original_filename,
      onSave    : (polygons) => this._saveEdits(item.item_id, polygons),
      onClose   : () => { 
        area.innerHTML = ''; 
        area.classList.remove('active');
        this._activeEditor = null;
        // Show the grid again
        if (grid) grid.style.display = 'grid';
      },
    });
    editor.build();
    this._activeEditor = editor;
  }

  async _saveEdits(itemId, polygons) {
    try {
      await fetch(`/api/batch/${this._batchId}/items/${itemId}/polygons`, {
        method : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body   : JSON.stringify({ polygons }),
      });
      const item = this._items.find(i => i.item_id === itemId);
      if (item) { item.polygons = polygons; item.building_count = polygons.length; }
      this._editedItems.add(itemId);
      this._renderGrid(this._items);
    } catch (e) {
      this._showError(`Failed to save edits: ${e.message}`);
    }
  }

  // ── Retry ─────────────────────────────────────────────────────────────────

  async _retryItem(itemId) {
    try {
      await fetch(`/api/batch/${this._batchId}/items/${itemId}/retry`, { method: 'POST' });
      this._startPolling();
    } catch (e) {
      this._showError(`Retry failed: ${e.message}`);
    }
  }

  // ── Download ──────────────────────────────────────────────────────────────

  async _downloadAll(format) {
    const btn = document.getElementById('batch-download-btn');
    btn.disabled    = true;
    btn.textContent = 'Preparing…';
    try {
      const res = await fetch(`/api/batch/${this._batchId}/download?format=${format}`);
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Download failed');
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = `batch_results.zip`; a.click();
      URL.revokeObjectURL(url);
      // Fire fileSaved for each processed image with the selected format
      this._items.filter(i => i.status === 'done').forEach(i => {
        const stem = i.original_filename.replace(/\.[^/.]+$/, '');
        window.dispatchEvent(new CustomEvent('fileSaved', {
          detail: { filename: `${stem}_output`, format: format.toUpperCase(), itemId: i.item_id }
        }));
      });
    } catch (e) {
      this._showError(`Download failed: ${e.message}`);
    } finally {
      btn.disabled    = false;
      btn.textContent = 'Download All';
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  _updateRunBtn() {
    // Use the selected model from dropdown
    const btn = document.getElementById('batch-run-btn');
    if (btn) btn.disabled = !(this._batchId && this._selectedModel);
  }

  _showDownloadRow(hasDone) {
    const row = document.getElementById('batch-download-row');
    if (row) row.style.display = 'flex';
    const btn = document.getElementById('batch-download-btn');
    if (btn) btn.disabled = !hasDone;
    if (this._hasWorldfiles) {
      const geoInput = document.getElementById('batch-geojson-option');
      if (geoInput) geoInput.disabled = false;
      const geoPill = document.getElementById('bp-geojson-pill');
      if (geoPill) geoPill.classList.remove('bp-format-pill--disabled');
    }
  }

  _setUploadStatus(msg) { const el = document.getElementById('batch-upload-status'); if (el) el.textContent = msg; }
  _setRunStatus(msg)    { const el = document.getElementById('batch-run-status');    if (el) el.textContent = msg; }
  _setWfStatus(msg)     { const el = document.getElementById('batch-wf-status');     if (el) el.textContent = msg; }

  _showBatchLoading(visible, message) {
    const el = document.getElementById('batch-loading');
    if (!el) return;
    if (visible) {
      const txt = document.getElementById('batch-loading-text');
      if (txt) txt.textContent = message || 'Processing...';
      el.style.display = 'block';
    } else {
      el.style.display = 'none';
    }
  }

  _showError(msg) {
    const el = document.getElementById('batch-error');
    if (!el) return;
    el.textContent  = msg;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 6000);
  }

  _hideError() { const el = document.getElementById('batch-error'); if (el) el.style.display = 'none'; }
  _fmtSize(b)  { return b < 1048576 ? (b/1024).toFixed(1)+' KB' : (b/1048576).toFixed(1)+' MB'; }
}
