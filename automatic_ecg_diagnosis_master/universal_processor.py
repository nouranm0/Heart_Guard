import os
import numpy as np
import scipy.io
import pandas as pd
import h5py
import xmltodict
import wfdb
import cv2
from PIL import Image
import base64
from scipy import signal as scipy_signal
from scipy.ndimage import gaussian_filter1d
from scipy.stats import kurtosis, pearsonr
from scipy.fft import fft, fftfreq

# Standard 12-lead order
LEAD_ORDER = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

# ECG Validation thresholds (fine-tuned for sick/noisy ECGs)
ECG_VALIDATION_CONFIG = {
    'min_periodicity_score': 0.05,     # Minimum autocorrelation peak (lowered for arrhythmias)
    'min_einthoven_correlation': 0.25, # Lead I + Lead III ≈ Lead II (lowered for axis deviation/noise)
    'max_flatline_ratio': 0.4,         # Max ratio of near-zero values
    'min_variance': 0.00001,           # Minimum signal variance
    'max_variance': 50.0,              # Maximum signal variance
    'min_kurtosis': -3.0,              # Minimum kurtosis
    'max_kurtosis': 100.0,             # Maximum kurtosis
    'min_zcr': 0.001,                  # Minimum zero-crossing rate
    'max_zcr': 0.6,                    # Maximum zero-crossing rate
    'ecg_freq_energy_ratio': 0.55,     # Min ratio of energy in ECG band (lowered from 0.6)
}

def load_mat_signal(mat_path):
    """Loads signal from CODE-15% MAT file."""
    try:
        data = scipy.io.loadmat(mat_path)
        if 'feats' in data:
            return data['feats'].T
        return None
    except:
        return None

def load_csv_signal(csv_path):
    """Loads signal from CSV file. Assumes 12 columns, or 12 rows."""
    try:
        df = pd.read_csv(csv_path)
        # If columns are leads
        if df.shape[1] == 12:
            return df.values
        # If rows are leads
        if df.shape[0] == 12:
            return df.values.T
        return None
    except:
        return None

def load_xml_signal(xml_path):
    """Parses ECG XML (supports GE MUSE, HL7 aECG, Philips, and generic formats)."""
    try:
        with open(xml_path, 'rb') as f:
            content = f.read()
        
        data = xmltodict.parse(content)
        
        # Try multiple XML formats
        signal = None
        
        # 1. GE MUSE Format
        signal = _parse_ge_muse(data)
        if signal is not None:
            return signal
            
        # 2. HL7 aECG Format
        signal = _parse_hl7_aecg(data)
        if signal is not None:
            return signal
            
        # 3. Philips Format
        signal = _parse_philips(data)
        if signal is not None:
            return signal
            
        # 4. Generic XML with lead data
        signal = _parse_generic_xml(data)
        if signal is not None:
            return signal
            
        print(f"Could not parse XML format. Root keys: {list(data.keys())}")
        return None
        
    except Exception as e:
        print(f"XML Error: {e}")
        return None

