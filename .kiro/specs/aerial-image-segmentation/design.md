# Design Document: Aerial Image Segmentation Web Application

## Overview

The aerial image segmentation web application is a client-server system that enables users to upload aerial imagery and apply machine learning segmentation models to identify buildings. The system consists of a web-based frontend for user interaction and visualization, and a backend API that handles image processing and model inference.

The architecture follows a clear separation between presentation (frontend), business logic (backend API), and model inference (segmentation models). Users interact with a simple workflow: upload image → select model → run segmentation → view results in three panels (original, mask, overlay).

The system supports three state-of-the-art segmentation models:
- **SAM2 (Segment Anything Model 2)**: A foundation model for general-purpose segmentation with strong zero-shot capabilities
- **YOLOv8 Segmentation**: A real-time instance segmentation model optimized for speed and accuracy
- **U-Net**: A classic encoder-decoder architecture widely used for semantic segmentation tasks

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Image Upload │  │ Model Select │  │ Run Button   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Original     │  │ Mask         │  │ Overlay      │      │
│  │ Panel        │  │ Panel        │  │ Panel        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend API                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Endpoint Handler                     │   │
│  │  - /upload (POST)                                     │   │
│  │  - /segment (POST)                                    │   │
│  │  - /models (GET)                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Image Processing Service                    │   │
│  │  - Validation                                         │   │
│  │  - Format conversion                                  │   │
│  │  - Preprocessing                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          Segmentation Model Manager                   │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │ SAM2       │  │ YOLOv8     │  │ U-Net      │     │   │
│  │  │ Adapter    │  │ Adapter    │  │ Adapter    │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Frontend:**
- HTML5/CSS3 for structure and styling
- JavaScript (vanilla or React/Vue) for interactivity
- Canvas API or image libraries for visualization
- Fetch API for backend communication

**Backend:**
- Python with FastAPI or Flask for REST API
- PIL/Pillow for image processing
- NumPy for array operations
- Model-specific libraries:
  - SAM2: `segment-anything-2` package
  - YOLOv8: `ultralytics` package
  - U-Net: PyTorch or TensorFlow/Keras

### Communication Flow

1. User uploads image → Frontend sends multipart/form-data to `/upload` endpoint
2. Backend validates and stores image → Returns image ID
3. User selects model and clicks "Run Segmentation" → Frontend sends POST to `/segment` with image ID and model name
4. Backend loads appropriate model → Processes image → Returns mask as base64-encoded PNG
5. Frontend receives mask → Renders three panels with original, mask, and overlay

## Components and Interfaces

### Frontend Components

#### ImageUploader
Handles file selection and upload to backend.

**Interface:**
```javascript
class ImageUploader {
  // Upload image file to backend
  async uploadImage(file: File): Promise<UploadResponse>
  
  // Validate file format before upload
  validateFile(file: File): ValidationResult
  
  // Display uploaded image in UI
  displayImage(imageData: string): void
}

interface UploadResponse {
  imageId: string
  imageUrl: string
  width: number
  height: number
}

interface ValidationResult {
  valid: boolean
  error?: string
}
```

#### ModelSelector
Manages model selection dropdown.

**Interface:**
```javascript
class ModelSelector {
  // Get list of available models
  async getAvailableModels(): Promise<Model[]>
  
  // Get currently selected model
  getSelectedModel(): string
  
  // Set selected model
  setSelectedModel(modelName: string): void
}

interface Model {
  name: string
  displayName: string
  description: string
}
```

#### SegmentationRunner
Triggers segmentation and handles response.

**Interface:**
```javascript
class SegmentationRunner {
  // Run segmentation on uploaded image
  async runSegmentation(imageId: string, modelName: string): Promise<SegmentationResult>
  
  // Check if segmentation can run (image uploaded, model selected)
  canRunSegmentation(): boolean
}

interface SegmentationResult {
  maskUrl: string
  processingTime: number
  modelUsed: string
}
```

#### VisualizationPanel
Renders the three-panel view with original, mask, and overlay.

**Interface:**
```javascript
class VisualizationPanel {
  // Display original image in left panel
  displayOriginal(imageUrl: string): void
  
  // Display segmentation mask in middle panel
  displayMask(maskUrl: string): void
  
  // Display overlay in right panel
  displayOverlay(imageUrl: string, maskUrl: string, opacity: number): void
  
  // Create overlay by combining image and mask
  createOverlay(image: HTMLImageElement, mask: HTMLImageElement): HTMLCanvasElement
}
```

