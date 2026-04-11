# BHUMI AI — User Manual

Welcome to BHUMI AI. This application helps you find and count buildings in aerial or satellite photos using artificial intelligence. You don't need any technical knowledge to use it — just upload your images and let the AI do the work.

---

## What does BHUMI AI do?

When you take a photo from a drone or download a satellite image, it can be hard to manually count or outline every building in it. BHUMI AI does this automatically. It looks at your image, finds every building, draws a border around each one, and tells you how many there are. You can then save those results in different file formats.

---

## Getting Started

Open your web browser and go to:

```
http://localhost:4000
```

You will see the BHUMI AI interface with a sidebar on the left. The sidebar has four sections:

| Icon | Section | What it does |
|------|---------|--------------|
| 🖼️ | Single Processing | Process one image at a time |
| 📦 | Batch Processing | Process many images at once |
| 📊 | Dashboard | See your activity and statistics |
| ⚙️ | Settings / Profile | Change your name, theme, and preferences |

---

## Section 1 — Single Processing

Use this when you have **one image** you want to analyse.

### Step 1 — Upload your image

- Click the **Browse Files** button, or drag and drop your image into the upload box.
- Supported formats: JPG, PNG, TIFF
- Maximum file size: 50 MB

Once uploaded, your image will appear on the right side of the screen.

### Step 2 — Choose an AI model

You will see two options:

- **YOLOv8** — faster, works well for dense city areas with many buildings close together.
- **Mask R-CNN** — slower but more accurate for buildings with unusual or irregular shapes.

Click on the one you want to use. If you are unsure, start with YOLOv8.

### Step 3 — Detect buildings

Click the **Detect Buildings** button. The AI will analyse your image. This usually takes a few seconds. When it finishes, you will see:

- The image with coloured outlines drawn around each detected building
- A count of how many buildings were found
- How long the processing took

### Step 4 — Save your results

Below the image you will find save options. You can download your results as:

- **JSON** — a data file listing all building outlines (good for use in other software)
- **PNG** — your image with building outlines drawn on it
- **JPEG** — same as PNG but smaller file size

### GeoJSON Export (optional)

If your image came with a **world file** (a small file ending in `.pgw`, `.tfw`, or `.jgw` that contains location information), you can export your results as a **GeoJSON** file. GeoJSON is a format that places your building outlines on a real map with GPS coordinates.

To do this:
1. Upload your world file using the **World File** section in the left panel
2. Click **Generate GeoJSON**
3. Click **Download GeoJSON** to save the file

---

## Section 2 — Batch Processing

Use this when you have **many images** you want to process all at once. Instead of uploading them one by one, you put them all in a ZIP file and upload that.

### Step 1 — Prepare your ZIP file

Put all your aerial images into a single ZIP file on your computer. The ZIP can contain up to 50 images, and the total size must be under 500 MB.

### Step 2 — Upload the ZIP

- Click **Step 1: Upload Images ZIP** and select your ZIP file.
- The app will unpack it and show you a list of all the images it found.

### Step 3 — Upload world files (optional)

If you have world files for your images (for GeoJSON export), create a second ZIP containing all the world files and upload it using **Step 2: Upload World Files ZIP**. The app will automatically match each world file to the correct image by filename.

### Step 4 — Choose a model and run

- Select either **YOLOv8** or **Mask R-CNN** from the dropdown.
- Click **Run Batch**. The app will process each image one by one.

You will see a progress grid showing each image as a small card. Each card shows:

- A thumbnail of the image
- A status badge: **Pending**, **Processing**, **Done**, or **Failed**
- The number of buildings found (once done)

### Step 5 — Review and edit

Click on any image card to open the **Polygon Editor**. Here you can:

- See the building outlines drawn on the image
- Add new outlines by drawing on the image
- Delete outlines that are incorrect
- Click **Save** when you are happy with the result

### Step 6 — Download results

Once processing is complete, click the **Download** button and choose your format:

- **JSON** — building data for each image
- **PNG** — images with outlines drawn on them
- **JPEG** — same as PNG, smaller file size
- **GeoJSON** — georeferenced building outlines (only available if world files were uploaded)

If any image failed, you can click the **Retry** button on that card to try again.

---

## Section 3 — Dashboard

The Dashboard gives you a live overview of everything that has happened in the application.

### Summary cards (top row)

| Card | What it shows |
|------|--------------|
| Images Processed | Total number of images the AI has analysed |
| Avg Proc. Time | Average time it takes to process one image |
| Total Time in App | How long you have been using the application in total |

### Model Usage (circle chart)

Shows which AI model you have used more — YOLOv8 or Mask R-CNN. Each colour represents one model. The bigger the slice, the more you used that model.

### Time in App (clock chart)

A 24-hour clock showing **when today** you were using the application. The circle represents the full day (midnight at the top). The coloured slices show the hours you were active. The legend below shows exactly which hours and how many minutes you spent in each.

For example, if you see a blue slice at the 2 o'clock position with "14:00 — 23m", it means you used the app for 23 minutes during the 2pm hour.

### Export Breakdown (horizontal bar)

Shows how many files you have downloaded and in which format. Each colour is a different format:

- 🟢 Green = JSON
- 🔵 Blue = PNG
- 🟣 Purple = GeoJSON
- 🩵 Teal = JPEG

### Single Processing chart

A bar chart showing how many buildings were detected in each image you processed individually.

### Batch Processing chart

A bar chart showing how many buildings were detected in each image from your batch jobs.

### Recent Activity table

A table listing every image that has been processed, showing:

- When it was processed
- The image filename
- Which AI model was used
- How many buildings were detected
- What format it was exported in (if downloaded)

Click **↻ Refresh** at any time to update the dashboard with the latest data.

---

## Section 4 — Settings & Profile

### Personal Info

Update your username and email address. Click **Save Changes** when done.

### Preferences

- **Default Intelligence Model** — choose which AI model is selected by default when you open the app.
- **Default Export Format** — choose which file format is pre-selected when downloading.
- **Hardware Acceleration** — leave this on for faster performance if your computer has a graphics card.

Click **Save Preferences** when done.

### Appearance

Switch between **Dark** and **Light** themes. Click **Apply Theme** to save your choice.

---

## Tips

- If you are processing images for the first time, the AI model needs a moment to load. The very first image may take a little longer than usual — this is normal.
- For best results, use images where buildings are clearly visible from above and not heavily obscured by trees or shadows.
- If a batch image fails, check that the image is not corrupted and try the Retry button.
- World files must have the same base name as their matching image. For example, `photo1.png` needs a world file called `photo1.pgw`.

---

## Supported File Formats

| Type | Formats accepted |
|------|-----------------|
| Images | JPG, JPEG, PNG, TIFF, TIF |
| World files | .pgw, .tfw, .jgw, .wld |
| Batch upload | .zip |

---

## Glossary

**Segmentation** — the process of the AI identifying and outlining objects (buildings) in an image.

**Polygon** — the outline drawn around a building. It is a shape made of connected points.

**GeoJSON** — a file format that stores shapes with real-world GPS coordinates, so they can be placed on a map.

**World file** — a small text file that tells the app where on Earth your image is located.

**Batch** — processing many images at the same time instead of one by one.

**Model** — the AI brain used to detect buildings. BHUMI AI has two: YOLOv8 (fast) and Mask R-CNN (precise).
