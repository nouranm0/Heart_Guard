# ECG Validation API Service

This service provides an HTTP API to validate ECG files (Images, PDF, XML, etc.) and detect if they are fake or invalid.

## Installation

Ensure you have the requirements installed:

```bash
pip install flask numpy scipy opencv-python Pillow wfdb
# Optional for PDF
pip install pymupdf
```

## Running the Server

Start the API server:

```bash
python api_server.py
```
The server will start at `http://localhost:5000`.

## API Usage

### 1. Web Interface
Open `http://localhost:5000` in your browser to use the drag-and-drop validation tool.

### 2. Programmatic API

**Endpoint:** `POST /validate`
**Format:** `multipart/form-data` with key `file`

#### Example (curl)
```bash
curl -X POST -F "file=@test_tachy_135bpm.jpg" http://localhost:5000/validate
```

#### Example (Python)
```python
import requests

url = 'http://localhost:5000/validate'
files = {'file': open('patient_ecg.pdf', 'rb')}
response = requests.post(url, files=files)
print(response.json())
```

#### Response Format
```json
{
  "filename": "patient_ecg.pdf",
  "is_valid": true,
  "confidence": 0.85,
  "reasons": [],
  "checks": {
    "periodicity": { "pass": true, "score": 0.25 },
    "einthoven": { "pass": true, "correlation": 0.88 },
    ...
  }
}
```

If `is_valid` is `false`, the `reasons` array will explain why (e.g., "Leads uncorrelated", "No heartbeat pattern").