### Backend Components

#### API Endpoints

**POST /upload**
```python
Request:
  Content-Type: multipart/form-data
  Body: {
    "file": <image file>
  }

Response:
  Status: 200 OK
  Body: {
    "image_id": "uuid-string",
    "image_url": "/images/uuid-string.jpg",
    "width": 1024,
    "height": 768
  }

Errors:
  400: Invalid file format
  413: File too large
  500: Server error
```

**POST /segment**
```python
Request:
  Content-Type: application/json
  Body: {
    "image_id": "uuid-string",
    "model": "sam2" | "yolov8" | "unet"
  }

Response:
  Status: 200 OK
  Body: {
    "mask_url": "/masks/uuid-string-mask.png",
    "mask_base64": "base64-encoded-png-data",
    "processing_time": 2.34,
    "model_used": "sam2"
  }

Errors:
  400: Invalid image_id or model
  404: Image not found
  500: Segmentation failed
```

**GET /models**
```python
Response:
  Status: 200 OK
  Body: {
    "models": [
      {
        "name": "sam2",
        "display_name": "SAM2 (Segment Anything Model)",
        "description": "Foundation model for general-purpose segmentation"
      },
      {
        "name": "yolov8",
        "display_name": "YOLOv8 Segmentation",
        "description": "Real-time instance segmentation"
      },
      {
        "name": "unet",
        "display_name": "U-Net",
        "description": "Classic encoder-decoder architecture"
      }
    ]
  }
```

#### ImageProcessor
Handles image validation, format conversion, and preprocessing.

**Interface:**
```python
class ImageProcessor:
    def validate_image(self, file_path: str) -> ValidationResult:
        """Validate image file format and integrity"""
        pass
    
    def load_image(self, file_path: str) -> np.ndarray:
        """Load image as numpy array"""
        pass
    
    def preprocess_for_model(self, image: np.ndarray, model_name: str) -> np.ndarray:
        """Apply model-specific preprocessing"""
        pass
    
    def save_mask(self, mask: np.ndarray, output_path: str) -> str:
        """Save binary mask as PNG"""
        pass
    
    def mask_to_base64(self, mask: np.ndarray) -> str:
        """Convert mask to base64-encoded PNG"""
        pass
```

#### SegmentationModelManager
Manages loading and execution of segmentation models.

**Interface:**
```python
class SegmentationModelManager:
    def __init__(self):
        self.models: Dict[str, SegmentationModel] = {}
    
    def load_model(self, model_name: str) -> None:
        """Load specified model into memory"""
        pass
    
    def get_model(self, model_name: str) -> SegmentationModel:
        """Get loaded model instance"""
        pass
    
    def segment(self, image: np.ndarray, model_name: str) -> np.ndarray:
        """Run segmentation using specified model"""
        pass
```

#### SegmentationModel (Abstract Base)
Common interface for all segmentation models.

**Interface:**
```python
from abc import ABC, abstractmethod

class SegmentationModel(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load model weights and initialize"""
        pass
    
    @abstractmethod
    def preprocess(self, image: np.ndarray) -> Any:
        """Apply model-specific preprocessing"""
        pass
    
    @abstractmethod
    def predict(self, preprocessed_input: Any) -> np.ndarray:
        """Run inference and return binary mask"""
        pass
    
    @abstractmethod
    def postprocess(self, raw_output: Any) -> np.ndarray:
        """Convert model output to binary mask (0 or 255)"""
        pass
    
    def segment(self, image: np.ndarray) -> np.ndarray:
        """Complete segmentation pipeline"""
        preprocessed = self.preprocess(image)
        raw_output = self.predict(preprocessed)
        mask = self.postprocess(raw_output)
        return mask
```

#### SAM2Adapter
Implements SegmentationModel for SAM2.

**Interface:**
```python
class SAM2Adapter(SegmentationModel):
    def __init__(self, checkpoint_path: str, model_cfg: str):
        self.checkpoint_path = checkpoint_path
        self.model_cfg = model_cfg
        self.predictor = None
    
    def load(self) -> None:
        """Load SAM2 model"""
        # Use segment-anything-2 library
        pass
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Convert to RGB if needed, normalize"""
        pass
    
    def predict(self, preprocessed_input: np.ndarray) -> Any:
        """Run SAM2 automatic mask generation"""
        pass
    
    def postprocess(self, raw_output: Any) -> np.ndarray:
        """Combine masks and threshold to binary"""
        pass
```

