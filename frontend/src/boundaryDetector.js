/**
 * BoundaryDetector - Detects building boundaries from segmentation mask
 */
export class BoundaryDetector {
  constructor(imageUploader, modelSelector) {
    this.imageUploader = imageUploader;
    this.modelSelector = modelSelector;
    this.boundaries = null;
  }
  
  // Getter methods for DOM elements
  get boundaryButton() {
    return document.getElementById('boundary-button');
  }
  
  get boundaryStatus() {
    return document.getElementById('boundary-status');
  }

  setupEventListeners() {
    if (this.boundaryButton) {
      this.boundaryButton.addEventListener('click', () => this.handleBoundaryDetection());
    }
    
    // Enable button when segmentation is complete
    window.addEventListener('segmentationComplete', () => {
      if (this.boundaryButton) this.boundaryButton.disabled = false;
    });
  }

  /**
   * Handle boundary detection button click
   */
  async handleBoundaryDetection() {
    const imageId = this.imageUploader.getImageId();
    const modelName = this.modelSelector.getSelectedModel();
    
    if (!imageId || !modelName) {
      this.showError('Please run segmentation first.');
      return;
    }
    
    try {
      const result = await this.detectBoundaries(imageId, modelName);
      this.boundaries = result;
      
      // Display results
      this.displayBoundaries(result);
      
      // Trigger custom event
      window.dispatchEvent(new CustomEvent('boundariesDetected', { 
        detail: result 
      }));
      
    } catch (error) {
      this.showError(error.message);
    }
  }

  /**
   * Detect building boundaries from mask
   * @param {string} imageId - ID of uploaded image
   * @param {string} modelName - Name of model used for segmentation
   * @returns {Promise<Object>} - Boundary detection result
   */
  async detectBoundaries(imageId, modelName) {
    // Show loading
    if (this.boundaryButton) {
      this.boundaryButton.disabled = true;
    }
    if (this.boundaryStatus) {
      this.boundaryStatus.textContent = 'Detecting boundaries...';
      this.boundaryStatus.style.display = 'block';
      this.boundaryStatus.style.color = '#666';
    }
    
    try {
      const response = await fetch('/boundaries', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          image_id: imageId,
          model: modelName
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Boundary detection failed');
      }
      
      const data = await response.json();
      
      return {
        buildings: data.buildings,
        totalBuildings: data.total_buildings,
        processingTime: data.processing_time
      };
      
    } catch (error) {
      if (error.message.includes('Failed to fetch')) {
        throw new Error('Boundary detection failed. Please check your connection.');
      }
      throw error;
    } finally {
      if (this.boundaryButton) {
        this.boundaryButton.disabled = false;
      }
    }
  }

  /**
   * Display boundary detection results
   * @param {Object} result - Boundary detection result
   */
  displayBoundaries(result) {
    const { buildings, totalBuildings, processingTime } = result;
    
    // Update status
    if (this.boundaryStatus) {
      this.boundaryStatus.textContent = 
        `Found ${totalBuildings} buildings in ${processingTime.toFixed(2)}s`;
      this.boundaryStatus.style.color = '#28a745';
    }
    
    // Draw boundaries on the overlay panel
    this.drawBoundariesOnCanvas(buildings);
    
    // Log building details
    console.log('Building boundaries detected:', buildings);
    console.log(`Total buildings: ${totalBuildings}`);
    
    // Show building statistics
    this.showBuildingStats(buildings);
  }

  /**
   * Draw boundaries on canvas overlay
   * @param {Array} buildings - List of building polygons
   */
  drawBoundariesOnCanvas(buildings) {
    const originalPanel = document.getElementById('original-panel');
    const img = originalPanel.querySelector('img');
    
    if (!img) {
      console.warn('No original image found');
      return;
    }
    
    // Create canvas
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    canvas.style.width = '100%';
    canvas.style.height = 'auto';
    
    const ctx = canvas.getContext('2d');
    
    // Draw the original image first
    ctx.drawImage(img, 0, 0);
    
    // Draw boundaries
    ctx.strokeStyle = '#00ff00'; // Green color
    ctx.lineWidth = 3;
    
    buildings.forEach(building => {
      const coords = building.coordinates;
      
      if (coords.length < 2) return;
      
      ctx.beginPath();
      ctx.moveTo(coords[0][0], coords[0][1]);
      
      for (let i = 1; i < coords.length; i++) {
        ctx.lineTo(coords[i][0], coords[i][1]);
      }
      
      ctx.closePath();
      ctx.stroke();
    });
    
    // Replace image with canvas
    originalPanel.innerHTML = '';
    originalPanel.appendChild(canvas);
  }

  /**
   * Calculate centroid of polygon
   * @param {Array} coords - Array of [x, y] coordinates
   * @returns {Array} - [x, y] centroid
   */
  calculateCentroid(coords) {
    let sumX = 0, sumY = 0;
    coords.forEach(([x, y]) => {
      sumX += x;
      sumY += y;
    });
    return [sumX / coords.length, sumY / coords.length];
  }

  /**
   * Show building statistics
   * @param {Array} buildings - List of building polygons
   */
  showBuildingStats(buildings) {
    // Calculate statistics
    const areas = buildings.map(b => b.area);
    const avgArea = areas.reduce((a, b) => a + b, 0) / areas.length;
    const maxArea = Math.max(...areas);
    const minArea = Math.min(...areas);
    
    console.log('Building Statistics:');
    console.log(`  Average area: ${avgArea.toFixed(2)} pixels`);
    console.log(`  Largest building: ${maxArea.toFixed(2)} pixels`);
    console.log(`  Smallest building: ${minArea.toFixed(2)} pixels`);
  }

  showError(message) {
    const errorBanner = document.getElementById('error-banner');
    errorBanner.textContent = message;
    errorBanner.style.display = 'block';
    
    setTimeout(() => {
      errorBanner.style.display = 'none';
    }, 5000);
  }

  getBoundaries() {
    return this.boundaries;
  }
}
