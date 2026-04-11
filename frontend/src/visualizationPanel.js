/**
 * VisualizationPanel - Renders the three-panel view with original, mask, and overlay
 */
export class VisualizationPanel {
  constructor(imageUploader) {
    this.imageUploader = imageUploader;
    this.originalPanel = document.getElementById('original-panel');
    this.maskPanel = document.getElementById('mask-panel');
    this.overlayPanel = document.getElementById('overlay-panel');
    
    this.setupEventListeners();
  }

  setupEventListeners() {
    // Listen for segmentation completion
    window.addEventListener('segmentationComplete', (event) => {
      this.handleSegmentationComplete(event.detail);
    });
  }

  async handleSegmentationComplete(result) {
    const imageData = this.imageUploader.getUploadedImageData();
    const originalImageUrl = `${imageData.image_url}`;
    
    // Display mask
    this.displayMask(result.maskUrl);
    
    // Generate and display overlay
    await this.displayOverlay(originalImageUrl, result.maskUrl, 0.5);
  }

  /**
   * Display original image in left panel
   * @param {string} imageUrl - URL of the image to display
   */
  displayOriginal(imageUrl) {
    this.originalPanel.innerHTML = '';
    
    const img = document.createElement('img');
    img.src = imageUrl;
    img.alt = 'Original aerial image';
    img.style.maxWidth = '100%';
    img.style.maxHeight = '500px';
    img.style.objectFit = 'contain';
    
    this.originalPanel.appendChild(img);
  }

  /**
   * Display segmentation mask in middle panel
   * @param {string} maskUrl - URL of the mask to display
   */
  displayMask(maskUrl) {
    this.maskPanel.innerHTML = '';
    
    const img = document.createElement('img');
    img.src = maskUrl;
    img.alt = 'Segmentation mask';
    img.style.maxWidth = '100%';
    img.style.maxHeight = '500px';
    img.style.objectFit = 'contain';
    
    this.maskPanel.appendChild(img);
  }

  /**
   * Display overlay in right panel
   * @param {string} imageUrl - URL of original image
   * @param {string} maskUrl - URL of mask image
   * @param {number} opacity - Opacity for the overlay (0-1)
   */
  async displayOverlay(imageUrl, maskUrl, opacity = 0.5) {
    try {
      // Load both images
      const [originalImg, maskImg] = await Promise.all([
        this.loadImage(imageUrl),
        this.loadImage(maskUrl)
      ]);
      
      // Create overlay canvas
      const canvas = this.createOverlay(originalImg, maskImg, opacity);
      
      // Display in panel
      this.overlayPanel.innerHTML = '';
      canvas.style.maxWidth = '100%';
      canvas.style.maxHeight = '500px';
      canvas.style.objectFit = 'contain';
      this.overlayPanel.appendChild(canvas);
      
    } catch (error) {
      console.error('Error creating overlay:', error);
      this.showError('Failed to generate overlay. Showing original and mask separately.');
    }
  }

  /**
   * Create overlay by combining image and mask
   * @param {HTMLImageElement} image - Original image
   * @param {HTMLImageElement} mask - Mask image
   * @param {number} opacity - Opacity for the overlay (0-1)
   * @returns {HTMLCanvasElement} - Canvas with overlay
   */
  createOverlay(image, mask, opacity = 0.5) {
    // Create canvas with same dimensions as original image
    const canvas = document.createElement('canvas');
    canvas.width = image.width;
    canvas.height = image.height;
    
    const ctx = canvas.getContext('2d');
    
    // Draw original image
    ctx.drawImage(image, 0, 0);
    
    // Create temporary canvas for mask processing
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = mask.width;
    maskCanvas.height = mask.height;
    const maskCtx = maskCanvas.getContext('2d');
    maskCtx.drawImage(mask, 0, 0);
    
    // Get mask pixel data
    const maskImageData = maskCtx.getImageData(0, 0, mask.width, mask.height);
    const maskData = maskImageData.data;
    
    // Create overlay image data
    const overlayCanvas = document.createElement('canvas');
    overlayCanvas.width = image.width;
    overlayCanvas.height = image.height;
    const overlayCtx = overlayCanvas.getContext('2d');
    const overlayImageData = overlayCtx.createImageData(image.width, image.height);
    const overlayData = overlayImageData.data;
    
    // Apply red color to building pixels (white in mask)
    for (let i = 0; i < maskData.length; i += 4) {
      const maskValue = maskData[i]; // R channel (grayscale)
      
      if (maskValue > 128) { // Building pixel (white in mask)
        overlayData[i] = 255;     // R
        overlayData[i + 1] = 0;   // G
        overlayData[i + 2] = 0;   // B
        overlayData[i + 3] = Math.floor(opacity * 255); // A (transparency)
      } else { // Background pixel
        overlayData[i] = 0;
        overlayData[i + 1] = 0;
        overlayData[i + 2] = 0;
        overlayData[i + 3] = 0; // Fully transparent
      }
    }
    
    // Draw overlay on top of original image
    overlayCtx.putImageData(overlayImageData, 0, 0);
    ctx.drawImage(overlayCanvas, 0, 0, image.width, image.height);
    
    return canvas;
  }

  /**
   * Load an image from URL
   * @param {string} url - Image URL
   * @returns {Promise<HTMLImageElement>}
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

  showError(message) {
    const errorBanner = document.getElementById('error-banner');
    errorBanner.textContent = message;
    errorBanner.style.display = 'block';
    
    setTimeout(() => {
      errorBanner.style.display = 'none';
    }, 5000);
  }
}