def _parse_ge_muse(data):
    """Parse GE MUSE XML format."""
    if 'RestingECG' not in data:
        return None
        
    try:
        ecg_data = data['RestingECG']
        leads_data = {}
        sample_rate = 500  # Default
        
        # Check for Waveform structure (original GE MUSE format)
        waveforms = ecg_data.get('Waveform', [])
        if waveforms:
            if not isinstance(waveforms, list):
                waveforms = [waveforms]
            
            for wf in waveforms:
                wf_type = wf.get('@Type', wf.get('Type', ''))
                
                # Get sample rate
                if 'SampleRate' in wf:
                    sample_rate = int(wf['SampleRate'])
                
                # Check for Leads/Lead structure (custom format in test XML)
                if 'Leads' in wf:
                    leads_container = wf['Leads']
                    lead_list = leads_container.get('Lead', [])
                    if not isinstance(lead_list, list):
                        lead_list = [lead_list]
                    
                    for lead in lead_list:
                        lead_name = lead.get('@id', lead.get('id', ''))
                        raw_data = lead.get('WaveformData', '')
                        
                        if raw_data and lead_name:
                            if ',' in raw_data:
                                signal = np.array([float(x) for x in raw_data.split(',') if x.strip()])
                            else:
                                signal = np.array([float(x) for x in raw_data.split() if x.strip()])
                            
                            if len(signal) > 0:
                                leads_data[lead_name] = signal
                
                # Check for LeadData structure (standard GE format)
                elif wf_type == 'Rhythm' or 'LeadData' in wf:
                    lead_data_list = wf.get('LeadData', [])
                    if not isinstance(lead_data_list, list):
                        lead_data_list = [lead_data_list]
                        
                    for lead in lead_data_list:
                        lead_name = lead.get('LeadByteCode', lead.get('LeadID', ''))
                        raw_data = lead.get('WaveFormData', '')
                        
                        if raw_data:
                            if ',' in raw_data:
                                signal = np.array([float(x) for x in raw_data.split(',') if x.strip()])
                            elif ' ' in raw_data:
                                signal = np.array([float(x) for x in raw_data.split() if x.strip()])
                            else:
                                try:
                                    decoded = base64.b64decode(raw_data)
                                    signal = np.frombuffer(decoded, dtype=np.int16).astype(float)
                                except:
                                    signal = np.array([float(x) for x in raw_data.split() if x.strip()])
                            
                            if len(signal) > 0:
                                leads_data[lead_name] = signal
        
        # Also check for direct Leads structure under Waveform
        if not leads_data and 'Waveform' in ecg_data:
            wf = ecg_data['Waveform']
            if isinstance(wf, dict):
                if 'SampleRate' in wf:
                    sample_rate = int(wf['SampleRate'])
                    
                if 'Leads' in wf:
                    leads_container = wf['Leads']
                    lead_list = leads_container.get('Lead', [])
                    if not isinstance(lead_list, list):
                        lead_list = [lead_list]
                    
                    for lead in lead_list:
                        lead_name = lead.get('@id', lead.get('id', ''))
                        raw_data = lead.get('WaveformData', '')
                        
                        if raw_data and lead_name:
                            if ',' in raw_data:
                                signal = np.array([float(x) for x in raw_data.split(',') if x.strip()])
                            else:
                                signal = np.array([float(x) for x in raw_data.split() if x.strip()])
                            
                            if len(signal) > 0:
                                leads_data[lead_name] = signal
        
        if leads_data:
            print(f"Found {len(leads_data)} leads: {list(leads_data.keys())}")
            
            # Helper to normalize lead names
            def normalize_lead(name):
                n = name.strip().upper().replace('LEAD', '').replace('_', '').replace(' ', '')
                mapping = {
                    '1': 'I', '2': 'II', '3': 'III',
                    'I': 'I', 'II': 'II', 'III': 'III',
                    'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF',
                    'VR': 'aVR', 'VL': 'aVL', 'VF': 'aVF',
                    'V1': 'V1', 'V2': 'V2', 'V3': 'V3', 
                    'V4': 'V4', 'V5': 'V5', 'V6': 'V6',
                    'MCL1': 'V1' 
                }
                return mapping.get(n, mapping.get(n.lstrip('0'), name)) # Handle '01'

            signals = []
            normalized_leads = {}
            
            # Create a normalized map
            for raw_name, signal in leads_data.items():
                norm = normalize_lead(raw_name)
                if norm not in normalized_leads:
                     normalized_leads[norm] = signal
            
            # Try to build ordered set
            for lead in LEAD_ORDER:
                if lead in normalized_leads:
                    signals.append(normalized_leads[lead])
                elif lead.upper() in normalized_leads: # Redundant but safe
                    signals.append(normalized_leads[lead.upper()])
            
            if len(signals) == 12:
                # Stack and transpose to (samples, 12)
                min_len = min(len(s) for s in signals)
                signals = [s[:min_len] for s in signals]
                return np.array(signals).T
            
            # Fallback 2: If we have exactly 12 leads but names didn't match perfectly, assume standard order
            if len(leads_data) == 12:
                print("Exact lead matching failed, using available 12 leads in finding order.")
                signals = list(leads_data.values())
                min_len = min(len(s) for s in signals)
                signals = [s[:min_len] for s in signals]
                return np.array(signals).T
            else:
                print(f"Only matched {len(signals)} leads out of 12")
                
        return None
    except Exception as e:
        print(f"GE MUSE parse error: {e}")
        return None

