# Requirements Document

## Introduction

This feature adds a batch processing section to the existing aerial image segmentation web application. Users can upload a ZIP archive containing multiple aerial images, select a segmentation model, run building boundary detection on all images in the batch, review and edit the detected polygons per image, and download all results in a chosen output format (JSON, PNG, or JPEG).

The feature reuses the existing single-image pipeline (upload → segment → boundary detect → editable polygons) and extends it to operate over a collection of images with a unified batch UI and a bulk download step.

## Glossary

- **Batch_Processor**: The frontend component that manages the batch ZIP upload, per-image processing pipeline, and bulk download.
- **Batch_API**: The backend FastAPI endpoints that handle ZIP extraction, per-image segmentation, boundary detection, and ZIP packaging of results.
- **ZIP_Archive**: A `.zip` file uploaded by the user that contains one or more aerial images in JPG, PNG, or TIFF format.
- **Batch_Job**: A server-side record that tracks the state of a single batch processing run, identified by a `batch_id`.
- **Batch_Item**: One image within a Batch_Job, identified by an `item_id`, with its own segmentation mask, boundary polygons, and edit state.
- **Polygon_Editor**: The interactive canvas component (already used in single-image mode) that allows users to move, resize, add, and delete building boundary polygons.
- **Output_Format**: The user-selected format for downloaded results — one of `json`, `png`, or `jpeg`.
- **Model_Selector**: The existing dropdown component that lists available segmentation models (SAM2, YOLOv8m-custom, Mask R-CNN).

---

## Requirements

### Requirement 1: ZIP File Upload

**User Story:** As a user, I want to upload a ZIP file containing multiple aerial images, so that I can process a batch of images without uploading them one by one.

#### Acceptance Criteria

1. THE Batch_Processor SHALL display a dedicated ZIP upload section that is visually separate from the existing single-image upload section.
2. WHEN a user selects a file in the ZIP upload input, THE Batch_Processor SHALL validate that the file has a `.zip` extension.
3. IF a user selects a file that does not have a `.zip` extension, THEN THE Batch_Processor SHALL display an error message and reject the file.
4. WHEN a user selects a valid ZIP file, THE Batch_Processor SHALL display the selected filename and file size.
5. WHEN a user clicks the upload button for the ZIP file, THE Batch_Processor SHALL send the ZIP to the Batch_API and display an upload progress indicator.
6. WHEN the Batch_API receives a ZIP file, THE Batch_API SHALL extract all images with `.jpg`, `.jpeg`, `.png`, `.tiff`, or `.tif` extensions from the archive.
7. IF the ZIP file contains no supported image files, THEN THE Batch_API SHALL return an error with a descriptive message.
8. IF the ZIP file is larger than 500MB, THEN THE Batch_API SHALL reject the upload with a descriptive error message.
9. WHEN the ZIP is successfully uploaded and extracted, THE Batch_API SHALL return a `batch_id` and the list of extracted image filenames.
10. WHEN the upload succeeds, THE Batch_Processor SHALL display the list of image filenames found in the ZIP.

---

### Requirement 2: Model Selection for Batch

**User Story:** As a user, I want to select a segmentation model for the entire batch, so that all images are processed consistently with the same model.

#### Acceptance Criteria

1. THE Batch_Processor SHALL display the Model_Selector dropdown within the batch section.
2. WHEN a user selects a model from the Model_Selector, THE Batch_Processor SHALL store the selected model and apply it to all images in the batch.
3. THE Batch_Processor SHALL disable the "Run Batch" button until both a ZIP file has been successfully uploaded and a model has been selected.

---

### Requirement 3: Batch Segmentation and Boundary Detection

**User Story:** As a user, I want to run segmentation and building boundary detection on all images in the batch, so that I can get building polygons for every image automatically.

#### Acceptance Criteria