#### YOLOv8Adapter
Implements SegmentationModel for YOLOv8.

**Interface:**
```python
class YOLOv8Adapter(SegmentationModel):
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
    
    def load(self) -> None:
        """Load YOLOv8 segmentation model"""
        # Use ultralytics library
        pass
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Resize and normalize for YOLO"""
        pass
    
    def predict(self, preprocessed_input: np.ndarray) -> Any:
        """Run YOLOv8 segmentation"""
        pass
    
    def postprocess(self, raw_output: Any) -> np.ndarray:
        """Extract building class masks and combine"""
        pass
```

#### UNetAdapter
Implements SegmentationModel for U-Net.

**Interface:**
```python
class UNetAdapter(SegmentationModel):
    def __init__(self, model_path: str, framework: str = "pytorch"):
        self.model_path = model_path
        self.framework = framework
        self.model = None
    
    def load(self) -> None:
        """Load U-Net model (PyTorch or TensorFlow)"""
        pass
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Resize to fixed size, normalize"""
        pass
    
    def predict(self, preprocessed_input: np.ndarray) -> np.ndarray:
        """Run U-Net forward pass"""
        pass
    
    def postprocess(self, raw_output: np.ndarray) -> np.ndarray:
        """Apply sigmoid/softmax and threshold"""
        pass
```

## Data Models

### Image Metadata
```python
class ImageMetadata:
    image_id: str          # UUID for the uploaded image
    original_filename: str # User's original filename
    file_path: str         # Server storage path
    format: str            # JPG, PNG, or TIFF
    width: int             # Image width in pixels
    height: int            # Image height in pixels
    upload_timestamp: datetime
    file_size: int         # Size in bytes
```

### Segmentation Result
```python
class SegmentationResult:
    result_id: str         # UUID for this segmentation
    image_id: str          # Reference to source image
    model_name: str        # Model used (sam2, yolov8, unet)
    mask_path: str         # Server storage path for mask
    processing_time: float # Seconds taken to segment
    timestamp: datetime
    success: bool
    error_message: Optional[str]
```

### Model Configuration
```python
class ModelConfig:
    name: str              # Internal name (sam2, yolov8, unet)
    display_name: str      # User-facing name
    description: str       # Brief description
    model_path: str        # Path to model weights
    config_path: Optional[str]  # Path to config file if needed
    is_loaded: bool        # Whether model is in memory
    input_size: Tuple[int, int]  # Expected input dimensions
```

### API Request/Response Models

