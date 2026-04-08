/**
 * ImageUploader - Handles file selection, validation, and upload to backend
 */
export class ImageUploader {
  constructor() {
    // Don't store element references in constructor - get them when needed
    // This allows the component to work even if elements don't exist yet
    this.uploadedImageData = null;
    this.imageId = null;
  }
  
  // Getter methods to retrieve elements when needed
  get fileInput() {
    return document.getElementById('image-input');
  }
  
  get uploadButton() {
    return document.getElementById('upload-button');
  }
  
  get uploadStatus() {
    return document.getElementById('upload-status');
  }
  
  get originalPanel() {
    return document.getElementById('original-panel');
  }
  
  setupEventListeners() {
    if (this.uploadButton) {
      this.uploadButton.addEventListener('click', () => this.handleUpload());
    }
    if (this.fileInput) {
      this.fileInput.addEventListener('change', () => this.handleFileSelect());
    }
  }

  handleFileSelect() {
    const file = this.fileInput ? this.fileInput.files[0] : null;
    if (file) {
      const validation = this.validateFile(file);
      if (!validation.valid) {
        this.showError(validation.error);
        if (this.fileInput) this.fileInput.value = '';
      } else {
        if (this.uploadStatus) {
          this.uploadStatus.textContent = `Selected: ${file.name}`;
          this.uploadStatus.style.color = '#27ae60';
        }
      }
    }
  }

  /**
   * Validate file format before upload
   * @param {File} file - The file to validate
   * @returns {Object} - {valid: boolean, error?: string}
   */
  validateFile(file) {
    const validExtensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif'];
    const fileName = file.name.toLowerCase();
    const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext));
    
    if (!hasValidExtension) {
      return {
        valid: false,
        error: 'Unsupported file format. Please upload JPG, PNG, or TIFF images.'
      };
    }
    
    // Check if file is not empty
    if (file.size === 0) {
      return {
        valid: false,
        error: 'File is empty. Please select a valid image file.'
      };
    }
    
    // Check file size (max 50MB)
    const maxSize = 50 * 1024 * 1024; // 50MB in bytes
    if (file.size > maxSize) {
      return {
        valid: false,
        error: 'Image file is too large. Maximum size is 50MB.'
      };
    }
    
    return { valid: true };
  }

  /**
   * Upload image file to backend
   * @param {File} file - The file to upload
   * @returns {Promise<Object>} - Upload response with imageId, imageUrl, width, height
   */
  async uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      
      return data;
    } catch (error) {
      if (error.message.includes('Failed to fetch')) {
        throw new Error('Upload failed. Please check your connection and try again.');
      }
      throw error;
    }
  }

  async handleUpload() {
    const file = this.fileInput ? this.fileInput.files[0] : null;
    
    if (!file) {
      this.showError('Please select an image file first.');
      return;
    }
    
    const validation = this.validateFile(file);
    if (!validation.valid) {
      this.showError(validation.error);
      return;
    }
    
    // Show uploading status
    if (this.uploadButton) this.uploadButton.disabled = true;
    if (this.uploadStatus) {
      this.uploadStatus.textContent = 'Uploading...';
      this.uploadStatus.style.color = '#3498db';
    }
    
    try {
      const response = await this.uploadImage(file);
      this.imageId = response.image_id;
      this.uploadedImageData = response;
      
      // Display the uploaded image
      this.displayImage(`${response.image_url}`);
      
      if (this.uploadStatus) {
        this.uploadStatus.textContent = `Upload successful! (${response.width}x${response.height})`;
        this.uploadStatus.style.color = '#27ae60';
      }
      
      // Trigger custom event for other components
      window.dispatchEvent(new CustomEvent('imageUploaded', { 
        detail: response 
      }));
      
    } catch (error) {
      this.showError(error.message);
      if (this.uploadStatus) this.uploadStatus.textContent = '';
    } finally {
      if (this.uploadButton) this.uploadButton.disabled = false;
    }
  }

  /**
   * Display uploaded image in UI
   * @param {string} imageUrl - URL of the image to display
   */
  displayImage(imageUrl) {
    if (!this.originalPanel) return;
    
    // Clear placeholder
    this.originalPanel.innerHTML = '';
    
    // Create and display image
    const img = document.createElement('img');
    img.src = imageUrl;
    img.alt = 'Uploaded aerial image';
    img.style.maxWidth = '100%';
    img.style.maxHeight = '500px';
    img.style.objectFit = 'contain';
    
    this.originalPanel.appendChild(img);
  }

  showError(message) {
    const errorBanner = document.getElementById('error-banner');
    if (errorBanner) {
      errorBanner.textContent = message;
      errorBanner.style.display = 'block';
      
      // Hide error after 5 seconds
      setTimeout(() => {
        errorBanner.style.display = 'none';
      }, 5000);
    } else {
      console.error('Error:', message);
    }
  }

  getImageId() {
    return this.imageId;
  }

  getUploadedImageData() {
    return this.uploadedImageData;
  }

  getOriginalFilename() {
    const file = this.fileInput ? this.fileInput.files[0] : null;
    if (!file) return 'output';
    return file.name; // keep full filename including extension
  }
}
