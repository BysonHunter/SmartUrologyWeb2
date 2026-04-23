# SmartUrologyWeb2

Web application for DICOM analysis in urology: series selection, object detection (kidneys/stones), parameter calculation, and PDF report generation.

## Features

- Upload a ZIP archive with DICOM files via the web UI.
- Detect available series and let the user choose which one to process.
- Run a full processing pipeline:
  - DICOM series reading
  - Object detection
  - Parameter calculation
  - Result packaging and PDF report generation
- Track processing progress in real time.
- Download the generated PDF report.

## Tech Stack

- Python 3.11
- Flask
- pydicom
- OpenCV
- PyTorch + Ultralytics
- NumPy / SciPy / pandas / matplotlib

## Project Structure

- `main_frontend.py` - Flask app, routes, sessions, progress endpoints.
- `main_backend.py` - core processing orchestration.
- `readDicom/` - DICOM parsing and helpers.
- `detectObj/` - object detection logic and model weights.
- `buildObj/` - object metrics/parameters calculation.
- `templates/`, `static/` - frontend templates and assets.
- `in/` - uploaded and unpacked input data.
- `workdir/` - intermediate processing files.
- `out/` - output artifacts and generated reports.

## Quick Start (Local)

1. Create and activate virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python main_frontend.py
```

4. Open:

`http://localhost:5000`

## Docker

Build and run:

```bash
docker compose up --build
```

Service will be available at `http://localhost:5000`.

## Usage Flow

1. Open the web page.
2. Upload a ZIP archive with DICOM study files.
3. Select one of the detected series.
4. Wait for processing to finish.
5. Download the generated PDF report.

## Troubleshooting

- **No series found in ZIP**
  - Check archive contents and folder structure.
  - Make sure DICOM files are actually present after extraction.

- **Processing is slow**
  - First run may be slower due to model loading.
  - Large studies (many slices) require more time and RAM.

- **No PDF in output**
  - Check the session output folder in `out/<session_id>/`.
  - Review logs from `main_frontend.py` for processing errors.

- **Docker compose FLASK_APP typo**
  - In `docker-compose.yml`, ensure:
    - `FLASK_APP=main_frontend.py`
  - Current value with `.py.py` may cause startup issues in some setups.

## Notes

- The app uses per-session folders to isolate user data.
- Background cleanup removes stale session data periodically.
- Keep model weights in `detectObj/weights` available for inference.