```python
class UploadRequest:
    file: UploadFile

class UploadResponse:
    image_id: str
    image_url: str
    width: int
    height: int

class SegmentRequest:
    image_id: str
    model: str  # "sam2" | "yolov8" | "unet"

class SegmentResponse:
    mask_url: str
    mask_base64: str
    processing_time: float
    model_used: str

class ModelsResponse:
    models: List[ModelInfo]

class ModelInfo:
    name: str
    display_name: str
    description: str
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Valid Image Format Acceptance
*For any* image file with extension JPG, PNG, or TIFF that contains valid image data, the system should accept the upload and successfully load the image.

**Validates: Requirements 1.1, 6.1, 6.2, 6.3**

### Property 2: Invalid Format Rejection
*For any* file with an extension other than JPG, PNG, or TIFF, the system should reject the upload and return an error.

**Validates: Requirements 1.2**

### Property 3: Corrupted File Detection
*For any* file that claims to be an image format but contains corrupted or invalid data, the system should detect the corruption and reject the upload.

**Validates: Requirements 1.5**

### Property 4: Upload Success Display
*For any* successfully uploaded image, the system should display that image in the main interface.

**Validates: Requirements 1.3**

### Property 5: Model Selection State Update
*For any* model selected from the dropdown, the system state should reflect that selection and display it to the user.

**Validates: Requirements 2.3, 2.4**

### Property 6: Segmentation Execution with Valid Inputs
*For any* valid uploaded image and any selected model (SAM2, YOLOv8, or U-Net), clicking "Run Segmentation" should trigger processing using the selected model.

**Validates: Requirements 3.1, 5.1**

### Property 7: Binary Mask Generation
*For any* successful segmentation execution, the output should be a binary mask where each pixel is classified as either building (255) or background (0).

**Validates: Requirements 3.4**

### Property 8: Mask Return to Frontend
*For any* successful segmentation, the backend should return the generated mask to the frontend in a usable format (base64 or URL).

**Validates: Requirements 3.6**

### Property 9: Three-Panel Display
*For any* completed segmentation, the system should display exactly three panels: original image (left), segmentation mask (middle), and overlay (right).

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 10: Overlay Color Mapping
*For any* generated overlay, building pixels from the mask should be rendered in red with transparency, and background pixels should be fully transparent.

**Validates: Requirements 4.5, 4.6**

### Property 11: Panel Dimension Consistency
*For any* set of three visualization panels, all panels should maintain the same dimensions to ensure visual alignment.

**Validates: Requirements 4.7**

### Property 12: Model Independence
*For any* model execution, only the selected model should be invoked without loading or initializing other models.

**Validates: Requirements 5.1, 5.2**

### Property 13: Resolution and Aspect Ratio Handling
*For any* image with valid dimensions and aspect ratio, the system should successfully process and segment the image regardless of its specific resolution.

**Validates: Requirements 6.5**

### Property 14: Pre-Segmentation Image Display
*For any* uploaded image where segmentation has not yet been executed, the system should display only the original image without mask or overlay panels.

**Validates: Requirements 7.3**

### Property 15: User Interaction Feedback
*For any* user interaction (button click, file selection, model change), the system should provide immediate visual feedback indicating the action was received.

**Validates: Requirements 7.5**

### Property 16: Error Message Display
*For any* operation that fails (upload, segmentation, validation), the system should display a descriptive error message to the user.

**Validates: Requirements 1.4, 3.5**

### Property 17: Loading Indicator Display
*For any* segmentation execution that begins, the system should display a loading indicator until processing completes or fails.

**Validates: Requirements 3.3**

## Error Handling

### Upload Errors

**Invalid File Format:**
- Detection: Check file extension against whitelist [.jpg, .jpeg, .png, .tiff, .tif]
- Response: HTTP 400 with message "Unsupported file format. Please upload JPG, PNG, or TIFF images."
- UI: Display error banner, keep upload button enabled for retry

**Corrupted Image File:**
- Detection: Attempt to load image with PIL/Pillow, catch exceptions
- Response: HTTP 400 with message "Unable to read image file. The file may be corrupted."
- UI: Display error banner, clear file input

**File Too Large:**
- Detection: Check file size before processing (e.g., max 50MB)
- Response: HTTP 413 with message "Image file is too large. Maximum size is 50MB."
- UI: Display error banner with size limit

**Network Failure During Upload:**
- Detection: Timeout or connection error in fetch request
- Response: Client-side error handling
- UI: Display "Upload failed. Please check your connection and try again."

### Segmentation Errors

**Missing Image:**
- Detection: Check if image_id exists in storage before segmentation
- Response: HTTP 404 with message "Image not found. Please upload an image first."
- UI: Display error banner, disable segmentation button

**Invalid Model Name:**
- Detection: Validate model name against supported models
- Response: HTTP 400 with message "Invalid model name. Supported models: sam2, yolov8, unet."
- UI: Should not occur if dropdown is used correctly

**Model Loading Failure:**
- Detection: Exception during model initialization
- Response: HTTP 500 with message "Failed to load segmentation model. Please try again."
- UI: Display error banner, keep segmentation button enabled for retry
- Logging: Log full stack trace for debugging

**Segmentation Processing Failure:**
- Detection: Exception during model inference
- Response: HTTP 500 with message "Segmentation failed. The image may be incompatible with this model."
- UI: Display error banner with suggestion to try different model
- Logging: Log error details and image metadata

**Out of Memory:**
- Detection: Catch memory errors during processing
- Response: HTTP 500 with message "Image is too large to process. Please try a smaller image."
- UI: Display error with size recommendation

### Visualization Errors

**Mask Loading Failure:**
- Detection: Failed to load mask image in frontend
- Response: Client-side error
- UI: Display "Failed to load segmentation mask. Please try again."

**Overlay Generation Failure:**
- Detection: Canvas API errors or dimension mismatches
- Response: Client-side error
- UI: Display "Failed to generate overlay. Showing original and mask separately."
- Fallback: Show original and mask panels, hide overlay panel

### Error Recovery Strategies

1. **Automatic Retry:** For transient network errors, implement exponential backoff retry (max 3 attempts)
2. **Graceful Degradation:** If overlay generation fails, still show original and mask
3. **State Preservation:** On error, preserve uploaded image and selected model for easy retry
4. **Clear Error Messages:** Always provide actionable guidance (e.g., "try a different model", "upload smaller image")
5. **Logging:** Log all errors server-side with context (image_id, model, timestamp) for debugging

## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit Tests:** Validate specific examples, edge cases, error conditions, and integration points
- **Property-Based Tests:** Verify universal properties across randomly generated inputs

Together, these approaches provide complementary coverage: unit tests catch concrete bugs in specific scenarios, while property-based tests verify general correctness across a wide input space.

### Property-Based Testing Configuration

**Framework Selection:**
- **Frontend (JavaScript):** Use `fast-check` library for property-based testing
- **Backend (Python):** Use `hypothesis` library for property-based testing

**Test Configuration:**
- Each property test must run a minimum of 100 iterations to ensure adequate randomization coverage
- Each test must include a comment tag referencing the design document property
- Tag format: `# Feature: aerial-image-segmentation, Property {number}: {property_text}`

