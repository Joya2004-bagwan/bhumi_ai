import { ImageUploader } from './imageUploader.js';
import { ModelSelector } from './modelSelector.js';
import { SegmentationRunner } from './segmentationRunner.js';
import { BoundaryDetector } from './boundaryDetector.js';
import { GPTBoundaryDetector } from './gptBoundaryDetector.js';
import { BatchProcessor } from './batchProcessor.js';
import { Dashboard } from './dashboard.js';
import { loadDashboardStats } from './dashboardStats.js';

// Main Application Class
class BhumiAIApp {
  constructor() {
    this.currentPage = 'single';
    this.currentView = 'original'; // For single processing viewer
    
    // Will be initialized when pages are loaded
    this.imageUploader = null;
    this.modelSelector = null;
    this.segmentationRunner = null;
    this.boundaryDetector = null;
    this.gptBoundaryDetector = null;
    this.batchProcessor = null;
    this.dashboard = null;
    
    this.init();
  }

  init() {
    // Set up user info
    this.setupUserInfo();
    
    // Set up navigation
    this.setupNavigation();
    
    // Set up theme switcher
    this.setupThemeSwitcher();
    
    // Set up settings tabs
    this.setupSettingsTabs();
    
    // Initialize dashboard
    this.dashboard = new Dashboard();
    this.dashboard.init();
    
    // Set up navigation
    this.setupNavigation();
    
    // Load dashboard stats
    this.loadDashboardStats();
    
    // Load initial page content
    this.loadRecentJobs();
    
    // Navigate to single processing as default
    this.navigateToPage('single');
    
    console.log('BHUMI AI Application initialized');
  }

  setupUserInfo() {
    const username = 'operator';
    const email = `${username}@bhumi.ai`;
    const initials = username.substring(0, 2).toUpperCase();
    
    // Update sidebar user info
    const userNameEl = document.getElementById('userName');
    const userEmailEl = document.getElementById('userEmail');
    const userAvatarEl = document.getElementById('userAvatar');
    
    if (userNameEl) userNameEl.textContent = username;
    if (userEmailEl) userEmailEl.textContent = email;
    if (userAvatarEl) userAvatarEl.textContent = initials;
    
    // Update profile page
    const profileNameEl = document.getElementById('profileName');
    const profileEmailEl = document.getElementById('profileEmail');
    const profileAvatarEl = document.getElementById('profileAvatar');
    
    if (profileNameEl) profileNameEl.textContent = username.charAt(0).toUpperCase() + username.slice(1);
    if (profileEmailEl) profileEmailEl.textContent = `📧 ${email}`;
    if (profileAvatarEl) profileAvatarEl.textContent = initials;
    
    // Update settings fields
    const settingsUsernameEl = document.getElementById('settingsUsername');
    const settingsEmailEl = document.getElementById('settingsEmail');
    if (settingsUsernameEl) settingsUsernameEl.value = username;
    if (settingsEmailEl) settingsEmailEl.value = email;
  }

