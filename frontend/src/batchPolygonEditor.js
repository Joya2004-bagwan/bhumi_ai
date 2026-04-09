/**
 * BatchItemEditor — inline SVG polygon editor for a single batch image.
 * Follows the exact same pattern as GPTBoundaryDetector's SVG editor.
 *
 * Config: { container, imageUrl, polygons, filename, onSave, onClose }
 */
export class BatchItemEditor {
  constructor({ container, imageUrl, polygons, filename, onSave, onClose }) {
    this._container  = container;
    this._imageUrl   = imageUrl;
    this._polygons   = polygons.map(p => p.map(pt => [...pt]));
    this._filename   = filename || 'output';
    this._onSave     = onSave;
    this._onClose    = onClose;

    this._svg          = null;
    this._imgW         = 0;
    this._imgH         = 0;
    this._selectedPoly = null;
    this._drawMode     = false;
    this._drawPoints   = [];
    this._dragState    = null;
    this._drawBtn      = null;
    this._cancelDrawBtn = null;
    this._hint         = null;
    this._infoBar      = null;
  }

  build() {
    this._container.innerHTML = '';
    
    // Create a wrapper container for the full-screen editor
    const editorContainer = document.createElement('div');
    editorContainer.className = 'bpe-container';

    // ── Header bar ──────────────────────────────────────────────────────────
    const header = document.createElement('div');
    header.className = 'bpe-header';
    header.innerHTML = `<span class="bpe-title">Editing: <strong>${this._filename}</strong></span>`;
    const closeBtn = this._makeBtn('✕ Close', '#7f8c8d', () => this._onClose());
    header.appendChild(closeBtn);
    editorContainer.appendChild(header);

    // ── Toolbar ─────────────────────────────────────────────────────────────
    const toolbar = document.createElement('div');
    toolbar.className = 'bpe-toolbar';
    this._drawBtn = this._makeBtn('Draw Polygon', '#2196F3', () => this._toggleDrawMode());
    this._cancelDrawBtn = this._makeBtn('Cancel Draw', '#e74c3c', () => this._cancelDraw());
    this._cancelDrawBtn.style.display = 'none';
    this._hint = document.createElement('span');
    this._hint.className = 'bpe-hint';
    this._hint.textContent = 'Click a polygon to select · drag handles to move vertices';

    // Zoom controls
    const zoomLabel = document.createElement('span');
    zoomLabel.className = 'bpe-hint';
    zoomLabel.textContent = 'Zoom:';
    const zoomBtns = [1, 1.5, 2, 3].map(z => {
      const b = this._makeBtn(`${z}×`, z === (this._scale || 1.5) ? '#00bcd4' : '#555', () => {
        this._scale = z;
        // rebuild editor in place, preserving polygons
        const ec = this._container.querySelector('.bpe-container');
        if (ec) {
          // remove wrap, infoBar, saveBar — keep header+toolbar
          while (ec.children.length > 2) ec.removeChild(ec.lastChild);
        }
        const imgEl = new Image();
        imgEl.onload = () => this._buildEditor(imgEl);
        imgEl.src = this._imageUrl;
      });
      b.style.padding = '3px 8px';
      b.style.fontSize = '0.75rem';
      return b;
    });

    toolbar.appendChild(this._drawBtn);
    toolbar.appendChild(this._cancelDrawBtn);
    toolbar.appendChild(this._hint);
    toolbar.appendChild(zoomLabel);
    zoomBtns.forEach(b => toolbar.appendChild(b));
    editorContainer.appendChild(toolbar);

    // ── Load image then build SVG editor ────────────────────────────────────
    const loadingMsg = document.createElement('div');
    loadingMsg.style.cssText = 'padding:20px;text-align:center;color:#aaa;background:#111;';
    loadingMsg.textContent = 'Loading image…';
    editorContainer.appendChild(loadingMsg);
    
    // Append the editor container to the main container
    this._container.appendChild(editorContainer);

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      this._imgW = img.naturalWidth;
      this._imgH = img.naturalHeight;
      loadingMsg.remove();
      this._buildEditor(img);
    };
    img.onerror = () => {
      loadingMsg.textContent = 'Failed to load image.';
      loadingMsg.style.color = '#e74c3c';
    };
    img.src = this._imageUrl;
  }

  _buildEditor(img) {
    const editorContainer = this._container.querySelector('.bpe-container');
    if (!editorContainer) return;

    // default scale — can be changed via zoom buttons
    this._scale = this._scale || 1.5;

    // wrap is scrollable so enlarged image can be panned
    const wrap = document.createElement('div');
    wrap.className = 'bpe-canvas-wrap';
    wrap.style.cssText = 'width:100%;background:#111;display:flex;align-items:flex-start;justify-content:center;overflow:auto;max-height:80vh;';
    this._wrap = wrap;

    const container = document.createElement('div');
    container.style.cssText = 'position:relative;line-height:0;flex-shrink:0;';

    const bgImg = document.createElement('img');
    bgImg.src = img.src;
    bgImg.alt = this._filename;
    bgImg.className = 'bpe-bg-img';
    // explicit pixel size — scale controls zoom, no CSS max-height constraint
    bgImg.style.cssText = `display:block;width:${Math.round(this._imgW * this._scale)}px;height:${Math.round(this._imgH * this._scale)}px;`;
    this._bgImg = bgImg;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;';
    svg.setAttribute('viewBox', `0 0 ${this._imgW} ${this._imgH}`);
    svg.setAttribute('preserveAspectRatio', 'none');
    // Set explicit pixel dimensions so getScreenCTM() resolves correctly
    // before the browser has finished percentage-based layout
    svg.setAttribute('width',  String(Math.round(this._imgW * this._scale)));
    svg.setAttribute('height', String(Math.round(this._imgH * this._scale)));
    this._svg = svg;

    svg.addEventListener('click',    e => this._onSVGClick(e));
    svg.addEventListener('dblclick', e => this._onSVGDblClick(e));

    container.appendChild(bgImg);
    container.appendChild(svg);
    wrap.appendChild(container);
    editorContainer.appendChild(wrap);

    this._renderAllPolygons();

    this._infoBar = document.createElement('div');
    this._infoBar.className = 'bpe-info-bar';
    this._updateInfoBar();
    editorContainer.appendChild(this._infoBar);

    const saveBar = document.createElement('div');
    saveBar.className = 'bpe-save-bar';
    const saveLabel = document.createElement('span');
    saveLabel.textContent = 'Save edits:';
    saveLabel.className = 'bpe-save-label';
    saveBar.appendChild(saveLabel);
    saveBar.appendChild(this._makeBtn('Save & Close', '#27ae60', () => this._save()));
    saveBar.appendChild(this._makeBtn('Discard', '#e74c3c', () => this._onClose()));
    editorContainer.appendChild(saveBar);
  }

  // ── Render polygons ───────────────────────────────────────────────────────

  _renderAllPolygons() {
    if (!this._svg) return;
    this._svg.innerHTML = '';
    this._polygons.forEach((poly, idx) => this._renderPoly(poly, idx));
  }

  _renderPoly(poly, polyIdx) {
    if (!poly || poly.length < 3) return;
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.dataset.polyIdx = polyIdx;

    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygon.setAttribute('points', poly.map(p => p[0]+','+p[1]).join(' '));
    polygon.setAttribute('fill',         'rgba(255,0,0,0.15)');
    polygon.setAttribute('stroke',       polyIdx === this._selectedPoly ? '#ff0' : 'red');
    polygon.setAttribute('stroke-width', polyIdx === this._selectedPoly ? '2.5' : '1.5');
    polygon.style.cursor = 'pointer';
    polygon.addEventListener('click', e => { e.stopPropagation(); this._selectPoly(polyIdx); });
    g.appendChild(polygon);

    // Delete button (shown when selected)
    const cx = poly.reduce((s,p)=>s+p[0],0)/poly.length;
    const cy = poly.reduce((s,p)=>s+p[1],0)/poly.length;
    const fo = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
    fo.setAttribute('x', cx-14); fo.setAttribute('y', cy-10);
    fo.setAttribute('width', 28); fo.setAttribute('height', 20);
    fo.style.display = polyIdx === this._selectedPoly ? '' : 'none';
    fo.dataset.deleteBtn = polyIdx;
    const delBtn = document.createElement('button');
    delBtn.textContent = '✕';
    delBtn.title       = 'Delete polygon';
    delBtn.style.cssText = 'width:28px;height:20px;background:#e74c3c;color:#fff;border:none;border-radius:3px;cursor:pointer;font-size:11px;padding:0;line-height:1;';
    delBtn.addEventListener('click', e => { e.stopPropagation(); this._deletePoly(polyIdx); });
    fo.appendChild(delBtn);
    g.appendChild(fo);

    // Vertex handles
    poly.forEach((pt, ptIdx) => {
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', pt[0]); c.setAttribute('cy', pt[1]); c.setAttribute('r', '5');
      c.setAttribute('fill', '#2196F3');
      c.setAttribute('stroke', 'white'); c.setAttribute('stroke-width', '1.5');
      c.style.cursor = 'grab';
      c.dataset.polyIdx = polyIdx; c.dataset.ptIdx = ptIdx;
      c.addEventListener('mousedown', e => { e.stopPropagation(); this._onHandleMouseDown(e, polyIdx, ptIdx); });
      g.appendChild(c);
    });

    this._svg.appendChild(g);
  }

  _selectPoly(polyIdx) {
    this._selectedPoly = this._selectedPoly === polyIdx ? null : polyIdx;
    this._renderAllPolygons();
  }

  _deletePoly(polyIdx) {
    this._polygons.splice(polyIdx, 1);
    this._selectedPoly = null;
    this._renderAllPolygons();
    this._updateInfoBar();
  }

  // ── Draw mode ─────────────────────────────────────────────────────────────

  _toggleDrawMode() {
    this._drawMode   = !this._drawMode;
    this._drawPoints = [];
    if (this._drawMode) {
      this._drawBtn.textContent       = 'Drawing… (dbl-click to finish)';
      this._drawBtn.style.background  = '#ff9800';
      this._cancelDrawBtn.style.display = '';
      if (this._hint) this._hint.textContent = 'Click to add vertices · double-click to close polygon';
      if (this._svg)  this._svg.style.cursor = 'crosshair';
    } else {
      this._resetDrawUI();
    }
  }

  _resetDrawUI() {
    this._drawMode   = false;
    this._drawPoints = [];
    if (this._drawBtn)       { this._drawBtn.textContent = 'Draw Polygon'; this._drawBtn.style.background = '#2196F3'; }
    if (this._cancelDrawBtn)   this._cancelDrawBtn.style.display = 'none';
    if (this._hint)            this._hint.textContent = 'Click a polygon to select · drag handles to move vertices';
    if (this._svg) {
      this._svg.style.cursor = '';
      const prev = this._svg.querySelector('#draw-preview');
      if (prev) prev.remove();
    }
  }

  _cancelDraw() { this._resetDrawUI(); }

  _svgCoords(e) {
    // getScreenCTM() is the only reliable method — it accounts for all
    // ancestor transforms, scroll offsets, and CSS scaling in one shot.
    // Works correctly because preserveAspectRatio:none means the CTM is
    // a pure scale+translate with no letterbox padding.
    const pt = this._svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const svgP = pt.matrixTransform(this._svg.getScreenCTM().inverse());
    return [
      Math.max(0, Math.min(this._imgW, Math.round(svgP.x))),
      Math.max(0, Math.min(this._imgH, Math.round(svgP.y))),
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
    if (this._drawPoints.length > 0) this._drawPoints.pop(); // remove duplicate from dblclick
    if (this._drawPoints.length >= 3) {
      this._polygons.push([...this._drawPoints]);
      this._resetDrawUI();
      this._renderAllPolygons();
      this._updateInfoBar();
    } else {
      this._resetDrawUI();
    }
  }

  _updateDrawPreview() {
    if (!this._svg) return;
    let prev = this._svg.querySelector('#draw-preview');
    if (!prev) {
      prev = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      prev.id = 'draw-preview';
      this._svg.appendChild(prev);
    }
    prev.innerHTML = '';
    const pts = this._drawPoints;
    if (pts.length >= 2) {
      const pl = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
      pl.setAttribute('points', pts.map(p=>p[0]+','+p[1]).join(' '));
      pl.setAttribute('fill', 'none');
      pl.setAttribute('stroke', '#ff9800');
      pl.setAttribute('stroke-width', '1.5');
      pl.setAttribute('stroke-dasharray', '4 2');
      prev.appendChild(pl);
    }
    pts.forEach(pt => {
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', pt[0]); c.setAttribute('cy', pt[1]);
      c.setAttribute('r', '4'); c.setAttribute('fill', '#ff9800');
      prev.appendChild(c);
    });
  }

  // ── Drag vertex handles ───────────────────────────────────────────────────

  _onHandleMouseDown(e, polyIdx, ptIdx) {
    e.preventDefault();
    this._dragState = { polyIdx, ptIdx };
    const onMove = ev => this._onMouseMove(ev);
    const onUp   = () => { this._dragState = null; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup',   onUp);
  }

  _onMouseMove(e) {
    if (!this._dragState || !this._svg) return;
    const { polyIdx, ptIdx } = this._dragState;
    const [newX, newY] = this._svgCoords(e);
    this._polygons[polyIdx][ptIdx] = [newX, newY];
    const g = this._svg.querySelector(`g[data-poly-idx="${polyIdx}"]`);
    if (g) {
      const polygon = g.querySelector('polygon');
      if (polygon) polygon.setAttribute('points', this._polygons[polyIdx].map(p=>p[0]+','+p[1]).join(' '));
      g.querySelectorAll(`circle[data-pt-idx="${ptIdx}"]`).forEach(c => { c.setAttribute('cx', newX); c.setAttribute('cy', newY); });
    }
  }

  // ── Save / helpers ────────────────────────────────────────────────────────

  _save() {
    this._onSave(this._polygons);
    this._onClose();
  }

  _updateInfoBar() {
    if (this._infoBar) this._infoBar.textContent = `${this._polygons.length} building polygon(s)`;
  }

  _makeBtn(label, bg, onClick) {
    const btn = document.createElement('button');
    btn.textContent = label;
    btn.style.cssText = `padding:5px 13px;background:${bg};color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:13px;`;
    btn.addEventListener('click', onClick);
    return btn;
  }
}
