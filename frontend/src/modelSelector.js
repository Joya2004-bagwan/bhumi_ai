/**
 * ModelSelector - Manages model selection dropdown
 */
export class ModelSelector {
  constructor() {
    this.models = [];
    this.selectedModel = null;
    this.useCards = false; // Flag to determine if using cards or dropdown
  }
  
  // Getter for modelSelect element
  get modelSelect() {
    return document.getElementById('model-select');
  }

  async init() {
    // Check if model-select is a container (for cards) or select element
    if (this.modelSelect && this.modelSelect.tagName !== 'SELECT') {
      this.useCards = true;
    }
    
    await this.loadAvailableModels();
    this.setupEventListeners();
  }

  setupEventListeners() {
    if (!this.useCards && this.modelSelect) {
      this.modelSelect.addEventListener('change', (e) => {
        this.setSelectedModel(e.target.value);
      });
    }
    // Card-based selection is handled in the main app
  }

  /**
   * Get list of available models from backend
   * @returns {Promise<Array>} - Array of model objects
   */
  async getAvailableModels() {
    try {
      const response = await fetch('/models');
      
      if (!response.ok) {
        throw new Error('Failed to fetch models');
      }
      
      const data = await response.json();
      return data.models;
    } catch (error) {
      console.error('Error fetching models:', error);
      this.showError('Failed to load available models. Please refresh the page.');
      return [];
    }
  }

  async loadAvailableModels() {
    this.models = await this.getAvailableModels();
    
    if (this.models.length > 0) {
      if (!this.useCards) {
        this.populateDropdown();
      }
      // Set default to first model
      this.setSelectedModel(this.models[0].name);
    }
  }

  populateDropdown() {
    if (!this.modelSelect || this.useCards) return;
    
    // Clear existing options
    this.modelSelect.innerHTML = '';
    
    // Add model options
    this.models.forEach(model => {
      const option = document.createElement('option');
      option.value = model.name;
      option.textContent = model.display_name;
      option.title = model.description; // Tooltip on hover
      this.modelSelect.appendChild(option);
    });
  }

  /**
   * Get currently selected model
   * @returns {string} - Name of selected model
   */
  getSelectedModel() {
    return this.selectedModel;
  }

  /**
   * Set selected model
   * @param {string} modelName - Name of model to select
   */
  setSelectedModel(modelName) {
    this.selectedModel = modelName;
    if (this.modelSelect && !this.useCards) {
      this.modelSelect.value = modelName;
    }
    
    // Trigger custom event for other components
    window.dispatchEvent(new CustomEvent('modelSelected', { 
      detail: { modelName } 
    }));
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
}
