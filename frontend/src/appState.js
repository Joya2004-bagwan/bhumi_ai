/**
 * AppState - Manages application state and UI feedback
 */
export class AppState {
  constructor() {
    this.state = {
      uploadedImage: null,
      selectedModel: null,
      segmentationResult: null,
      isUploading: false,
      isSegmenting: false,
      error: null
    };
    
    this.errorBanner = document.getElementById('error-banner');
    this.loadingIndicator = document.getElementById('loading-indicator');
    
    this.setupEventListeners();
  }

  setupEventListeners() {
    // Listen for image upload
    window.addEventListener('imageUploaded', (event) => {
      this.updateState({ uploadedImage: event.detail });
    });
    
    // Listen for model selection
    window.addEventListener('modelSelected', (event) => {
      this.updateState({ selectedModel: event.detail.modelName });
    });
    
    // Listen for segmentation completion
    window.addEventListener('segmentationComplete', (event) => {
      this.updateState({ segmentationResult: event.detail });
    });
  }

  /**
   * Update application state
   * @param {Object} updates - State updates to apply
   */
  updateState(updates) {
    this.state = { ...this.state, ...updates };
    this.notifyStateChange();
  }

  /**
   * Get current state
   * @returns {Object} - Current application state
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Notify listeners of state change
   */
  notifyStateChange() {
    window.dispatchEvent(new CustomEvent('stateChanged', { 
      detail: this.getState() 
    }));
  }

  /**
   * Show error message
   * @param {string} message - Error message to display
   */
  showError(message) {
    this.updateState({ error: message });
    this.errorBanner.textContent = message;
    this.errorBanner.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
      this.hideError();
    }, 5000);
  }

  /**
   * Hide error message
   */
  hideError() {
    this.updateState({ error: null });
    this.errorBanner.style.display = 'none';
  }

  /**
   * Show loading indicator
   * @param {string} message - Loading message
   */
  showLoading(message = 'Processing...') {
    this.loadingIndicator.textContent = message;
    this.loadingIndicator.style.display = 'block';
  }

  /**
   * Hide loading indicator
   */
  hideLoading() {
    this.loadingIndicator.style.display = 'none';
  }

  /**
   * Add visual feedback for button interactions
   */
  addButtonFeedback() {
    const buttons = document.querySelectorAll('button');
    
    buttons.forEach(button => {
      // Add active state on click
      button.addEventListener('mousedown', () => {
        button.style.transform = 'scale(0.98)';
      });
      
      button.addEventListener('mouseup', () => {
        button.style.transform = 'scale(1)';
      });
      
      // Add hover effect
      button.addEventListener('mouseenter', () => {
        if (!button.disabled) {
          button.style.transition = 'all 0.3s ease';
        }
      });
    });
  }

  /**
   * Add visual feedback for file input
   */
  addFileInputFeedback() {
    const fileInput = document.getElementById('image-input');
    
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        fileInput.style.color = '#27ae60';
      }
    });
  }

  /**
   * Add visual feedback for model selection
   */
  addModelSelectFeedback() {
    const modelSelect = document.getElementById('model-select');
    
    modelSelect.addEventListener('change', () => {
      modelSelect.style.borderColor = '#3498db';
      
      setTimeout(() => {
        modelSelect.style.borderColor = '#ddd';
      }, 500);
    });
  }

  /**
   * Initialize all UI feedback
   */
  initializeUIFeedback() {
    this.addButtonFeedback();
    this.addFileInputFeedback();
    this.addModelSelectFeedback();
  }
}