**Property Test Implementation:**
- Each correctness property listed above must be implemented as a single property-based test
- Tests should generate random valid inputs (images, model selections, etc.) within constraints
- Tests should verify the property holds for all generated inputs

### Unit Testing Strategy

**Frontend Unit Tests:**
- Test specific UI interactions (button clicks, file selection)
- Test edge cases (empty file, no model selected, missing image)
- Test error message display for known error conditions
- Test overlay generation with specific image/mask pairs
- Mock backend API responses for isolated testing

**Backend Unit Tests:**
- Test API endpoints with specific valid and invalid inputs
- Test image validation with known good and bad files
- Test each model adapter with sample images
- Test error handling for specific failure scenarios
- Test mask generation and encoding

**Integration Tests:**
- Test complete upload → segment → visualize workflow
- Test model switching with same image
- Test multiple segmentation runs
- Test concurrent requests handling

### Test Coverage Goals

**Critical Paths (Must Have 100% Coverage):**
- Image upload and validation
- Model selection and execution
- Mask generation and return
- Error handling and messaging

**Important Paths (Target 90% Coverage):**
- Visualization and overlay generation
- API endpoint handlers
- Image preprocessing

**Supporting Paths (Target 70% Coverage):**
- UI feedback and loading states
- Logging and monitoring

### Example Property-Based Tests

**Backend (Python with Hypothesis):**
```python
from hypothesis import given, strategies as st
import numpy as np

# Feature: aerial-image-segmentation, Property 7: Binary Mask Generation
@given(st.integers(min_value=100, max_value=2000),
       st.integers(min_value=100, max_value=2000),
       st.sampled_from(['sam2', 'yolov8', 'unet']))
def test_binary_mask_generation(width, height, model_name):
    """For any successful segmentation, output should be binary mask"""
    # Generate random image
    image = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    
    # Run segmentation
    model = model_manager.get_model(model_name)
    mask = model.segment(image)
    
    # Verify binary output
    assert mask.dtype == np.uint8
    assert set(np.unique(mask)).issubset({0, 255})
    assert mask.shape == (height, width)
```

**Frontend (JavaScript with fast-check):**
```javascript
// Feature: aerial-image-segmentation, Property 5: Model Selection State Update
fc.assert(
  fc.property(
    fc.constantFrom('sam2', 'yolov8', 'unet'),
    (modelName) => {
      const selector = new ModelSelector();
      selector.setSelectedModel(modelName);
      return selector.getSelectedModel() === modelName;
    }
  ),
  { numRuns: 100 }
);
```

### Manual Testing Checklist

While automated tests cover functional correctness, manual testing should verify:
- Visual quality of overlays (color, transparency)
- UI responsiveness and feedback
- Error message clarity and helpfulness
- Cross-browser compatibility
- Performance with large images
- Accessibility (keyboard navigation, screen readers)

### Performance Testing

- Measure segmentation time for each model with various image sizes
- Target: < 5 seconds for 1024x1024 images on standard hardware
- Monitor memory usage during processing
- Test concurrent request handling (multiple users)

### Security Testing

- Test file upload size limits
- Test malicious file uploads (executables renamed as images)
- Test path traversal attempts in image_id parameters
- Validate all user inputs are sanitized
- Test rate limiting on API endpoints
