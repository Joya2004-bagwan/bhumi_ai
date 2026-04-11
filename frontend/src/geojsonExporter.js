/**
 * GeoJSON Exporter Panel
 * Handles world file upload and GeoJSON export for georeferenced output.
 */

const API_BASE = 'http://localhost:8000';

class GeoJSONExporter {
  constructor() {
    this.imageId = null;
    this.worldFileId = null;
    this.currentGeoJSON = null;
    this.init();
  }

  init() {
    this.createPanel();
    this.bindEvents();
  }

  createPanel() {
    const container = document.createElement('div');
    container.id = 'geojson-exporter-panel';
    container.className = 'geojson-panel';
    container.innerHTML = `
      <h3>GeoJSON Export</h3>
      <p class="panel-hint">Upload a world file (.pgw) to export segmentation results with real-world coordinates.</p>
      
      <div class="geojson-section">
        <label class="section-label">1. World File</label>
        <div class="file-input-wrapper">
          <input type="file" id="worldfile-input" accept=".pgw,.tfw,.jgw,.wld" />
          <span id="worldfile-status" class="file-status">No file selected</span>
        </div>
      </div>
      
      <div class="geojson-section">
        <label class="section-label">2. Segmentation Model</label>
        <select id="geojson-model-select" class="model-select">
          <option value="yolov8m-custom">YOLOv8m Custom</option>
          <option value="maskrcnn-custom">Mask R-CNN Custom</option>
        </select>
      </div>
      
      <div class="geojson-section">
        <label class="section-label">3. Export Settings</label>
        <div class="settings-row">
          <label>Min Area (px):</label>
          <input type="number" id="min-area-input" value="100" min="0" />
        </div>
        <div class="settings-row">
          <label>Simplify Tolerance:</label>
          <input type="number" id="simplify-input" value="1" min="0" step="0.5" />
        </div>
      </div>
      
      <div class="geojson-actions">
        <button id="generate-geojson-btn" class="btn-primary" disabled>
          Generate GeoJSON
        </button>
        <button id="download-geojson-btn" class="btn-secondary" disabled>
          Download GeoJSON
        </button>
      </div>
      
      <div id="geojson-result" class="geojson-result hidden">
        <div class="result-stats">
          <span id="feature-count">0</span> features exported
        </div>
      </div>
    `;
    
    // Find insertion point after boundary detector
    const boundaryPanel = document.getElementById('gpt-boundary-panel');
    if (boundaryPanel && boundaryPanel.nextSibling) {
      boundaryPanel.parentNode.insertBefore(container, boundaryPanel.nextSibling);
    } else {
      const dashboard = document.querySelector('.dashboard') || document.body;
      dashboard.appendChild(container);
    }
    
    this.panel = container;
  }

  bindEvents() {
    // World file input - just store the file, upload happens at generate time
    const worldfileInput = document.getElementById('worldfile-input');
    if (worldfileInput) {
      worldfileInput.addEventListener('change', (e) => this.handleWorldFileSelect(e));
    }
    
    // Generate button
    const generateBtn = document.getElementById('generate-geojson-btn');
    if (generateBtn) generateBtn.addEventListener('click', () => this.generateGeoJSON());
    
    // Download button
    const downloadBtn = document.getElementById('download-geojson-btn');
    if (downloadBtn) downloadBtn.addEventListener('click', () => this.downloadGeoJSON());
    
    // Listen on both window and document for image upload events
    const onImageUploaded = (e) => {
      this.imageId = e.detail?.image_id || e.detail?.imageId;
    };
    window.addEventListener('imageUploaded', onImageUploaded);
    document.addEventListener('imageUploaded', onImageUploaded);
  }

  handleWorldFileSelect(e) {
    const file = e.target.files[0];
    const statusEl = document.getElementById('worldfile-status');
    
    if (!file) {
      statusEl.textContent = 'No file selected';
      this.pendingWorldFile = null;
      return;
    }
    
    // Just store the file - no blocking check here
    this.pendingWorldFile = file;
    statusEl.textContent = `${file.name} ✓ (ready)`;
    statusEl.style.color = 'var(--status-success)';
    
    const generateBtn = document.getElementById('generate-geojson-btn');
    if (generateBtn) generateBtn.disabled = false;
  }

  async generateGeoJSON() {
    // Get imageId from stored value or app instance
    const imageId = this.imageId || window.bhumiApp?.currentImageId || window.bhumiApp?.imageUploader?.imageId;
    
    if (!imageId) {
      alert('Please upload an image first');
      return;
    }
    if (!this.pendingWorldFile && !this.worldFileId) {
      alert('Please select a world file (.pgw) first');
      return;
    }
    
    const model = document.getElementById('geojson-model-select')?.value || 'yolov8m-custom';
    const minArea = parseFloat(document.getElementById('min-area-input')?.value) || 100;
    const simplify = parseFloat(document.getElementById('simplify-input')?.value) || 1;
    
    const generateBtn = document.getElementById('generate-geojson-btn');
    if (generateBtn) { generateBtn.disabled = true; generateBtn.textContent = 'Processing...'; }
    
    try {
      // Upload world file if not done yet
      if (this.pendingWorldFile && !this.worldFileId) {
        const statusEl = document.getElementById('worldfile-status');
        if (statusEl) statusEl.textContent = 'Uploading world file...';
        
        const formData = new FormData();
        formData.append('file', this.pendingWorldFile);
        
        const wfRes = await fetch(`/upload/worldfile?image_id=${imageId}`, {
          method: 'POST',
          body: formData
        });
        
        if (!wfRes.ok) {
          const err = await wfRes.json();
          throw new Error(err.detail || 'World file upload failed');
        }
        
        const wfData = await wfRes.json();
        this.worldFileId = wfData.world_file_id;
        if (statusEl) { statusEl.textContent = `${this.pendingWorldFile.name} ✓`; }
      }
      
      // Run segmentation and get GeoJSON
      const response = await fetch(`/segment/geojson`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_id: imageId,
          world_file_id: this.worldFileId,
          model: model,
          min_area: minArea,
          simplify_tolerance: simplify
        })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Segmentation failed');
      }
      
      const data = await response.json();
      this.currentGeoJSON = data.geojson;
      
      // Update UI
      document.getElementById('feature-count').textContent = data.feature_count;
      document.getElementById('geojson-result').classList.remove('hidden');
      document.getElementById('download-geojson-btn').disabled = false;
      
      // Dispatch event for other components
      document.dispatchEvent(new CustomEvent('geojsonGenerated', {
        detail: { geojson: data.geojson, featureCount: data.feature_count }
      }));
      
    } catch (error) {
      console.error('GeoJSON generation error:', error);
      alert(`Failed to generate GeoJSON: ${error.message}`);
    } finally {
      if (generateBtn) { generateBtn.disabled = false; generateBtn.textContent = 'Generate GeoJSON'; }
    }
  }

  downloadGeoJSON() {
    if (!this.currentGeoJSON) return;
    const blob = new Blob([JSON.stringify(this.currentGeoJSON, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `segmentation_${this.imageId || 'output'}.geojson`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.geoJSONExporter = new GeoJSONExporter();
});

export default GeoJSONExporter;