def _parse_hl7_aecg(data):
    """Parse HL7 aECG (annotated ECG) format."""
    if 'AnnotatedECG' not in data:
        return None
    
    try:
        aecg = data['AnnotatedECG']
        
        # Navigate to the component containing waveform data
        component = aecg.get('component', {})
        if isinstance(component, list):
            component = component[0]
        
        series = component.get('series', {})
        if isinstance(series, list):
            series = series[0]
            
        component_list = series.get('component', [])
        if not isinstance(component_list, list):
            component_list = [component_list]
        
        leads_data = {}
        
        for comp in component_list:
            seq = comp.get('sequenceSet', {})
            components = seq.get('component', [])
            if not isinstance(components, list):
                components = [components]
            
            for c in components:
                sequence = c.get('sequence', {})
                code = sequence.get('code', {})
                lead_code = code.get('@code', code.get('code', ''))
                
                # Get digits (the actual waveform values)
                value = sequence.get('value', {})
                digits = value.get('digits', '')
                
                if digits and lead_code:
                    signal = np.array([float(x) for x in digits.split() if x.strip()])
                    if len(signal) > 0:
                        # Map HL7 lead codes to standard names
                        lead_map = {
                            'MDC_ECG_LEAD_I': 'I', 'MDC_ECG_LEAD_II': 'II', 
                            'MDC_ECG_LEAD_III': 'III', 'MDC_ECG_LEAD_AVR': 'aVR',
                            'MDC_ECG_LEAD_AVL': 'aVL', 'MDC_ECG_LEAD_AVF': 'aVF',
                            'MDC_ECG_LEAD_V1': 'V1', 'MDC_ECG_LEAD_V2': 'V2',
                            'MDC_ECG_LEAD_V3': 'V3', 'MDC_ECG_LEAD_V4': 'V4',
                            'MDC_ECG_LEAD_V5': 'V5', 'MDC_ECG_LEAD_V6': 'V6'
                        }
                        lead_name = lead_map.get(lead_code, lead_code)
                        leads_data[lead_name] = signal
        
        if len(leads_data) >= 12:
            signals = [leads_data.get(lead) for lead in LEAD_ORDER if lead in leads_data]
            if len(signals) == 12:
                min_len = min(len(s) for s in signals)
                signals = [s[:min_len] for s in signals]
                return np.array(signals).T
                
        return None
    except Exception as e:
        print(f"HL7 aECG parse error: {e}")
        return None

def _parse_philips(data):
    """Parse Philips XML format."""
    # Look for Philips-specific keys
    root_key = None
    for key in ['SierraECG', 'ECG', 'PhilipsECG']:
        if key in data:
            root_key = key
            break
    
    if root_key is None:
        return None
    
    try:
        ecg_data = data[root_key]
        waveforms = ecg_data.get('Waveforms', ecg_data.get('waveforms', {}))
        
        leads_data = {}
        
        # Try to find lead data in various structures
        for key in ['Lead', 'lead', 'LeadData']:
            if key in waveforms:
                lead_list = waveforms[key]
                if not isinstance(lead_list, list):
                    lead_list = [lead_list]
                
                for lead in lead_list:
                    lead_id = lead.get('LeadID', lead.get('leadId', lead.get('@id', '')))
                    wave_data = lead.get('Data', lead.get('data', lead.get('WaveFormData', '')))
                    
                    if wave_data:
                        signal = np.array([float(x) for x in str(wave_data).split(',') if x.strip()])
                        if len(signal) > 0:
                            leads_data[lead_id] = signal
        
        if len(leads_data) >= 12:
            signals = [leads_data.get(lead) for lead in LEAD_ORDER if lead in leads_data]
            if len(signals) == 12:
                min_len = min(len(s) for s in signals)
                signals = [s[:min_len] for s in signals]
                return np.array(signals).T
                
        return None
    except Exception as e:
        print(f"Philips parse error: {e}")
        return None

