/**
 * GPTBoundaryDetector
 * Features:
 *   - Static overlay view with Save button (JSON / PNG / JPEG)
 *     Output filename: {original_name}_output.{ext}
 *   - Edit mode: drag vertices, draw new polygons, delete polygons
 */
export class GPTBoundaryDetector {
  constructor(imageUploader, modelSelector) {
    this.imageUploader = imageUploader;
    this.modelSelector = modelSelector;

    this._polygons     = [];
    this._overlayB64   = null;
    this._imageUrl     = null;
    this._editMode     = false;
    this._drawMode     = false;
    this._drawPoints   = [];
    this._dragState    = null;
    this._svg          = null;
    this._imgW         = 0;
    this._imgH         = 0;
    this._selectedPoly = null;

    // Don't store references in constructor - get them when needed
    this._setupButtonListeners();
  }

  _setupButtonListeners() {
    // Use event delegation on document to avoid issues with element references
    document.addEventListener('click', (e) => {
      if (e.target.id === 'gpt-boundary-button' || e.target.closest('#gpt-boundary-button')) {
        console.log('GPT Boundary button clicked');
        this._runDetection();
      }
      if (e.target.id === 'gpt-edit-button' || e.target.closest('#gpt-edit-button')) {
        console.log('GPT Edit button clicked');
        this._enterEditMode();
      }
      if (e.target.id === 'gpt-done-button' || e.target.closest('#gpt-done-button')) {
        console.log('GPT Done button clicked');
        this._exitEditMode();
      }
    });
  }
  
  // Helper methods to get elements when needed
  _getGptPanel() {
    return document.getElementById('gpt-panel');
  }
  
  _getGptPanelWrap() {
    return document.getElementById('gpt-panel-wrapper');
  }
  
  _getGptStatus() {
    return document.getElementById('gpt-status');
  }
  
  _getGptInfoBar() {
    return document.getElementById('gpt-info-bar');
  }
  
  _getEditBar() {
    return document.getElementById('gpt-edit-bar');
  }
  
  _getEditBtn() {
    return document.getElementById('gpt-edit-button');
  }
  
  _getDoneBtn() {
    return document.getElementById('gpt-done-button');
  }
  
  _getGptBtn() {
    return document.getElementById('gpt-boundary-button');
  }

  // ── Filename helper ────────────────────────────────────────────────────────

  _baseName() {
    const name = (this.imageUploader && this.imageUploader.getOriginalFilename)
      ? this.imageUploader.getOriginalFilename()
      : 'output';
    // Strip extension so download methods can append the correct one
    return name.replace(/\.[^/.]+$/, '');
  }

  // ── Detection ──────────────────────────────────────────────────────────────

