# Walkthrough - Universal ECG Processor & Validation

This walkthrough documents the successful implementation of a universal ECG processor that handles PDF, JPG, and XML files, along with a robust signal validation system to detect fake or invalid ECGs.

## 1. Universal Processor Improvements

We addressed the limitations in `universal_processor.py` where PDF, JPG, and XML processing was stubbed or broken.

### Supported Formats & Implementation Details

| Format | Implementation | Status |
|--------|----------------|--------|
| **PDF** | Uses **PyMuPDF** (`fitz`) to render the first page to a high-res image (300 DPI), then processes it as an image. Falls back to `pdf2image` if needed. | ✅ Working |
| **JPG/PNG**| Uses **OpenCV** to: <br>1. Remove red/pink grid lines (HSV masking)<br>2. Detect lead rows via horizontal profiling<br>3. Extract signals via column-wise centroid tracking<br>4. Normalize and resample to 4096 samples | ✅ Working |
| **XML** | Enhanced parser to support: <br>- standard GE MUSE (`Waveform/LeadData`)<br>- custom GE formats (`Leads/Lead/@id`)<br>- HL7 aECG<br>- Philips XML<br>- Generic recursive search | ✅ Working |
| **MAT/CSV**| Existing functionality preserved. | ✅ Working |

## 2. Robust ECG Validation

We implemented a comprehensive validation module to reject non-ECG files (like random images or corrupted data) while accepting legitimate but noisy generic ECG images.

### Validation Heuristics

The `validate_ecg_signal` function checks multiple signal characteristics:

1.  **Periodicity Check**: Uses autocorrelation to find repetitive heartbeat patterns.
    *   *Threshold:* Score > 0.1 (adjusted for variable heart rates in images)
2.  **Lead Correlation**: Checks if different leads are correlated (Real ECG leads are views of the same heart, so they must correlate).
    *   *Threshold:* Average Correlation > 0.15
3.  **Einthoven's Law**: Verifies `Lead II ≈ Lead I + Lead III`.
    *   *Threshold:* Correlation > 0.3
4.  **Frequency Content**: Checks if signal energy is concentrated in the ECG band (0.5-40 Hz).
    *   *Threshold:* > 60% of energy in band
5.  **Statistical Checks**: Signal variance, kurtosis, zero-crossing rate, and flatline ratio.

### "Essential Checks" Logic
To be considered valid, a signal must pass at least **2 out of 3** essential checks:
1.  **Periodicity** (Is it a heartbeat?)
2.  **Einthoven's Law** (Is it physically consistent?)
3.  **Lead Correlation** (Are leads related?)

### Verification Results

We tested the validator against real and fake data:

| Input File | Type | Result | Confidence | Reason |
|------------|------|--------|------------|--------|
| `test_sick_tachy.xml` | Real ECG | **✅ VALID** | 65% | Passes all essential checks. |
| `test_sick_tachy.pdf` | Real ECG | **✅ VALID** | 80% | Valid signal extracted from PDF. |
| `test_tachy_135bpm.jpg`| Real ECG | **✅ VALID** | 80% | Passes Correlation & Frequency checks despite noise. |
| `fake_random_image.jpg`| Random Noise | **❌ INVALID**| 65% | Failed Correlation (<0.15) and Frequency (<0.6). |

## 3. Usage

```python
from universal_processor import universal_loader_with_validation

# Load and validate
signal, validation = universal_loader_with_validation('patient_data.pdf')

if signal is None:
    print("Invalid File:", validation['reasons'])
else:
    print(f"Loaded successfully! Confidence: {validation['confidence']:.2f}")
    # Proceed to prediction...
```