  setupNavigation() {
    const navItems = document.querySelectorAll('.sidebar-nav-item');
    console.log('Setting up navigation, found', navItems.length, 'nav items');
    
    navItems.forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        console.log('=== NAV ITEM CLICKED ===', page);
        this.navigateToPage(page);
      });
    });
  }

  navigateToPage(page) {
    console.log('=== NAVIGATION START ===');
    console.log('Navigating to page:', page);
    
    try {
      // Update active nav item
      document.querySelectorAll('.sidebar-nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === page) {
          item.classList.add('active');
        }
      });
      console.log('Nav items updated');
      
      // Update page sections
      document.querySelectorAll('.page-section').forEach(section => {
        section.classList.remove('active');
      });
      console.log('All page sections hidden');
      
      const pageSection = document.getElementById(`page-${page}`);
      console.log('Looking for page section:', `page-${page}`, 'Found:', !!pageSection);
      
      if (pageSection) {
        pageSection.classList.add('active');
        console.log('Page section activated');
      } else {
        console.error('Page section not found:', `page-${page}`);
        return;
      }
      
      // Update breadcrumb
      const pageNames = {
        dashboard: 'Dashboard',
        single: 'Single Processing',
        batch: 'Batch Processing',
        history: 'Processing History',
        settings: 'Settings & Profile'
      };
      const currentPageEl = document.getElementById('currentPage');
      if (currentPageEl) currentPageEl.textContent = pageNames[page] || page;
      console.log('Breadcrumb updated');
      
      this.currentPage = page;
      
      // Load page-specific content
      if (page === 'single') {
        console.log('Loading Single Processing page...');
        this.loadSingleProcessingPage();
        this.setupGeoJSONHandlers();
      } else if (page === 'batch') {
        console.log('Loading Batch Processing page...');
        this.loadBatchProcessingPage();
      } else if (page === 'history') {
        console.log('Loading History page...');
        this.loadHistoryPage();
      } else if (page === 'dashboard') {
        this.loadDashboardStats();
      }
      
      console.log('=== NAVIGATION COMPLETE ===');
    } catch (error) {
      console.error('=== NAVIGATION ERROR ===');
      console.error('Error in navigateToPage:', error);
      console.error('Stack:', error.stack);
    }
  }

  loadSingleProcessingPage() {
    console.log('=== LOAD SINGLE PROCESSING PAGE START ===');
    try {
      const container = document.getElementById('singleProcessingContent');
      console.log('Container found:', !!container);
      
      if (!container) {
        console.error('singleProcessingContent container not found');
        alert('ERROR: singleProcessingContent container not found');
        return;
      }
      
      if (container.children.length > 0) {
        console.log('Single Processing page already loaded');
        return; // Already loaded
      }
      
      console.log('Creating Single Processing page HTML...');
    container.innerHTML = `
      <div class="processing-grid">
        <div class="processing-sidebar">
          <div class="card">
            <h3 class="card-title">SOURCE MATERIAL</h3>
            <div style="margin-top: var(--spacing-md);">
              <div class="upload-zone" id="singleUploadZone">
                <div class="upload-zone-icon">📁</div>
                <div class="upload-zone-title">Drop image here</div>
                <div class="upload-zone-subtitle">JPG, PNG, TIFF (Max 50MB)</div>
                <input type="file" id="image-input" accept=".jpg,.jpeg,.png,.tiff,.tif" style="display: none;">
                <button class="btn btn-secondary" id="browseImageBtn">Browse Files</button>
              </div>
              <div id="upload-status" style="margin-top: var(--spacing-md); font-size: 0.875rem; color: var(--text-secondary);"></div>
            </div>
          </div>
          
          <div class="card">
            <h3 class="card-title">INTELLIGENCE MODEL</h3>
            <div id="model-select" style="margin-top: var(--spacing-md); display: flex; flex-direction: column; gap: var(--spacing-sm);">
              <div class="model-card" data-model="yolov8m-custom">
                <div class="model-card-header">
                  <div class="model-card-radio"></div>
                  <span class="model-card-title">YOLOv8</span>
                  <span class="model-card-version">v8.8</span>
                </div>
                <p class="model-card-description">Fastest speed for dense urban</p>
              </div>
              <div class="model-card" data-model="maskrcnn-custom">
                <div class="model-card-header">
                  <div class="model-card-radio"></div>
                  <span class="model-card-title">Mask R-CNN</span>
                  <span class="model-card-version">v3.4</span>
                </div>
                <p class="model-card-description">Complex irregular boundaries</p>
              </div>
            </div>
          </div>
          
          <button class="btn btn-primary" id="gpt-boundary-button" disabled style="width: 100%;">
            <span>📐</span>
            <span>Detect Buildings</span>
          </button>
          
          <div id="loading-indicator" style="display: none; padding: var(--spacing-md); background: var(--status-info-bg); border: 1px solid var(--status-info); border-radius: var(--radius-md); color: var(--status-info); font-size: 0.875rem; text-align: center;">
            <div class="spinner" style="margin: 0 auto var(--spacing-sm);"></div>
            <span>Detecting boundaries...</span>
          </div>
          
          <div id="boundary-status" style="margin-top: var(--spacing-sm); font-size: 0.875rem;"></div>
          <div id="gpt-status" style="margin-top: var(--spacing-sm); font-size: 0.875rem;"></div>
          
          <!-- GeoJSON Export Panel -->
          <div class="card" style="margin-top: var(--spacing-lg);">
            <h3 class="card-title">GEOJSON EXPORT</h3>
            <p style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: var(--spacing-md);">Upload world file (.pgw) for georeferenced output</p>
            
            <div style="margin-bottom: var(--spacing-md);">
              <label style="font-size: 0.75rem; color: var(--text-secondary); display: block; margin-bottom: var(--spacing-xs);">World File</label>
              <input type="file" id="worldfile-input" accept=".pgw,.tfw,.jgw,.wld" style="width: 100%; font-size: 0.75rem;">
              <div id="worldfile-status" style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: var(--spacing-xs);">No file selected</div>
            </div>
            
            <div style="margin-bottom: var(--spacing-md);">
              <label style="font-size: 0.75rem; color: var(--text-secondary); display: block; margin-bottom: var(--spacing-xs);">Min Area (px)</label>
              <input type="number" id="geojson-min-area" value="100" style="width: 100%; padding: var(--spacing-xs); background: var(--bg-tertiary); border: 1px solid var(--border-primary); border-radius: var(--radius-sm); color: var(--text-primary);">
            </div>
            
            <div style="margin-bottom: var(--spacing-md);">
              <label style="font-size: 0.75rem; color: var(--text-secondary); display: block; margin-bottom: var(--spacing-xs);">Simplify Tolerance</label>
              <input type="number" id="geojson-simplify" value="1" step="0.5" style="width: 100%; padding: var(--spacing-xs); background: var(--bg-tertiary); border: 1px solid var(--border-primary); border-radius: var(--radius-sm); color: var(--text-primary);">
            </div>
            
            <button class="btn btn-secondary" id="generate-geojson-btn" disabled style="width: 100%; margin-bottom: var(--spacing-sm);">
              Generate GeoJSON
            </button>
            <button class="btn btn-success" id="download-geojson-btn" disabled style="width: 100%;">
              Download GeoJSON
            </button>
            
            <div id="geojson-result" style="display: none; margin-top: var(--spacing-md); padding: var(--spacing-sm); background: var(--status-success-bg); border: 1px solid var(--status-success); border-radius: var(--radius-sm); color: var(--status-success); font-size: 0.875rem;">
              <span id="feature-count">0</span> features exported
            </div>
          </div>
        </div>
        
        <div class="processing-main">
          <div style="display: flex; gap: var(--spacing-sm); margin-bottom: var(--spacing-md); border-bottom: 1px solid var(--border-primary);">
            <button class="btn btn-secondary view-tab active" data-view="original">Original</button>
            <button class="btn btn-secondary view-tab" data-view="geojson">GeoJSON Preview</button>
          </div>
          
          <div class="image-viewer" id="imageViewer">
            <div class="image-viewer-placeholder">
              <div class="image-viewer-placeholder-icon">🖼️</div>
              <p>Upload an image to begin processing</p>
            </div>
          </div>
          
          <!-- Hidden panels for compatibility -->
          <div id="original-panel" style="display: none;"></div>
          <div id="mask-panel" style="display: none;"></div>
          <div id="overlay-panel" style="display: none;"></div>
          
          <!-- GeoJSON Preview Panel (hidden - content rendered into imageViewer) -->
          <div id="geojson-preview-panel" style="display: none;">
            <canvas id="geojson-canvas" style="display:none;"></canvas>
            <div id="geojson-preview-stats" style="display:none;"></div>
          </div>
          
          <!-- GPT Panel for boundary detection -->
          <div id="gpt-panel-wrapper" style="display: none;">
            <div id="gpt-panel" style="background: var(--bg-card); border: 1px solid var(--border-primary); border-radius: var(--radius-lg); padding: var(--spacing-lg); margin-top: var(--spacing-lg);"></div>
            <div id="gpt-info-bar" style="display: none; margin-top: var(--spacing-sm); font-size: 0.875rem; color: var(--text-secondary);"></div>
            <div id="gpt-edit-bar" style="display: none; margin-top: var(--spacing-sm); display: flex; gap: var(--spacing-sm);">
              <button id="gpt-edit-button" class="btn btn-secondary">Edit Polygons</button>
              <button id="gpt-draw-button" class="btn btn-secondary" style="display: none;">Draw Polygon</button>
              <button id="gpt-delete-button" class="btn btn-danger" style="display: none;">Delete Polygon</button>
              <button id="gpt-done-button" class="btn btn-success" style="display: none;">Done Editing</button>
            </div>
          </div>
          
          <div id="detection-results" style="margin-top: var(--spacing-lg); display: none;">
            <div class="card">
              <h3 class="card-title">DETECTION RESULTS</h3>
              <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--spacing-md); margin-top: var(--spacing-md);">
                <div>
                  <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: var(--spacing-xs);">BUILDINGS DETECTED</div>
                  <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-cyan);" id="buildingCount">0</div>
                </div>
                <div>
                  <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: var(--spacing-xs);">AVG CONFIDENCE</div>
                  <div style="font-size: 1.5rem; font-weight: 700; color: var(--status-success);" id="avgConfidence">0%</div>
                </div>
                <div>
                  <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: var(--spacing-xs);">PROC. TIME</div>
                  <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);" id="procTime">0s</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div id="error-banner" style="display: none; margin-top: var(--spacing-lg); padding: var(--spacing-md); background: var(--status-error-bg); border: 1px solid var(--status-error); color: var(--status-error); border-radius: var(--radius-md);"></div>
    `;
    
    console.log('Single Processing HTML created, initializing components...');
    
    // Initialize components for single processing
    this.initializeSingleProcessing();
    console.log('=== SINGLE PROCESSING PAGE LOADED SUCCESSFULLY ===');
    } catch (error) {
      console.error('=== ERROR IN LOAD SINGLE PROCESSING PAGE ===');
      console.error('Error:', error);
      console.error('Stack:', error.stack);
      alert('ERROR loading Single Processing page: ' + error.message);
    }
  }

  initializeSingleProcessing() {
    console.log('=== INITIALIZING SINGLE PROCESSING ===');
    
    try {
      // Initialize components
      console.log('Creating ImageUploader...');
      this.imageUploader = new ImageUploader();
      console.log('ImageUploader created successfully');
      
      console.log('Creating ModelSelector...');
      this.modelSelector = new ModelSelector();
      console.log('ModelSelector created successfully');
      
      console.log('Creating SegmentationRunner...');
      this.segmentationRunner = new SegmentationRunner(this.imageUploader, this.modelSelector);
      console.log('SegmentationRunner created successfully');
      
      console.log('Creating BoundaryDetector...');
      this.boundaryDetector = new BoundaryDetector(this.imageUploader, this.modelSelector);
      console.log('BoundaryDetector created successfully');
      
      console.log('Creating GPTBoundaryDetector...');
      this.gptBoundaryDetector = new GPTBoundaryDetector(this.imageUploader, this.modelSelector);
      console.log('GPTBoundaryDetector created successfully');
    } catch (error) {
      console.error('=== ERROR CREATING COMPONENTS ===');
      console.error('Error:', error);
      console.error('Stack:', error.stack);
      throw error;
    }
    
    // Set up upload zone
    console.log('Setting up upload zone...');
    const uploadZone = document.getElementById('singleUploadZone');
    const fileInput = document.getElementById('image-input');
    const browseBtn = document.getElementById('browseImageBtn');
    
    console.log('Upload zone elements:', { uploadZone: !!uploadZone, fileInput: !!fileInput, browseBtn: !!browseBtn });
    
    if (browseBtn && fileInput) {
      browseBtn.addEventListener('click', () => fileInput.click());
      console.log('Browse button listener added');
    }
    
    if (fileInput) {
      // Handle file selection - automatically upload when file is selected
      fileInput.addEventListener('change', async () => {
        console.log('File input changed');
        const file = fileInput.files[0];
        if (!file) return;
        
        // Validate file
        const validation = this.imageUploader.validateFile(file);
        if (!validation.valid) {
          this.showError(validation.error);
          fileInput.value = '';
          return;
        }
        
        // Show uploading status
        const statusEl = document.getElementById('upload-status');
        if (statusEl) {
          statusEl.textContent = `Uploading ${file.name}...`;
          statusEl.style.color = 'var(--status-info)';
        }
        
        try {
          // Upload the file
          const response = await this.imageUploader.uploadImage(file);
          this.imageUploader.imageId = response.image_id;
          this.imageUploader.uploadedImageData = response;
          console.log('Image uploaded, imageId set to:', this.imageUploader.imageId);
          
          // Update status
          if (statusEl) {
            statusEl.textContent = `✓ Uploaded: ${file.name} (${response.width}x${response.height})`;
            statusEl.style.color = 'var(--status-success)';
          }
          
          // Display image in viewer
          const viewer = document.getElementById('imageViewer');
          if (viewer) {
            viewer.innerHTML = `<img src="${response.image_url}" alt="Uploaded image" style="max-width: 100%; max-height: 70vh; object-fit: contain; border-radius: var(--radius-md);">`;
          }
          
          // Also update the hidden original panel for compatibility
          const originalPanel = document.getElementById('original-panel');
          if (originalPanel) {
            originalPanel.innerHTML = `<img src="${response.image_url}" alt="Uploaded image" style="max-width: 100%; max-height: 500px; object-fit: contain;">`;
          }
          
          // Store imageId on app instance for GeoJSON panel
          this.currentImageId = response.image_id;
          
          // Trigger event
          window.dispatchEvent(new CustomEvent('imageUploaded', { 
            detail: response 
          }));
          
        } catch (error) {
          this.showError(error.message);
          if (statusEl) {
            statusEl.textContent = '';
          }
        }
      });
      console.log('File input listener added');
    }
    
    if (uploadZone && fileInput) {
      uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
      });
      
      uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
      });
      
      uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
          fileInput.files = e.dataTransfer.files;
          // Trigger change event
          const event = new Event('change', { bubbles: true });
          fileInput.dispatchEvent(event);
        }
      });
      console.log('Drag and drop listeners added');
    }
    
    // Set up model selection
    console.log('Setting up model selection...');
    document.querySelectorAll('.model-card').forEach(card => {
      card.addEventListener('click', () => {
        document.querySelectorAll('.model-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        const model = card.dataset.model;
        this.modelSelector.setSelectedModel(model);
      });
    });
    console.log('Model selection listeners added');
    
    // Set up view tabs
    console.log('Setting up view tabs...');
    document.querySelectorAll('.view-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.currentView = tab.dataset.view;
        this.updateImageViewer();
      });
    });
    console.log('View tab listeners added');
    
    // Initialize existing components (but don't call setupEventListeners again for imageUploader)
    console.log('Initializing component event listeners...');
    try {
      this.modelSelector.init();
      console.log('ModelSelector initialized');
    } catch (error) {
      console.error('Error initializing ModelSelector:', error);
    }
    
    try {
      this.segmentationRunner.setupEventListeners();
      console.log('SegmentationRunner event listeners set up');
    } catch (error) {
      console.error('Error setting up SegmentationRunner:', error);
    }
    
    try {
      this.boundaryDetector.setupEventListeners();
      console.log('BoundaryDetector event listeners set up');
    } catch (error) {
      console.error('Error setting up BoundaryDetector:', error);
    }
    
    // GPTBoundaryDetector uses event delegation, so it should work automatically
    // But let's make sure it's initialized
    console.log('GPTBoundaryDetector initialized:', this.gptBoundaryDetector);
    
    // Set up GeoJSON export handlers
    console.log('Setting up GeoJSON export handlers...');
    this.setupGeoJSONHandlers();
    
    // Set up workflow handlers
    console.log('Setting up workflow handlers...');
    this.setupWorkflowHandlers();
    
    console.log('=== SINGLE PROCESSING INITIALIZATION COMPLETE ===');
  }
  
  setupGeoJSONHandlers() {
    this.pendingWorldFile = null;
    this.worldFileId = null;
    this.currentGeoJSON = null;

    // Clone elements to remove any stale event listeners
    const replaceWithClone = (id) => {
      const el = document.getElementById(id);
      if (!el) return null;
      const clone = el.cloneNode(true);
      el.parentNode.replaceChild(clone, el);
      return clone;
    };

    const worldfileInput = replaceWithClone('worldfile-input');
    const generateBtn = replaceWithClone('generate-geojson-btn');
    const downloadBtn = replaceWithClone('download-geojson-btn');

    console.log('GeoJSON handlers attached:', { worldfileInput: !!worldfileInput, generateBtn: !!generateBtn, downloadBtn: !!downloadBtn });

    if (worldfileInput) {
      worldfileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        const statusEl = document.getElementById('worldfile-status');
        console.log('World file selected:', file?.name);
        if (!file) {
          if (statusEl) statusEl.textContent = 'No file selected';
          this.pendingWorldFile = null;
          return;
        }
        this.pendingWorldFile = file;
        if (statusEl) { statusEl.textContent = `${file.name} ✓ (ready)`; statusEl.style.color = 'var(--status-success)'; }
        const btn = document.getElementById('generate-geojson-btn');
        console.log('Enabling generate btn:', btn, 'disabled was:', btn?.disabled);
        if (btn) btn.disabled = false;
      });
    }

    if (generateBtn) {
      generateBtn.addEventListener('click', async () => {
        const imageId = this.currentImageId || this.imageUploader?.imageId;
        console.log('Generate GeoJSON - imageId:', imageId, 'pendingWorldFile:', this.pendingWorldFile?.name);

        if (!imageId) { this.showError('Please upload an image first'); return; }
        if (!this.pendingWorldFile && !this.worldFileId) { this.showError('Please select a world file (.pgw) first'); return; }

        const model = this.modelSelector?.getSelectedModel() || 'yolov8m-custom';
        const minArea = parseFloat(document.getElementById('geojson-min-area')?.value) || 100;
        const simplify = parseFloat(document.getElementById('geojson-simplify')?.value) || 1;
        const btn = document.getElementById('generate-geojson-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Processing...'; }

        try {
          // Upload world file first if not done
          if (this.pendingWorldFile && !this.worldFileId) {
            const statusEl = document.getElementById('worldfile-status');
            if (statusEl) statusEl.textContent = 'Uploading world file...';
            const formData = new FormData();
            formData.append('file', this.pendingWorldFile);
            const wfRes = await fetch(`/upload/worldfile?image_id=${imageId}`, { method: 'POST', body: formData });
            if (!wfRes.ok) { const e = await wfRes.json(); throw new Error(e.detail || 'World file upload failed'); }
            const wfData = await wfRes.json();
            this.worldFileId = wfData.world_file_id;
            if (statusEl) statusEl.textContent = `${this.pendingWorldFile.name} ✓`;
          }

          // Run segmentation → GeoJSON
          const res = await fetch('/segment/geojson', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_id: imageId, world_file_id: this.worldFileId, model, min_area: minArea, simplify_tolerance: simplify })
          });
          if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Segmentation failed'); }
          const data = await res.json();
          this.currentGeoJSON = data.geojson;
          this._lastCrsInfo = data.crs_info;
          this._lastImageId = imageId;

          const resultEl = document.getElementById('geojson-result');
          const countEl = document.getElementById('feature-count');
          if (countEl) countEl.textContent = data.feature_count;
          if (resultEl) resultEl.style.display = 'block';
          const dlBtn = document.getElementById('download-geojson-btn');
          if (dlBtn) dlBtn.disabled = false;
          
          // Render preview and switch to GeoJSON tab
          this.renderGeoJSONPreview(data.geojson, imageId);
          // Switch to GeoJSON preview tab
          document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
          const geoTab = document.querySelector('.view-tab[data-view="geojson"]');
          if (geoTab) geoTab.classList.add('active');
          this.currentView = 'geojson';
          this.updateImageViewer();

        } catch (err) {
          this.showError(`GeoJSON failed: ${err.message}`);
        } finally {
          const b = document.getElementById('generate-geojson-btn');
          if (b) { b.disabled = false; b.textContent = 'Generate GeoJSON'; }
        }
      });
    }

    if (downloadBtn) {
      downloadBtn.addEventListener('click', () => {
        if (!this.currentGeoJSON) return;
        const blob = new Blob([JSON.stringify(this.currentGeoJSON, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // Use original filename without extension, e.g. tile_100.png → tile_100.geojson
        const originalName = this.imageUploader?.getOriginalFilename?.() || '';
        const baseName = originalName.replace(/\.[^.]+$/, '') || `segmentation_${this.currentImageId || 'output'}`;
        a.download = `${baseName}.geojson`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
    }
  }
  renderGeoJSONPreview(geojson, imageId) {
    const canvas = document.getElementById('geojson-canvas');
    const panel = document.getElementById('geojson-preview-panel');
    const statsEl = document.getElementById('geojson-preview-stats');
    if (!canvas || !panel) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = `/images/${imageId}.png`;
    img.onerror = () => { img.src = `/images/${imageId}.jpg`; };

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);

      const features = geojson.features || [];
      const wf = this._lastCrsInfo;

      // Determine if coords are world or pixel
      const firstCoord = features[0]?.geometry?.coordinates?.[0]?.[0];
      const isWorldCoords = firstCoord && (Math.abs(firstCoord[0]) > 1000 || Math.abs(firstCoord[1]) > 1000);

      features.forEach((feature) => {
        const coords = feature.geometry?.coordinates?.[0];
        if (!coords) return;
        ctx.beginPath();
        coords.forEach(([x, y], idx) => {
          let px = x, py = y;
          if (isWorldCoords && wf) {
            px = (x - wf.origin_x) / wf.scale_x;
            py = (y - wf.origin_y) / wf.scale_y;
          }
          idx === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
        });
        ctx.closePath();
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = 'rgba(0, 229, 255, 0.15)';
        ctx.fill();
      });

      if (statsEl) {
        statsEl.innerHTML = `<span>${features.length} buildings detected</span>`;
      }
      // Switch to GeoJSON tab and update viewer AFTER canvas is drawn
      document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
      const geoTab = document.querySelector('.view-tab[data-view="geojson"]');
      if (geoTab) geoTab.classList.add('active');
      this.currentView = 'geojson';
      this.updateImageViewer();
      panel.style.display = 'block';    };
  }

  openGeoJSONEditor(geojson, imageId, imgW, imgH) {
    const wf = this._lastCrsInfo;
    const features = geojson.features || [];

    // Determine if coords are world or pixel
    const firstCoord = features[0]?.geometry?.coordinates?.[0]?.[0];
    const isWorldCoords = firstCoord && (Math.abs(firstCoord[0]) > 1000 || Math.abs(firstCoord[1]) > 1000);

    // Convert GeoJSON coords → pixel coords for the editor
    const pixelPolygons = features.map(f => {
      const ring = f.geometry?.coordinates?.[0] || [];
      return ring.slice(0, -1).map(([x, y]) => {
        if (isWorldCoords && wf) {
          return [
            Math.round((x - wf.origin_x) / wf.scale_x),
            Math.round((y - wf.origin_y) / wf.scale_y)
          ];
        }
        return [Math.round(x), Math.round(y)];
      });
    }).filter(p => p.length >= 3);

    // Build editor in the main viewer
    const viewer = document.getElementById('imageViewer');
    if (!viewer) return;

    const { BatchItemEditor } = window._batchEditorModule || {};
    if (!BatchItemEditor) {
      // Dynamically import
      import('./batchPolygonEditor.js').then(({ BatchItemEditor }) => {
        window._batchEditorModule = { BatchItemEditor };
        this._launchEditor(BatchItemEditor, viewer, imageId, imgW, imgH, pixelPolygons, isWorldCoords, wf);
      });
    } else {
      this._launchEditor(BatchItemEditor, viewer, imageId, imgW, imgH, pixelPolygons, isWorldCoords, wf);
    }
  }

  _launchEditor(BatchItemEditor, viewer, imageId, imgW, imgH, pixelPolygons, isWorldCoords, wf) {
    const imageUrl = `/images/${imageId}.png`;
    
    // Clear viewer and mark as editing to prevent updateImageViewer interference
    viewer.innerHTML = '';
    this._geojsonEditing = true;

    const editor = new BatchItemEditor({
      container: viewer,
      imageUrl,
      polygons: pixelPolygons,
      filename: `segmentation_${imageId}`,
      onSave: (editedPixelPolygons) => {
        this._geojsonEditing = false;
        const features = editedPixelPolygons.map((poly, idx) => {
          const coords = poly.map(([px, py]) => {
            if (isWorldCoords && wf) {
              const wx = wf.scale_x * px + wf.origin_x;
              const wy = wf.scale_y * py + wf.origin_y;
              return [wx, wy];
            }
            return [px, py];
          });
          coords.push(coords[0]);
          return {
            type: 'Feature',
            properties: { id: idx + 1 },
            geometry: { type: 'Polygon', coordinates: [coords] }
          };
        });

        this.currentGeoJSON = { type: 'FeatureCollection', features };
        const countEl = document.getElementById('feature-count');
        if (countEl) countEl.textContent = features.length;

        this.renderGeoJSONPreview(this.currentGeoJSON, imageId);
      },
      onClose: () => {
        this._geojsonEditing = false;
        document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
        const geoTab = document.querySelector('.view-tab[data-view="geojson"]');
        if (geoTab) geoTab.classList.add('active');
        this.currentView = 'geojson';
        this.updateImageViewer();
      }
    });

    editor.build();
  }

  showError(message) {
    const errorBanner = document.getElementById('error-banner');
    if (errorBanner) {
      errorBanner.textContent = message;
      errorBanner.style.display = 'block';
      
      setTimeout(() => {
        errorBanner.style.display = 'none';
      }, 5000);
    }
  }

  updateImageViewer() {
    if (this._geojsonEditing) return;
    const viewer = document.getElementById('imageViewer');
    if (!viewer) return;
    
    const originalPanel = document.getElementById('original-panel');
    const maskPanel     = document.getElementById('mask-panel');
    const overlayPanel  = document.getElementById('overlay-panel');
    const gptPanel      = document.getElementById('gpt-panel');
    
    viewer.innerHTML = '';
    
    const showPanel = (panel) => {
      if (!panel || panel.children.length === 0) return false;
      const child = panel.children[0];
      // Canvas can't be cloned — convert to img instead
      if (child.tagName === 'CANVAS') {
        const img = document.createElement('img');
        img.src = child.toDataURL();
        img.style.cssText = 'max-width:100%;max-height:70vh;object-fit:contain;border-radius:var(--radius-md);';
        viewer.appendChild(img);
      } else {
        viewer.appendChild(child.cloneNode(true));
      }
      return true;
    };

    if (this.currentView === 'original' && showPanel(originalPanel)) return;
    if (this.currentView === 'mask'     && showPanel(maskPanel))     return;
    if (this.currentView === 'overlay'  && showPanel(overlayPanel))  return;

    if (this.currentView === 'geojson') {
      const canvas = document.getElementById('geojson-canvas');
      if (canvas && canvas.width > 0) {
        viewer.innerHTML = '';
        const img = document.createElement('img');
        img.src = canvas.toDataURL();
        img.style.cssText = 'max-width:100%;max-height:70vh;object-fit:contain;border-radius:var(--radius-md);display:block;';
        viewer.appendChild(img);

        const statsBar = document.createElement('div');
        statsBar.style.cssText = 'margin-top:8px;padding:8px;background:var(--bg-tertiary);border-radius:var(--radius-sm);font-size:0.8rem;color:var(--text-secondary);display:flex;align-items:center;gap:12px;';
        const featureCount = this.currentGeoJSON?.features?.length || 0;
        statsBar.innerHTML = `<span>${featureCount} buildings detected</span>`;
        const editBtn = document.createElement('button');
        editBtn.textContent = '✏️ Edit Polygons';
        editBtn.style.cssText = 'padding:4px 12px;background:#2196F3;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:0.8rem;';
        editBtn.addEventListener('click', () => {
          this.openGeoJSONEditor(this.currentGeoJSON, this._lastImageId, canvas.width, canvas.height);
        });
        statsBar.appendChild(editBtn);
        viewer.appendChild(statsBar);
        return;
      }
    }

    if (gptPanel && gptPanel.children.length > 0) {
      const gptContent = gptPanel.cloneNode(true);
      gptContent.style.display = 'block';
      viewer.appendChild(gptContent);
      return;
    }

    viewer.innerHTML = `
      <div class="image-viewer-placeholder">
        <div class="image-viewer-placeholder-icon">🖼️</div>
        <p>No ${this.currentView} available yet</p>
      </div>
    `;
  }

  loadBatchProcessingPage() {
    const container = document.getElementById('batchProcessingContent');
    if (!container) return;
    
    if (container.children.length > 0) return; // Already loaded
    
    // Initialize batch processor
    if (!this.batchProcessor) {
      this.batchProcessor = new BatchProcessor(this.modelSelector || new ModelSelector());
    }
    this.batchProcessor.init();
  }

  loadHistoryPage() {
    this.loadProcessingHistory();
  }

  async loadProcessingHistory() {
    const tbody = document.getElementById('historyTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 3rem; color: var(--text-tertiary);">
          <div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <div class="empty-state-title">No processing history yet</div>
            <div class="empty-state-description">Start processing images to see them here</div>
          </div>
        </td>
      </tr>
    `;
  }

  setupThemeSwitcher() {
    const themeOptions = document.querySelectorAll('.theme-option');
    
    themeOptions.forEach(option => {
      option.addEventListener('click', () => {
        const theme = option.dataset.theme;
        this.applyTheme(theme);
        
        themeOptions.forEach(opt => opt.classList.remove('active'));
        option.classList.add('active');
      });
    });
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    this.applyTheme(savedTheme);
  }

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }

  setupSettingsTabs() {
    const tabs = document.querySelectorAll('.settings-tab');
    
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        document.querySelectorAll('.settings-tab-content').forEach(content => {
          content.classList.remove('active');
        });
        const tabContent = document.getElementById(`tab-${tabName}`);
        if (tabContent) tabContent.classList.add('active');
      });
    });
  }

  setupWorkflowHandlers() {
    // Handle image upload success
    window.addEventListener('imageUploaded', (event) => {
      console.log('Image uploaded:', event.detail);
      
      // Show original image in viewer
      const viewer = document.getElementById('imageViewer');
      if (viewer) {
        viewer.innerHTML = `<img src="${event.detail.image_url}" alt="Uploaded image" style="max-width: 100%; max-height: 70vh; object-fit: contain; border-radius: var(--radius-md);">`;
      }
      
      // Enable boundary button if model is selected
      if (this.modelSelector && this.modelSelector.getSelectedModel()) {
        const gptBtn = document.getElementById('gpt-boundary-button');
        if (gptBtn) gptBtn.disabled = false;
      }
    });
    
    // Handle model selection
    window.addEventListener('modelSelected', (event) => {
      console.log('Model selected:', event.detail.modelName);
      
      // Enable boundary button if image is uploaded
      if (this.imageUploader && this.imageUploader.getImageId()) {
        const gptBtn = document.getElementById('gpt-boundary-button');
        if (gptBtn) gptBtn.disabled = false;
      }
    });
    
    // Handle segmentation completion
    window.addEventListener('segmentationComplete', async (event) => {
      console.log('Segmentation complete:', event.detail);
      
      const result = event.detail;
      const imageData = this.imageUploader ? this.imageUploader.getUploadedImageData() : null;
      
      if (!imageData) {
        console.error('No image data available');
        return;
      }
      
      // Update hidden panels for compatibility with existing components
      const maskPanel = document.getElementById('mask-panel');
      const overlayPanel = document.getElementById('overlay-panel');
      
      // Display mask in hidden panel
      if (maskPanel) {
        maskPanel.innerHTML = `<img src="${result.maskUrl}" alt="Segmentation mask" style="max-width: 100%; max-height: 500px; object-fit: contain;">`;
      }
      
      // Generate overlay
      if (overlayPanel && imageData.image_url) {
        try {
          const canvas = await this.createOverlay(imageData.image_url, result.maskUrl);
          overlayPanel.innerHTML = '';
          canvas.style.cssText = 'max-width:100%;max-height:70vh;object-fit:contain;border-radius:var(--radius-md);';
          overlayPanel.appendChild(canvas);
        } catch (error) {
          console.error('Error creating overlay:', error);
        }
      }
      
      // Auto-switch to overlay tab and update viewer
      this.currentView = 'overlay';
      document.querySelectorAll('.view-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.view === 'overlay');
      });
      this.updateImageViewer();
      
      // Enable boundary detection
      const boundaryBtn = document.getElementById('gpt-boundary-button');
      if (boundaryBtn) boundaryBtn.disabled = false;
      
      // Update dashboard stats
      this.updateDashboardStats();
    });
    
    // Handle boundary detection
    window.addEventListener('boundariesDetected', (event) => {
      console.log('Boundaries detected:', event.detail);
      
      // Show detection results
      const resultsDiv = document.getElementById('detection-results');
      if (resultsDiv) {
        resultsDiv.style.display = 'block';
        const buildingCountEl = document.getElementById('buildingCount');
        if (buildingCountEl) buildingCountEl.textContent = event.detail.totalBuildings || 0;
        const avgConfEl = document.getElementById('avgConfidence');
        if (avgConfEl) avgConfEl.textContent = '94%';
        const procTimeEl = document.getElementById('procTime');
        if (procTimeEl) procTimeEl.textContent = '1.4s';
      }
      
      // Update dashboard
      this.updateDashboardStats();
    });
    
    // Handle GPT boundary detection completion
    window.addEventListener('gptDetectionComplete', (event) => {
      console.log('GPT Detection complete:', event.detail);
      
      // Show the GPT panel wrapper
      const gptPanelWrapper = document.getElementById('gpt-panel-wrapper');
      if (gptPanelWrapper) {
        gptPanelWrapper.style.display = 'block';
      }
      
      // Show detection results
      const resultsDiv = document.getElementById('detection-results');
      if (resultsDiv) {
        resultsDiv.style.display = 'block';
        const buildingCountEl = document.getElementById('buildingCount');
        if (buildingCountEl) buildingCountEl.textContent = event.detail.count || 0;
        const avgConfEl = document.getElementById('avgConfidence');
        if (avgConfEl) avgConfEl.textContent = '94%';
        const procTimeEl = document.getElementById('procTime');
        if (procTimeEl) procTimeEl.textContent = '1.4s';
      }
      
      // Track in dashboard — use itemId presence to distinguish batch vs single
      if (this.dashboard) {
        const source = event.detail.itemId ? 'batch' : 'single';
        this.dashboard.recordDetection(event.detail.imageName, event.detail.count, event.detail.itemId, source);
        this.updateDashboardStats();
      }
    });
    
    window.addEventListener('fileSaved', (event) => {
      if (this.dashboard) {
        this.dashboard.recordSave(event.detail.filename, event.detail.format, event.detail.itemId);
        this.loadDashboardStats();
      }
    });

    window.addEventListener('dashboardStatsChanged', () => {
      this.loadDashboardStats();
    });
  }
  
  /**
   * Create overlay by combining image and mask
   */
  async createOverlay(imageUrl, maskUrl) {
    // Load both images
    const [originalImg, maskImg] = await Promise.all([
      this.loadImage(imageUrl),
      this.loadImage(maskUrl)
    ]);
    
    // Create canvas with same dimensions as original image
    const canvas = document.createElement('canvas');
    canvas.width = originalImg.width;
    canvas.height = originalImg.height;
    
    const ctx = canvas.getContext('2d');
    
    // Draw original image
    ctx.drawImage(originalImg, 0, 0);
    
    // Create temporary canvas for mask processing
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = maskImg.width;
    maskCanvas.height = maskImg.height;
    const maskCtx = maskCanvas.getContext('2d');
    maskCtx.drawImage(maskImg, 0, 0);
    
    // Get mask pixel data
    const maskImageData = maskCtx.getImageData(0, 0, maskImg.width, maskImg.height);
    const maskData = maskImageData.data;
    
    // Create overlay image data
    const overlayCanvas = document.createElement('canvas');
    overlayCanvas.width = originalImg.width;
    overlayCanvas.height = originalImg.height;
    const overlayCtx = overlayCanvas.getContext('2d');
    const overlayImageData = overlayCtx.createImageData(originalImg.width, originalImg.height);
    const overlayData = overlayImageData.data;
    
    // Apply red color to building pixels (white in mask)
    const scaleX = maskImg.width / originalImg.width;
    const scaleY = maskImg.height / originalImg.height;
    
    for (let y = 0; y < originalImg.height; y++) {
      for (let x = 0; x < originalImg.width; x++) {
        const maskX = Math.floor(x * scaleX);
        const maskY = Math.floor(y * scaleY);
        const maskIdx = (maskY * maskImg.width + maskX) * 4;
        const overlayIdx = (y * originalImg.width + x) * 4;
        
        const maskValue = maskData[maskIdx]; // R channel (grayscale)
        
        if (maskValue > 128) { // Building pixel (white in mask)
          overlayData[overlayIdx] = 255;     // R
          overlayData[overlayIdx + 1] = 0;   // G
          overlayData[overlayIdx + 2] = 0;   // B
          overlayData[overlayIdx + 3] = 128; // A (50% transparency)
        } else { // Background pixel
          overlayData[overlayIdx] = 0;
          overlayData[overlayIdx + 1] = 0;
          overlayData[overlayIdx + 2] = 0;
          overlayData[overlayIdx + 3] = 0; // Fully transparent
        }
      }
    }
    
    // Draw overlay on top of original image
    overlayCtx.putImageData(overlayImageData, 0, 0);
    ctx.drawImage(overlayCanvas, 0, 0);
    
    return canvas;
  }
  
  /**
   * Load an image from URL
   */
  loadImage(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous'; // Enable CORS
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(`Failed to load image: ${url}`));
      img.src = url;
    });
  }


  async loadDashboardStats() {
    await loadDashboardStats();
    // wire up refresh button once
    const btn = document.getElementById('dashRefreshBtn');
    if (btn && !btn._wired) {
      btn._wired = true;
      btn.addEventListener('click', () => loadDashboardStats());
    }
  }

  updateDashboardStats() {
    this.loadDashboardStats();
  }
  
  loadRecentJobs() {
    const jobsList = document.getElementById('recentJobsList');
    if (!jobsList) return;
    
    jobsList.innerHTML = `
      <div style="padding: 1rem; text-align: center; color: var(--text-tertiary); font-size: 0.875rem;">
        No recent jobs yet. Start processing to see activity here.
      </div>
    `;
  }
}

// Initialize app when DOM is ready
console.log('=== INDEX.JS LOADED ===');
console.log('Document ready state:', document.readyState);

window.addEventListener('error', (event) => {
  console.error('=== GLOBAL ERROR ===');
  console.error('Message:', event.message);
  console.error('Filename:', event.filename);
  console.error('Line:', event.lineno, 'Column:', event.colno);
  console.error('Error object:', event.error);
});

if (document.readyState === 'loading') {
  console.log('Waiting for DOMContentLoaded...');
  document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded fired, creating BhumiAIApp...');
    try {
      const app = new BhumiAIApp();
      window.bhumiApp = app;
      console.log('BhumiAIApp created successfully:', app);
    } catch (error) {
      console.error('ERROR creating BhumiAIApp:', error);
      alert('Failed to initialize app: ' + error.message);
    }
  });
} else {
  console.log('DOM already loaded, creating BhumiAIApp immediately...');
  try {
    const app = new BhumiAIApp();
    window.bhumiApp = app;
    console.log('BhumiAIApp created successfully:', app);
  } catch (error) {
    console.error('ERROR creating BhumiAIApp:', error);
    alert('Failed to initialize app: ' + error.message);
  }
}