def _parse_generic_xml(data):
    """Try to parse generic XML with lead data."""
    try:
        # Recursively search for anything that looks like lead data
        leads_data = {}
        
        def search_leads(obj, depth=0):
            if depth > 10:  # Prevent infinite recursion
                return
            if isinstance(obj, dict):
                # Check if this dict contains lead-like data
                for key, value in obj.items():
                    key_lower = key.lower()
                    if any(lead.lower() in key_lower for lead in LEAD_ORDER):
                        if isinstance(value, str):
                            try:
                                signal = np.array([float(x) for x in value.split(',') if x.strip()])
                                if len(signal) > 100:  # Reasonable ECG length
                                    for lead in LEAD_ORDER:
                                        if lead.lower() in key_lower:
                                            leads_data[lead] = signal
                                            break
                            except:
                                pass
                    search_leads(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    search_leads(item, depth + 1)
        
        search_leads(data)
        
        if len(leads_data) >= 12:
            signals = [leads_data.get(lead) for lead in LEAD_ORDER if lead in leads_data]
            if len(signals) == 12:
                min_len = min(len(s) for s in signals)
                signals = [s[:min_len] for s in signals]
                return np.array(signals).T
        
        return None
    except:
        return None

def extract_signal_from_pdf(pdf_path):
    """Extract ECG signal from PDF file using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        
        # Open the PDF
        pdf_doc = fitz.open(pdf_path)
        if len(pdf_doc) == 0:
            print(f"PDF has no pages: {pdf_path}")
            return None
        
        # Get first page
        page = pdf_doc[0]
        
        # Render to image (300 DPI for good quality)
        mat = fitz.Matrix(2, 2)  # 2x zoom = ~150 DPI
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to numpy array
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        # Convert to BGR for OpenCV (PDF uses RGB)
        if pix.n == 4:  # RGBA
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:  # RGB
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_array
        
        pdf_doc.close()
        
        return extract_signal_from_image_array(img_bgr, pdf_path)
        
    except ImportError:
        # Fallback to pdf2image if PyMuPDF not available
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
            if not images:
                print(f"Could not convert PDF to image: {pdf_path}")
                return None
            
            img_array = np.array(images[0])
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return extract_signal_from_image_array(img_bgr, pdf_path)
        except ImportError:
            print("Neither PyMuPDF nor pdf2image installed.")
            print("Install PyMuPDF: pip install PyMuPDF")
            return None
        except Exception as e:
            print(f"pdf2image Error: {e}")
            return None
    except Exception as e:
        print(f"PDF Error: {e}")
        return None

def extract_signal_from_image(image_path):
    """Extract ECG signals from JPG/PNG images."""
    try:
        if image_path.lower().endswith('.pdf'):
            return extract_signal_from_pdf(image_path)
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"Could not load image: {image_path}")
            return None
        
        return extract_signal_from_image_array(img, image_path)
        
    except Exception as e:
        print(f"Image Error: {e}")
        return None

def extract_signal_from_image_array(img, source_name="image"):
    """
    Extract ECG signal from image array using computer vision.
    Works with standard 12-lead ECG printout format.
    """
    try:
        height, width = img.shape[:2]
        print(f"Processing image: {width}x{height}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect and remove grid (pink/red lines on ECG paper)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Create mask for red/pink grid (ECG paper background)
        lower_red1 = np.array([0, 30, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 30, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        grid_mask = cv2.bitwise_or(mask_red1, mask_red2)
        
        # Also detect light pink
        lower_pink = np.array([0, 10, 200])
        upper_pink = np.array([20, 80, 255])
        pink_mask = cv2.inRange(hsv, lower_pink, upper_pink)
        grid_mask = cv2.bitwise_or(grid_mask, pink_mask)
        
        # Remove grid from grayscale
        gray_no_grid = gray.copy()
        gray_no_grid[grid_mask > 0] = 255
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_enhanced = clahe.apply(gray_no_grid)
        
        # Threshold to get black signal lines
        _, binary = cv2.threshold(gray_enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Clean up noise
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # Check signal density
        # ECG signals are sparse (thin lines). Natural images are dense (blobs).
        density = np.count_nonzero(binary) / binary.size
        print(f"Signal density: {density:.2%}")
        if density > 0.15:
            print("Image is too dense (>15%) to be a valid ECG scan. Likely a photo/natural image.")
            return None
        
        # Try to detect the layout (typically 4 rows x 3 columns for standard 12-lead)
        # Or 3 rows with 4 leads each, or 6 rows with 2 leads each
        
        # Find horizontal divisions by looking at row profiles
        row_profile = np.mean(binary, axis=1)
        
        # Normalize and smooth
        row_profile = gaussian_filter1d(row_profile, sigma=5)
        
        # Find peaks (rows with signal)
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(row_profile, height=np.max(row_profile) * 0.1, distance=height // 6)
        
        if len(peaks) < 3:
            # Fall back to dividing image into 4 equal rows
            num_rows = 4
            row_height = height // num_rows
            row_bounds = [(i * row_height, (i + 1) * row_height) for i in range(num_rows)]
        else:
            # Use detected peaks to define rows
            peaks = sorted(peaks)
            row_bounds = []
            margin = height // 20
            for i, peak in enumerate(peaks[:4]):  # Max 4 rows
                start = max(0, peak - margin)
                end = min(height, peak + margin)
                row_bounds.append((start, end))
        
        # Determine leads per row (usually 3 in standard 12-lead: I, II, III then aVR, aVL, aVF, etc.)
        leads_per_row = 3
        if len(row_bounds) == 3:
            leads_per_row = 4
        elif len(row_bounds) == 6:
            leads_per_row = 2
        elif len(row_bounds) == 12:
            leads_per_row = 1
        
        col_width = width // leads_per_row
        
        # Extract signal from each lead region
        extracted_signals = []
        
        for row_idx, (row_start, row_end) in enumerate(row_bounds):
            for col_idx in range(leads_per_row):
                col_start = col_idx * col_width
                col_end = (col_idx + 1) * col_width
                
                # Extract region
                region = binary[row_start:row_end, col_start:col_end]
                
                if region.size == 0:
                    continue
                
                # Extract signal by finding the centroid of white pixels in each column
                signal = []
                region_height = region.shape[0]
                
                for x in range(region.shape[1]):
                    column = region[:, x]
                    white_pixels = np.where(column > 0)[0]
                    
                    if len(white_pixels) > 0:
                        # Use centroid (weighted average) for smoother signal
                        y_value = np.mean(white_pixels)
                        # Invert y (image y goes down, ECG voltage goes up)
                        y_value = region_height - y_value
                    else:
                        # No signal detected, use baseline (middle)
                        y_value = region_height / 2
                    
                    signal.append(y_value)
                
                if len(signal) > 50:
                    signal = np.array(signal)
                    # Normalize to [-1, 1] range
                    signal = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
                    # Smooth the signal
                    signal = gaussian_filter1d(signal, sigma=2)
                    extracted_signals.append(signal)
        
        if len(extracted_signals) < 12:
            print(f"Only extracted {len(extracted_signals)} leads from image, need 12")
            # Pad with zeros if we have some signals
            if len(extracted_signals) > 0:
                avg_len = int(np.mean([len(s) for s in extracted_signals]))
                while len(extracted_signals) < 12:
                    extracted_signals.append(np.zeros(avg_len))
            else:
                return None
        
        # Take first 12 leads
        extracted_signals = extracted_signals[:12]
        
        # Normalize lengths (use the mode length or resample)
        target_samples = 4096
        normalized_signals = []
        
        for sig in extracted_signals:
            if len(sig) != target_samples:
                # Resample to target length
                indices = np.linspace(0, len(sig) - 1, target_samples)
                resampled = np.interp(indices, np.arange(len(sig)), sig)
                normalized_signals.append(resampled)
            else:
                normalized_signals.append(sig)
        
        # Stack into (4096, 12) array
        result = np.column_stack(normalized_signals)
        
        print(f"Extracted signal shape: {result.shape}")
        return result
        
    except Exception as e:
        print(f"Image extraction error: {e}")
        import traceback
        traceback.print_exc()
        return None

def preprocess_signal(signal, target_len=4096):
    """Pads or truncates signal to target length and 12 leads."""
    if signal is None:
        return None
    
    # Handle shape (N, 12) or (12, N)
    if signal.ndim == 1:
        print(f"Warning: Signal is 1D with shape {signal.shape}")
        return None
    
    if signal.shape[1] != 12:
        if signal.shape[0] == 12:
            signal = signal.T
        else:
            print(f"Warning: Signal has {signal.shape[1]} leads. 12 required.")
            return None 

    current_len = signal.shape[0]
    if current_len < target_len:
        padding = np.zeros((target_len - current_len, 12))
        signal = np.vstack([signal, padding])
    else:
        signal = signal[:target_len, :]
    
    return signal.astype(np.float32)


# ============================================================================
# ECG VALIDATION FUNCTIONS
# ============================================================================

def check_periodicity(signal, sample_rate=400, expected_hr_range=(30, 200)):
    """
    Check if signal has periodic heartbeat patterns using autocorrelation.
    Returns periodicity score (0-1) and estimated heart rate.
    """
    try:
        # Use Lead II (index 1) which typically has best R-wave visibility
        lead = signal[:, 1] if signal.ndim == 2 else signal
        lead = lead - np.mean(lead)
        
        # Compute autocorrelation
        n = len(lead)
        autocorr = np.correlate(lead, lead, mode='full')[n-1:]
        autocorr = autocorr / autocorr[0]  # Normalize
        
        # Expected RR interval range (in samples)
        min_rr = int(60 / expected_hr_range[1] * sample_rate)  # 200 bpm
        max_rr = int(60 / expected_hr_range[0] * sample_rate)  # 30 bpm
        
        # Find peaks in autocorrelation (periodic signals have regular peaks)
        search_region = autocorr[min_rr:min(max_rr, len(autocorr)//2)]
        if len(search_region) == 0:
            return 0.0, 0
        
        peak_idx = np.argmax(search_region) + min_rr
        periodicity_score = autocorr[peak_idx]
        
        # Estimate heart rate
        if peak_idx > 0:
            estimated_hr = 60 * sample_rate / peak_idx
        else:
            estimated_hr = 0
        
        return max(0, periodicity_score), estimated_hr
        
    except Exception:
        return 0.0, 0


def check_einthoven_law(signal):
    """
    Verify Einthoven's law: Lead II ≈ Lead I + Lead III.
    Returns correlation coefficient (0-1). High values indicate valid ECG.
    """
    try:
        if signal.ndim != 2 or signal.shape[1] < 3:
            return 0.0
        
        lead_I = signal[:, 0]
        lead_II = signal[:, 1]
        lead_III = signal[:, 2]
        
        # Einthoven's law: II = I + III
        predicted_II = lead_I + lead_III
        
        # Compute correlation
        correlation, _ = pearsonr(lead_II, predicted_II)
        
        return max(0, correlation)
        
    except Exception:
        return 0.0


def check_signal_statistics(signal):
    """
    Check basic signal statistics to detect noise, flatlines, or non-ECG signals.
    Returns dict with variance, kurtosis, zero-crossing rate, and flatline ratio.
    """
    try:
        results = {
            'variance': 0.0,
            'kurtosis': 0.0,
            'zcr': 0.0,
            'flatline_ratio': 1.0
        }
        
        # Use average across all leads
        if signal.ndim == 2:
            avg_signal = np.mean(signal, axis=1)
        else:
            avg_signal = signal
        
        avg_signal = avg_signal - np.mean(avg_signal)
        
        # Variance
        results['variance'] = np.var(avg_signal)
        
        # Kurtosis (measure of "tailedness")
        results['kurtosis'] = kurtosis(avg_signal)
        
        # Zero-crossing rate
        zero_crossings = np.sum(np.diff(np.signbit(avg_signal).astype(int)) != 0)
        results['zcr'] = zero_crossings / len(avg_signal)
        
        # Flatline ratio (proportion of very small values)
        threshold = np.std(avg_signal) * 0.01
        results['flatline_ratio'] = np.sum(np.abs(avg_signal) < threshold) / len(avg_signal)
        
        return results
        
    except Exception:
        return {'variance': 0.0, 'kurtosis': 0.0, 'zcr': 0.0, 'flatline_ratio': 1.0}


def check_frequency_content(signal, sample_rate=400):
    """
    Check if signal has typical ECG frequency content (0.5-40 Hz).
    Returns ratio of energy in ECG band vs total energy.
    """
    try:
        if signal.ndim == 2:
            lead = signal[:, 1]  # Use Lead II
        else:
            lead = signal
        
        # Compute FFT
        n = len(lead)
        yf = fft(lead)
        xf = fftfreq(n, 1/sample_rate)
        
        # Power spectrum
        power = np.abs(yf[:n//2])**2
        freqs = xf[:n//2]
        
        # Energy in ECG band (0.5-40 Hz)
        ecg_band_mask = (freqs >= 0.5) & (freqs <= 40)
        ecg_energy = np.sum(power[ecg_band_mask])
        total_energy = np.sum(power) + 1e-10
        
        energy_ratio = ecg_energy / total_energy
        
        return energy_ratio
        
    except Exception:
        return 0.0


def check_lead_correlation(signal):
    """
    Check inter-lead correlation. Real ECG leads are correlated but not identical.
    Returns average correlation and check if correlations are in expected range.
    """
    try:
        if signal.ndim != 2 or signal.shape[1] < 12:
            return 0.0, False
        
        correlations = []
        for i in range(12):
            for j in range(i+1, 12):
                corr, _ = pearsonr(signal[:, i], signal[:, j])
                if not np.isnan(corr):
                    correlations.append(abs(corr))
        
        if len(correlations) == 0:
            return 0.0, False
        
        avg_corr = np.mean(correlations)
        
        # Real ECG: leads should have moderate correlation (not too high, not too low)
        # If all leads are identical (correlation=1), it's likely fake
        # If all leads are uncorrelated (correlation=0), it's likely noise
        is_valid = 0.15 < avg_corr < 0.98
        
        return avg_corr, is_valid
        
    except Exception:
        return 0.0, False


def validate_ecg_signal(signal, sample_rate=400, strict=False):
    """
    Comprehensive ECG signal validation.
    
    Args:
        signal: numpy array of shape (samples, 12)
        sample_rate: sampling rate in Hz
        strict: if True, requires all checks to pass; if False, uses weighted scoring
    
    Returns:
        dict with:
            - is_valid: bool indicating if signal appears to be valid ECG
            - confidence: float 0-1 indicating confidence in validation
            - checks: dict with individual check results
            - reasons: list of reasons for rejection (if invalid)
    """
    result = {
        'is_valid': False,
        'confidence': 0.0,
        'checks': {},
        'reasons': []
    }
    
    if signal is None:
        result['reasons'].append("Signal is None")
        return result
    
    if signal.ndim != 2 or signal.shape[1] != 12:
        result['reasons'].append(f"Invalid shape: {signal.shape}. Expected (N, 12)")
        return result
    
    config = ECG_VALIDATION_CONFIG
    weights = {
        'periodicity': 0.25,
        'einthoven': 0.20,
        'statistics': 0.20,
        'frequency': 0.20,
        'correlation': 0.15
    }
    
    score = 0.0
    
    # 1. Periodicity check
    periodicity_score, hr = check_periodicity(signal, sample_rate)
    result['checks']['periodicity'] = {
        'score': periodicity_score,
        'estimated_hr': hr,
        'passed': periodicity_score >= config['min_periodicity_score']
    }
    if periodicity_score >= config['min_periodicity_score']:
        score += weights['periodicity']
    else:
        result['reasons'].append(f"Low periodicity ({periodicity_score:.2f}), no clear heartbeat pattern")
    
    # 2. Einthoven's law check
    einthoven_corr = check_einthoven_law(signal)
    result['checks']['einthoven'] = {
        'correlation': einthoven_corr,
        'passed': einthoven_corr >= config['min_einthoven_correlation']
    }
    if einthoven_corr >= config['min_einthoven_correlation']:
        score += weights['einthoven']
    else:
        result['reasons'].append(f"Einthoven's law violation (corr={einthoven_corr:.2f}), leads are inconsistent")
    
    # 3. Signal statistics check
    stats = check_signal_statistics(signal)
    result['checks']['statistics'] = stats
    
    stats_passed = True
    if stats['variance'] < config['min_variance']:
        result['reasons'].append(f"Signal too flat (variance={stats['variance']:.6f})")
        stats_passed = False
    elif stats['variance'] > config['max_variance']:
        result['reasons'].append(f"Signal too noisy (variance={stats['variance']:.2f})")
        stats_passed = False
    
    if stats['flatline_ratio'] > config['max_flatline_ratio']:
        result['reasons'].append(f"Too many flatline segments ({stats['flatline_ratio']*100:.1f}%)")
        stats_passed = False
    
    if not (config['min_kurtosis'] < stats['kurtosis'] < config['max_kurtosis']):
        result['reasons'].append(f"Abnormal kurtosis ({stats['kurtosis']:.2f})")
        stats_passed = False
    
    if not (config['min_zcr'] < stats['zcr'] < config['max_zcr']):
        result['reasons'].append(f"Abnormal zero-crossing rate ({stats['zcr']:.3f})")
        stats_passed = False
    
    result['checks']['statistics']['passed'] = stats_passed
    if stats_passed:
        score += weights['statistics']
    
    # 4. Frequency content check
    freq_ratio = check_frequency_content(signal, sample_rate)
    result['checks']['frequency'] = {
        'ecg_band_ratio': freq_ratio,
        'passed': freq_ratio >= config['ecg_freq_energy_ratio']
    }
    if freq_ratio >= config['ecg_freq_energy_ratio']:
        score += weights['frequency']
    else:
        result['reasons'].append(f"Low ECG frequency content ({freq_ratio*100:.1f}%)")
    
    # 5. Lead correlation check
    avg_corr, corr_valid = check_lead_correlation(signal)
    result['checks']['correlation'] = {
        'average_correlation': avg_corr,
        'passed': corr_valid
    }
    if corr_valid:
        score += weights['correlation']
    else:
        if avg_corr > 0.98:
            result['reasons'].append(f"Leads too similar (corr={avg_corr:.2f}), possibly synthetic")
        elif avg_corr < 0.15:
            result['reasons'].append(f"Leads uncorrelated (corr={avg_corr:.2f}), possibly noise")
    
    # Count essential ECG-specific checks that passed
    # These are checks that specifically verify ECG characteristics
    essential_checks_passed = sum([
        result['checks']['periodicity']['passed'],  # Has heartbeat pattern
        result['checks']['einthoven']['passed'],    # Lead relationships valid
        corr_valid                                   # Inter-lead correlation reasonable
    ])
    
    # Final decision
    result['confidence'] = score
    result['essential_checks_passed'] = essential_checks_passed
    
    if strict:
        result['is_valid'] = len(result['reasons']) == 0
    else:
        # Require at least 2 of 3 essential checks AND score >= 0.4
        # This prevents random noise from passing
        result['is_valid'] = essential_checks_passed >= 2 and score >= 0.4
    
    return result


def validate_and_report(signal, source="unknown"):
    """
    Validate ECG signal and print a human-readable report.
    Returns (is_valid, confidence, reasons).
    """
    validation = validate_ecg_signal(signal)
    
    print(f"\n{'='*50}")
    print(f"ECG VALIDATION REPORT: {source}")
    print(f"{'='*50}")
    
    if validation['is_valid']:
        print(f"✓ VALID ECG (confidence: {validation['confidence']*100:.1f}%)")
    else:
        print(f"✗ INVALID/SUSPICIOUS (confidence: {validation['confidence']*100:.1f}%)")
    
    print(f"\nCheck Results:")
    for check_name, check_result in validation['checks'].items():
        passed = check_result.get('passed', False)
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}: {check_result}")
    
    if validation['reasons']:
        print(f"\nReasons for concern:")
        for reason in validation['reasons']:
            print(f"  - {reason}")
    
    print(f"{'='*50}\n")
    
    return validation['is_valid'], validation['confidence'], validation['reasons']


def universal_loader(file_path):
    """Universal ECG file loader supporting multiple formats."""
    ext = os.path.splitext(file_path)[1].lower()
    signal = None
    
    print(f"Loading {file_path} (format: {ext})")
    
    # Content-based detection
    try:
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'rb') as f:
            header = f.read(1024)  # Read first 1KB
            
        # Detect PDF
        if header.startswith(b'%PDF'):
            print(f"Detected PDF content for {file_path}")
            signal = extract_signal_from_pdf(file_path)
            
        # Detect Images (JPEG, PNG, BMP)
        elif header.startswith(b'\xFF\xD8') or header.startswith(b'\x89PNG') or header[:2] == b'BM':
            print(f"Detected Image content for {file_path}")
            signal = extract_signal_from_image(file_path)
            
        # Detect HDF5/MAT
        elif header.startswith(b'\x89HDF') or b'MATLAB' in header[:20]:
            print(f"Detected MAT/HDF5 content for {file_path}")
            signal = load_mat_signal(file_path)
            
        # Detect XML (check for tags)
        elif b'<?xml' in header[:100] or b'<RestingECG' in header or b'<AnnotatedECG' in header or b'<SierraECG' in header or b'<FDXML' in header:
            print(f"Detected XML content for {file_path}")
            signal = load_xml_signal(file_path)
            
        # Fallback to extension if content detection failed but extension is known
        elif ext == '.mat':
            signal = load_mat_signal(file_path)
        elif ext == '.csv':
            signal = load_csv_signal(file_path)
        elif ext in ['.dat', '.hea']:
            try:
                record_name = os.path.splitext(file_path)[0]
                record = wfdb.rdrecord(record_name)
                signal = record.p_signal
            except:
                signal = None
                
        # Try processing as generic text/CSV if nothing else matched
        else:
            try:
                # Check if it looks like character-separated numbers
                text_start = header.decode('utf-8', errors='ignore')
                if ',' in text_start or '\t' in text_start:
                    print(f"Attempting to read as generic CSV/Text: {file_path}")
                    signal = load_csv_signal(file_path)
                else:
                    print(f"Could not determine format for {file_path}")
            except:
                 pass
                 
    except Exception as e:
        print(f"Detection Error: {e}")

    
    return preprocess_signal(signal)


def universal_loader_with_validation(file_path, validate=True, strict=False, verbose=True):
    """
    Load ECG file and validate that it contains real ECG signals.
    
    Args:
        file_path: path to ECG file
        validate: if True, perform ECG validation
        strict: if True, require all validation checks to pass
        verbose: if True, print validation report
    
    Returns:
        tuple: (signal, validation_result)
        - signal: numpy array (4096, 12) or None if invalid
        - validation_result: dict with validation details
    """
    signal = universal_loader(file_path)
    
    if signal is None:
        return None, {'is_valid': False, 'confidence': 0.0, 'reasons': ['Failed to load signal']}
    
    if not validate:
        return signal, {'is_valid': True, 'confidence': 1.0, 'reasons': []}
    
    # Perform signal-based validation
    validation = validate_ecg_signal(signal, strict=strict)
    
    # Perform AI Image Analysis (Optional but recommended)
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.pdf', '']:
            import ai_validator
            is_doc, reason = ai_validator.is_likely_document(file_path)
            validation['checks']['ai_check'] = {'passed': is_doc, 'reason': reason}
            
            if not is_doc:
                validation['confidence'] = 0.0
                validation['is_valid'] = False
                validation['reasons'].append(f"AI Rejection: {reason}")
    except Exception as e:
        print(f"AI Check skipped: {e}")
    
    if verbose:
        validate_and_report(signal, source=os.path.basename(file_path))
    
    if not validation['is_valid']:
        print(f"⚠ WARNING: {file_path} does not appear to contain valid ECG signals!")
        return None, validation
    
    return signal, validation