  async _runDetection() {
    const imageId = this.imageUploader ? this.imageUploader.getImageId() : null;
    const model   = this.modelSelector  ? this.modelSelector.getSelectedModel() : null;
    if (!imageId) {
      this._setStatus('Please upload an image first.', 'error');
      return;
    }
    if (!model) {
      this._setStatus('Please select a model first.', 'error');
      return;
    }

    const gptBtn = this._getGptBtn();
    if (gptBtn) gptBtn.disabled = true;
    this._showLoading(true, 'Running segmentation...');

    try {
      // Step 1: Run segmentation silently in the background
      const segResp = await fetch('/segment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: imageId, model })
      });
      if (!segResp.ok) {
        const err = await segResp.json().catch(() => ({ detail: segResp.statusText }));
        throw new Error(err.detail || 'Segmentation failed');
      }

      // Step 2: Detect boundaries using the mask
      this._showLoading(true, 'Detecting boundaries...');
      const resp = await fetch('/api/gpt-boundaries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: imageId, model })
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || 'Detection failed');
      }
      const data = await resp.json();
      this._overlayB64 = data.gpt_overlay_b64;
      this._polygons   = data.polygons || [];
      this._imageUrl   = data.image_url ? data.image_url : null;
      this._setStatus('Found ' + this._polygons.length + ' building(s) in ' + data.processing_time_s + 's', 'success');
      this._showStaticOverlay();
      window.dispatchEvent(new CustomEvent('gptDetectionComplete', {
        detail: { imageName: this.imageUploader ? this.imageUploader.getOriginalFilename() : this._baseName(), count: this._polygons.length }
      }));
    } catch (e) {
      this._setStatus('Error: ' + e.message, 'error');
    } finally {
      this._showLoading(false);
      if (gptBtn) gptBtn.disabled = false;
    }
  }

  _showLoading(visible, message) {
    const el = document.getElementById('loading-indicator');
    if (!el) return;
    if (visible) {
      const span = el.querySelector('span');
      if (span) span.textContent = message || 'Processing...';
      el.style.display = 'flex';
    } else {
      el.style.display = 'none';
    }
  }

  // ── Static overlay ─────────────────────────────────────────────────────────

  _showStaticOverlay() {
    const gptPanel = this._getGptPanel();
    if (!gptPanel || !this._overlayB64) return;
    this._editMode   = false;
    this._drawMode   = false;
    this._drawPoints = [];

    const gptPanelWrap = this._getGptPanelWrap();
    if (gptPanelWrap) gptPanelWrap.style.display = 'block';
    gptPanel.innerHTML = '';

    const img = document.createElement('img');
    img.src = 'data:image/png;base64,' + this._overlayB64;
    img.alt = 'GPT boundary overlay';
    img.style.cssText = 'width:100%;max-height:85vh;object-fit:contain;display:block;';
    gptPanel.appendChild(img);

    // Save bar
    const saveBar = document.createElement('div');
    saveBar.style.cssText = 'display:flex;gap:8px;margin-top:8px;align-items:center;flex-wrap:wrap;';
    const saveLabel = document.createElement('span');
    saveLabel.textContent = 'Save as:';
    saveLabel.style.cssText = 'font-size:13px;color:var(--text-secondary);font-weight:600;';
    saveBar.appendChild(saveLabel);
    saveBar.appendChild(this._makeBtn('JSON', 'var(--status-success)', () => this._saveJSON()));
    saveBar.appendChild(this._makeBtn('PNG',  'var(--status-info)', () => this._saveImage('png')));
    saveBar.appendChild(this._makeBtn('JPEG', 'var(--primary-cyan)', () => this._saveImage('jpeg')));
    gptPanel.appendChild(saveBar);

    const editBar = this._getEditBar();
    const editBtn = this._getEditBtn();
    const doneBtn = this._getDoneBtn();
    const gptInfoBar = this._getGptInfoBar();
    
    if (editBar)  editBar.style.display  = 'flex';
    if (editBtn)  editBtn.style.display  = '';
    if (doneBtn)  doneBtn.style.display  = 'none';
    if (gptInfoBar) {
      gptInfoBar.textContent = this._polygons.length + ' building(s) detected';
      gptInfoBar.style.display = 'block';
    }
  }

  _makeBtn(label, bg, onClick) {
    const btn = document.createElement('button');
    btn.textContent = label;
    btn.style.cssText = 'padding:4px 12px;background:' + bg + ';color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:13px;';
    btn.addEventListener('click', onClick);
    return btn;
  }

  // ── Save: JSON ─────────────────────────────────────────────────────────────

  _saveJSON() {
    const payload = {
      building_count: this._polygons.length,
      polygons: this._polygons.map((poly, i) => ({
        id: i,
        coordinates: poly,
        type: 'rotated_rect'
      }))
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    this._download(blob, this._baseName() + '.json');
  }

  // ── Save: PNG / JPEG ───────────────────────────────────────────────────────

  _saveImage(format) {
    const src = this._imageUrl || ('data:image/png;base64,' + this._overlayB64);
    const bgImg = new Image();
    bgImg.crossOrigin = 'anonymous';
    bgImg.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width  = bgImg.naturalWidth;
      canvas.height = bgImg.naturalHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(bgImg, 0, 0);
      this._polygons.forEach(poly => {
        if (!poly || poly.length < 3) return;
        ctx.beginPath();
        ctx.moveTo(poly[0][0], poly[0][1]);
        for (let i = 1; i < poly.length; i++) ctx.lineTo(poly[i][0], poly[i][1]);
        ctx.closePath();
        ctx.strokeStyle = 'red';
        ctx.lineWidth   = 1.5;
        ctx.stroke();
        ctx.fillStyle = 'rgba(255,0,0,0.12)';
        ctx.fill();
      });
      const mimeType = format === 'jpeg' ? 'image/jpeg' : 'image/png';
      const quality  = format === 'jpeg' ? 0.92 : undefined;
      canvas.toBlob(blob => {
        this._download(blob, this._baseName() + '.' + format);
      }, mimeType, quality);
    };
    bgImg.onerror = () => {
      const byteStr = atob(this._overlayB64);
      const arr = new Uint8Array(byteStr.length);
      for (let i = 0; i < byteStr.length; i++) arr[i] = byteStr.charCodeAt(i);
      this._download(new Blob([arr], { type: 'image/png' }), this._baseName() + '.png');
    };
    bgImg.src = src;
  }

  _download(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a   = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    window.dispatchEvent(new CustomEvent('fileSaved', { detail: { filename } }));
  }

  // ── Enter edit mode ────────────────────────────────────────────────────────

  _enterEditMode() {
    const gptPanel = this._getGptPanel();
    if (!gptPanel || !this._overlayB64) return;
    this._editMode = true;
    const refImg = new Image();
    refImg.onload = () => this._buildSVGEditor(refImg.naturalWidth, refImg.naturalHeight);
    refImg.src = 'data:image/png;base64,' + this._overlayB64;
  }

  // ── Build SVG editor ───────────────────────────────────────────────────────

  _buildSVGEditor(imgW, imgH) {
    const gptPanel = this._getGptPanel();
    if (!gptPanel) return;
    this._imgW = imgW; this._imgH = imgH;
    gptPanel.innerHTML = '';

    const toolbar = document.createElement('div');
    toolbar.style.cssText = 'display:flex;gap:8px;margin-bottom:6px;align-items:center;flex-wrap:wrap;';

    this._drawBtn = document.createElement('button');
    this._drawBtn.textContent = 'Draw Polygon';
    this._drawBtn.style.cssText = 'padding:4px 10px;background:#2196F3;color:#fff;border:none;border-radius:4px;cursor:pointer;';
    this._drawBtn.addEventListener('click', () => this._toggleDrawMode());

    this._cancelDrawBtn = document.createElement('button');
    this._cancelDrawBtn.textContent = 'Cancel Draw';
    this._cancelDrawBtn.style.cssText = 'padding:4px 10px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;display:none;';
    this._cancelDrawBtn.addEventListener('click', () => this._cancelDraw());

    const hint = document.createElement('span');
    hint.style.cssText = 'font-size:12px;color:#666;';
    hint.textContent = 'Click polygon to select, drag handles to move';
    this._hint = hint;

    toolbar.appendChild(this._drawBtn);
    toolbar.appendChild(this._cancelDrawBtn);
    toolbar.appendChild(hint);

    const container = document.createElement('div');
    container.style.cssText = 'position:relative;display:block;width:100%;';

    const bgImg = document.createElement('img');
    bgImg.src = this._imageUrl || ('data:image/png;base64,' + this._overlayB64);
    bgImg.alt = 'Original image';
    bgImg.style.cssText = 'display:block;width:100%;max-height:85vh;object-fit:contain;';

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;overflow:visible;';
    svg.setAttribute('viewBox', '0 0 ' + imgW + ' ' + imgH);
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    this._svg = svg;

    this._polygons.forEach((poly, polyIdx) => this._renderPoly(svg, poly, polyIdx));
    svg.addEventListener('click',    (e) => this._onSVGClick(e));
    svg.addEventListener('dblclick', (e) => this._onSVGDblClick(e));

    container.appendChild(bgImg);
    container.appendChild(svg);
    
    if (gptPanel) {
      gptPanel.appendChild(toolbar);
      gptPanel.appendChild(container);
    }

    const editBtn = this._getEditBtn();
    const doneBtn = this._getDoneBtn();
    if (editBtn) editBtn.style.display = 'none';
    if (doneBtn) doneBtn.style.display = '';
  }

  // ── Render one polygon ─────────────────────────────────────────────────────

  _renderPoly(svg, poly, polyIdx) {
    if (!poly || poly.length < 3) return;
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.dataset.polyIdx = polyIdx;

    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygon.setAttribute('points', poly.map(p => p[0]+','+p[1]).join(' '));
    polygon.setAttribute('fill', 'rgba(255,0,0,0.15)');
    polygon.setAttribute('stroke', 'red');
    polygon.setAttribute('stroke-width', '1.5');
    polygon.style.cursor = 'pointer';
    polygon.addEventListener('click', (e) => { e.stopPropagation(); this._selectPoly(polyIdx); });
    g.appendChild(polygon);

    const cx = poly.reduce((s,p)=>s+p[0],0)/poly.length;
    const cy = poly.reduce((s,p)=>s+p[1],0)/poly.length;
    const fo = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
    fo.setAttribute('x', cx-14); fo.setAttribute('y', cy-10);
    fo.setAttribute('width', 28); fo.setAttribute('height', 20);
    fo.style.display = 'none'; fo.dataset.deleteBtn = polyIdx;
    const delBtn = document.createElement('button');
    delBtn.textContent = 'x'; delBtn.title = 'Delete polygon';
    delBtn.style.cssText = 'width:28px;height:20px;background:#e74c3c;color:#fff;border:none;border-radius:3px;cursor:pointer;font-size:11px;padding:0;line-height:1;';
    delBtn.addEventListener('click', (e) => { e.stopPropagation(); this._deletePoly(polyIdx); });
    fo.appendChild(delBtn);
    g.appendChild(fo);

    poly.forEach((pt, ptIdx) => {
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', pt[0]); circle.setAttribute('cy', pt[1]);
      circle.setAttribute('r', '5');
      circle.setAttribute('fill', '#2196F3');
      circle.setAttribute('stroke', 'white'); circle.setAttribute('stroke-width', '1.5');
      circle.style.cursor = 'grab';
      circle.dataset.polyIdx = polyIdx; circle.dataset.ptIdx = ptIdx;
      circle.addEventListener('mousedown', (e) => { e.stopPropagation(); this._onHandleMouseDown(e, polyIdx, ptIdx); });
      g.appendChild(circle);
    });

    svg.appendChild(g);
  }

  _selectPoly(polyIdx) {
    if (!this._svg) return;
    this._svg.querySelectorAll('foreignObject[data-delete-btn]').forEach(fo => fo.style.display = 'none');
    if (this._selectedPoly === polyIdx) { this._selectedPoly = null; return; }
    this._selectedPoly = polyIdx;
    const fo = this._svg.querySelector('foreignObject[data-delete-btn="' + polyIdx + '"]');
    if (fo) fo.style.display = '';
  }

  _deletePoly(polyIdx) {
    this._polygons.splice(polyIdx, 1);
    this._selectedPoly = null;
    this._buildSVGEditor(this._imgW, this._imgH);
    this._updateBuildingCount();
  }

  // ── Draw mode ──────────────────────────────────────────────────────────────

  _toggleDrawMode() {
    this._drawMode = !this._drawMode;
    this._drawPoints = [];
    if (this._drawMode) {
      this._drawBtn.textContent = 'Drawing... (dbl-click to finish)';
      this._drawBtn.style.background = '#ff9800';
      this._cancelDrawBtn.style.display = '';
      if (this._hint) this._hint.textContent = 'Click to add vertices, double-click to close';
      if (this._svg) this._svg.style.cursor = 'crosshair';
    } else {
      this._resetDrawUI();
    }
  }

  _resetDrawUI() {
    this._drawMode = false; this._drawPoints = [];
    if (this._drawBtn) { this._drawBtn.textContent = 'Draw Polygon'; this._drawBtn.style.background = '#2196F3'; }
    if (this._cancelDrawBtn) this._cancelDrawBtn.style.display = 'none';
    if (this._hint) this._hint.textContent = 'Click polygon to select, drag handles to move';
    if (this._svg) {
      this._svg.style.cursor = '';
      const prev = this._svg.querySelector('#draw-preview');
      if (prev) prev.remove();
    }
  }

  _cancelDraw() { this._resetDrawUI(); }

  _svgCoords(e) {
    const rect = this._svg.getBoundingClientRect();
    return [
      Math.round((e.clientX - rect.left) * (this._imgW / rect.width)),
      Math.round((e.clientY - rect.top)  * (this._imgH / rect.height))
    ];
  }

  _onSVGClick(e) {
    if (!this._drawMode) return;
    if (e.detail >= 2) return;
    this._drawPoints.push(this._svgCoords(e));
    this._updateDrawPreview();
  }

  _onSVGDblClick(e) {
    if (!this._drawMode) return;
    e.preventDefault();
    if (this._drawPoints.length > 0) this._drawPoints.pop();
    if (this._drawPoints.length >= 3) {
      this._polygons.push([...this._drawPoints]);
      this._resetDrawUI();
      this._buildSVGEditor(this._imgW, this._imgH);
      this._updateBuildingCount();
    } else {
      this._setStatus('Need at least 3 points to close a polygon.', 'error');
      this._resetDrawUI();
    }
  }

  _updateDrawPreview() {
    if (!this._svg) return;
    let prev = this._svg.querySelector('#draw-preview');
    if (!prev) { prev = document.createElementNS('http://www.w3.org/2000/svg', 'g'); prev.id = 'draw-preview'; this._svg.appendChild(prev); }
    prev.innerHTML = '';
    const pts = this._drawPoints;
    if (pts.length >= 2) {
      const pl = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
      pl.setAttribute('points', pts.map(p=>p[0]+','+p[1]).join(' '));
      pl.setAttribute('fill', 'none'); pl.setAttribute('stroke', '#ff9800');
      pl.setAttribute('stroke-width', '1.5'); pl.setAttribute('stroke-dasharray', '4 2');
      prev.appendChild(pl);
    }
    pts.forEach(pt => {
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', pt[0]); c.setAttribute('cy', pt[1]); c.setAttribute('r', '4'); c.setAttribute('fill', '#ff9800');
      prev.appendChild(c);
    });
  }

  // ── Drag handles ───────────────────────────────────────────────────────────

  _onHandleMouseDown(e, polyIdx, ptIdx) {
    e.preventDefault();
    const rect = this._svg.getBoundingClientRect();
    this._dragState = { polyIdx, ptIdx, rect, scaleX: this._imgW / rect.width, scaleY: this._imgH / rect.height };
    const onMove = (ev) => this._onMouseMove(ev);
    const onUp   = () => { this._dragState = null; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  _onMouseMove(e) {
    if (!this._dragState || !this._svg) return;
    const { polyIdx, ptIdx, rect, scaleX, scaleY } = this._dragState;
    const newX = Math.round((e.clientX - rect.left) * scaleX);
    const newY = Math.round((e.clientY - rect.top)  * scaleY);
    this._polygons[polyIdx][ptIdx] = [newX, newY];
    const g = this._svg.querySelector('g[data-poly-idx="' + polyIdx + '"]');
    if (g) {
      const polygon = g.querySelector('polygon');
      if (polygon) polygon.setAttribute('points', this._polygons[polyIdx].map(p=>p[0]+','+p[1]).join(' '));
      g.querySelectorAll('circle[data-pt-idx="' + ptIdx + '"]').forEach(c => { c.setAttribute('cx', newX); c.setAttribute('cy', newY); });
    }
  }

  // ── Exit edit mode — redraw overlay from current polygons ─────────────────

  _exitEditMode() {
    // Redraw the overlay image using the current (edited) polygons
    const src = this._imageUrl || ('data:image/png;base64,' + this._overlayB64);
    const bgImg = new Image();
    bgImg.crossOrigin = 'anonymous';
    bgImg.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width  = bgImg.naturalWidth;
      canvas.height = bgImg.naturalHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(bgImg, 0, 0);
      this._polygons.forEach(poly => {
        if (!poly || poly.length < 3) return;
        ctx.beginPath();
        ctx.moveTo(poly[0][0], poly[0][1]);
        for (let i = 1; i < poly.length; i++) ctx.lineTo(poly[i][0], poly[i][1]);
        ctx.closePath();
        ctx.strokeStyle = 'red';
        ctx.lineWidth   = 1.5;
        ctx.stroke();
        ctx.fillStyle = 'rgba(255,0,0,0.12)';
        ctx.fill();
      });
      // Update the stored overlay so saves also use the edited version
      this._overlayB64 = canvas.toDataURL('image/png').split(',')[1];
      this._updateBuildingCount();
      this._showStaticOverlay();
    };
    bgImg.onerror = () => this._showStaticOverlay();
    bgImg.src = src;
  }

  // ── Status ─────────────────────────────────────────────────────────────────

  _updateBuildingCount() {
    const count = this._polygons.length;
    // Update info bar
    const gptInfoBar = this._getGptInfoBar();
    if (gptInfoBar) gptInfoBar.textContent = count + ' building(s)';
    // Update detection results panel
    const buildingCountEl = document.getElementById('buildingCount');
    if (buildingCountEl) buildingCountEl.textContent = count;
  }

  _setStatus(msg, type) {
    const gptStatus = this._getGptStatus();
    if (!gptStatus) {
      console.log('GPT Status:', msg, type);
      return;
    }
    gptStatus.textContent = msg;
    gptStatus.style.display = msg ? 'block' : 'none';
    gptStatus.style.color = type === 'error' ? 'var(--status-error)' : type === 'success' ? 'var(--status-success)' : 'var(--status-info)';
  }
}