1. WHEN a user clicks the "Run Batch" button, THE Batch_Processor SHALL send a batch processing request to the Batch_API with the `batch_id` and selected model name.
2. WHEN the Batch_API receives a batch processing request, THE Batch_API SHALL run segmentation followed by boundary detection on each Batch_Item sequentially.
3. WHILE the Batch_API is processing a Batch_Job, THE Batch_API SHALL update the progress state of each Batch_Item as it completes (pending → processing → done or failed).
4. WHILE the Batch_API is processing a Batch_Job, THE Batch_Processor SHALL poll for progress and display a per-image status indicator showing pending, processing, done, or failed state.
5. IF segmentation or boundary detection fails for a Batch_Item, THEN THE Batch_API SHALL mark that item as failed with an error message and continue processing the remaining items.
6. WHEN all Batch_Items have been processed, THE Batch_API SHALL mark the Batch_Job as complete.
7. WHEN the Batch_Job is complete, THE Batch_Processor SHALL display the results for all processed images.

---

### Requirement 4: Per-Image Boundary Editing

**User Story:** As a user, I want to review and edit the detected building boundaries for each image in the batch, so that I can correct any inaccurate detections before downloading.

#### Acceptance Criteria

1. WHEN a Batch_Job is complete, THE Batch_Processor SHALL display a thumbnail grid of all processed images with their detected boundary overlays.
2. WHEN a user clicks on a thumbnail, THE Batch_Processor SHALL open the Polygon_Editor for that Batch_Item, showing the original image with editable polygon overlays.
3. WHILE the Polygon_Editor is open for a Batch_Item, THE Polygon_Editor SHALL allow the user to move, resize, add, and delete individual building polygons.
4. WHEN a user saves edits in the Polygon_Editor, THE Batch_Processor SHALL update the stored polygon data for that Batch_Item.
5. WHEN a user closes the Polygon_Editor without saving, THE Batch_Processor SHALL discard the unsaved changes and retain the previous polygon data for that Batch_Item.
6. THE Batch_Processor SHALL display a visual indicator on each thumbnail to distinguish items that have been edited from items that have not been edited.

---

### Requirement 5: Bulk Download

**User Story:** As a user, I want to download all processed images and their boundary data in a selected format, so that I can use the results in downstream workflows.

#### Acceptance Criteria

1. THE Batch_Processor SHALL display an output format selector with options: JSON, PNG, JPEG.
2. WHEN a user selects an output format, THE Batch_Processor SHALL store the selection and apply it to all items in the download.
3. WHEN a user clicks the "Download All" button, THE Batch_Processor SHALL send a download request to the Batch_API with the `batch_id` and selected output format.
4. WHEN the Batch_API receives a download request with format `json`, THE Batch_API SHALL package a ZIP archive containing one JSON file per Batch_Item with the image filename, polygon coordinates, and building count.
5. WHEN the Batch_API receives a download request with format `png` or `jpeg`, THE Batch_API SHALL package a ZIP archive containing one rendered image per Batch_Item with the boundary polygons drawn on the original image.
6. WHEN the output ZIP is ready, THE Batch_API SHALL return it as a file download response.
7. WHEN the download is ready, THE Batch_Processor SHALL trigger the browser to download the ZIP file.
8. IF no Batch_Items have been successfully processed, THEN THE Batch_Processor SHALL disable the "Download All" button.

---

### Requirement 6: Error Handling and Resilience

**User Story:** As a user, I want clear feedback when something goes wrong during batch processing, so that I understand what failed and can take corrective action.

#### Acceptance Criteria

1. IF the ZIP upload fails due to a network error, THEN THE Batch_Processor SHALL display a descriptive error message and allow the user to retry the upload.
2. IF a Batch_Item fails during segmentation or boundary detection, THEN THE Batch_Processor SHALL display the error reason next to that item's thumbnail and allow the user to skip or retry that item individually.
3. IF the Batch_API returns an error for the entire batch job, THEN THE Batch_Processor SHALL display the error and allow the user to restart the batch.
4. WHEN a Batch_Item is retried, THE Batch_API SHALL re-run segmentation and boundary detection for that item only, without reprocessing the rest of the batch.
5. IF the download request fails, THEN THE Batch_Processor SHALL display an error message and allow the user to retry the download.
