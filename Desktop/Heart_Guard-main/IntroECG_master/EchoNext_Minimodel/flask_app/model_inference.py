#E:\heartgaurd (2)\heartgaurd\heartgaurd\IntroECG_master\EchoNext_Minimodel\flask_app\model_inference.py
import sys
import os
import base64
import struct
import xmltodict
import numpy as np
import pandas as pd
import torch
import asyncio
from pathlib import Path
from tempfile import mkstemp
from xml.dom.minidom import parse
from scipy.interpolate import interp1d
import json
from PIL import Image

# Extracted from ai_model11 (1).ipynb

# Add potential parent directories to sys.path to resolve cradlenet
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

try:
    from cradlenet.lightning.modules.resnet1d_with_tabular import Resnet1dWithTabularModule
except ImportError:
    # If running from flask_app directory directly without parent in path
    sys.path.append(str(Path.cwd().parent))
    try:
        from cradlenet.lightning.modules.resnet1d_with_tabular import Resnet1dWithTabularModule
    except ImportError:
        print("Warning: Could not import cradlenet. Ensure it is in the Python path.")

# Constants as defined in predict_file.py
LABELS = [
    "LVEF <= 45%",
    "LVWT >= 1.3cm",
    "Moderate or Greater Aortic Stenosis",
    "Moderate or Greater Aortic Regurgitation",
    "Moderate or Greater Mitral Regurgitation",
    "Moderate or Greater Tricuspid Regurgitation",
    "Moderate or Greater Pulmonary Regurgitation",
    "Moderate or Greater RV Systolic Dysfunction",
    "Moderate or Greater Pericardial Effusion",
    "PASP >= 45mmHg",
    "TR Max V >= 3.2m/s",
    "Moderate or Greater Structural Heart Disease"
]

def decode_ekg_muse_to_array(raw_wave, downsample=1):
    try:
        dwnsmpl = int(1 // downsample)
    except ZeroDivisionError:
        dwnsmpl = 1

    # covert the waveform from base64 to byte array
    arr = base64.b64decode(bytes(raw_wave, 'utf-8'))
    # unpack every 2 bytes, little endian (16 bit encoding)
    # unpack every 2 bytes, little endian (16 bit encoding)
    # Use explicit little endian '<' to ensure consistency across platforms
    count = int(len(arr) / 2)
    unpack_format = f'<{count}h'
    byte_array = struct.unpack(unpack_format, arr)
    return np.array(byte_array)[::dwnsmpl]

def parse_xml_file(path_to_xml):
    with open(path_to_xml, 'rb') as fd:
        dic = xmltodict.parse(fd.read().decode('utf8'))
    lead_order = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
    lead_data = dict.fromkeys(lead_order)
    # Handle different XML structures if generic or specific
    waveforms = dic.get('RestingECG', {}).get('Waveform', [])
    if not isinstance(waveforms, list):
        waveforms = [waveforms]
    for lead in waveforms:
        if 'LeadData' not in lead:
            continue

        lead_datas = lead['LeadData']
        if not isinstance(lead_datas, list):
            lead_datas = [lead_datas]

        for single_lead in lead_datas:
            lead_id = single_lead.get('LeadID')
            wave_data = single_lead.get('WaveFormData')

            if not lead_id or not wave_data:
                continue
            # Decode to array to check length
            decoded = decode_ekg_muse_to_array(wave_data)
            sample_length = len(decoded)
            if sample_length == 5000:
                lead_data[lead_id] = decode_ekg_muse_to_array(wave_data, downsample=0.5)
            elif sample_length == 2500:
                lead_data[lead_id] = decode_ekg_muse_to_array(wave_data, downsample=1)
    # Calculate missing leads if possible
    if lead_data.get('I') is not None and lead_data.get('II') is not None:
        if lead_data.get('III') is None:
            lead_data['III'] = np.array(lead_data["II"]) - np.array(lead_data["I"])
        if lead_data.get('aVR') is None:
            lead_data['aVR'] = -(np.array(lead_data["I"]) + np.array(lead_data["II"])) / 2
        if lead_data.get('aVF') is None:
            lead_data['aVF'] = (np.array(lead_data["II"]) + np.array(lead_data["III"])) / 2
        if lead_data.get('aVL') is None:
            lead_data['aVL'] = (np.array(lead_data["I"]) - np.array(lead_data["III"])) / 2
    # Ensure all leads are present
    temp = []
    for key in lead_order:
        if lead_data[key] is None:
            raise ValueError(f"Missing lead data for {key}")
        temp.append(lead_data[key])

    ekg_array = np.array(temp).T
    return ekg_array

# PDF Parsing Helpers
def resample_core(signalx, signaly, sqlen, minspacing):
    f = interp1d(signalx, signaly, fill_value="extrapolate")
    xx = np.linspace(signalx[0], signalx[-1], sqlen)
    newy = f(xx)
    return newy

async def convert_pdf_to_svg(fname, outname) -> int:
    cmd = f'pdftocairo -svg "{fname}" "{outname}"'
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        if stderr:
             print(f'Error in converting {fname} to SVG:\n{stderr.decode()}')
    return proc.returncode

def process_svg_to_pd_perdata(svgfile):
    columnnames = np.array(['I', 'II','III','aVR','aVL','aVF','V1','V2','V3','V4', \
                     'V5', 'V6', 'V1L','IIL','V5L'])
    doc = parse(svgfile)
    data = pd.DataFrame(columns=['lead', 'x', 'y'])

    scale_vals = []

    siglen = []
    for path in doc.getElementsByTagName('path'):
        tmp = path.getAttribute('d')
        tmp_split = tmp.split(' ')
        try:
            signal_np = np.asarray([float(x) for x in tmp_split if (x != 'M' and x != 'L' and x != 'C' and x != 'Z' and x != '')])
            if len(signal_np) == 0: continue
            signalx = signal_np[0::2]
            siglen.append(len(signalx))
        except ValueError:
            continue

    siglen = np.array(siglen)
    if len(siglen) == 0: return None

    cali6sigs = np.where(siglen == 6)[0]
    if len(cali6sigs) == 0: return None

    minposcali = np.min(cali6sigs)
    tmpstart = list(range(minposcali, len(siglen)))
    last15sigs = np.array(list(set(tmpstart)- set(cali6sigs)))

    a = 0
    for ind, path in enumerate(doc.getElementsByTagName('path')):
        if ind in last15sigs:
            if a > 14: continue
            tmp = path.getAttribute('d')
            tmp_split = tmp.split(' ')
            signal_np = np.asarray([float(x) for x in tmp_split if (x != 'M' and x != 'L' and x != 'C' and x != 'Z' and x != '')])
            signalx = signal_np[0::2]
            signaly = signal_np[1::2]

            data.loc[data.shape[0]] = [columnnames[a], signalx, signaly]
            a += 1
        elif ind in cali6sigs:
            tmp = path.getAttribute('d')
            tmp_split = tmp.split(' ')
            signal_np = np.asarray([float(x) for x in tmp_split if (x != 'M' and x != 'L' and x != 'C' and x != 'Z' and x != '')])
            signaly = signal_np[1::2]
            scale_vals.append([np.min(signaly), np.max(signaly)])
    if data.empty or len(scale_vals) == 0: return None
    sx = [x[0] for x in scale_vals]
    sy = [x[1] for x in scale_vals]

    if data.shape[0] >= 12:
         scale_x_list = [sx[0]] * data.shape[0]
         scale_y_list = [sy[0]] * data.shape[0]
         if len(sx) >= 4:
             scale_x_list = [sx[0]]*3 + [sx[1]]*3 + [sx[2]]*3 + [sx[3]]*3
             scale_y_list = [sy[0]]*3 + [sy[1]]*3 + [sy[2]]*3 + [sy[3]]*3

         if data.shape[0] == 15 and len(sx) >= 5:
             scale_x_list += [sx[4]]*3
             scale_y_list += [sy[4]]*3

         data['scale_x'] = scale_x_list[:data.shape[0]]
         data['scale_y'] = scale_y_list[:data.shape[0]]

    return data

def process_resample_data(data):
    target_len = 2500
    lead_order = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
    ekg_array = np.zeros((target_len, 12))

    for i, lead_name in enumerate(lead_order):
        lead_data = data.loc[data.lead == lead_name]
        if lead_data.empty:
            continue

        signalx = lead_data.x.values[0]
        signaly = lead_data.y.values[0] - lead_data.scale_x.values[0]
        calibration_y = (lead_data.scale_y.values[0] - lead_data.scale_x.values[0]) / 1000
        if calibration_y == 0: calibration_y = 1

        signaly = signaly / calibration_y
        newy = resample_core(signalx, signaly, target_len, 0)
        ekg_array[:, i] = newy

    return ekg_array

async def parse_pdf_file_async(pdf_path):
    if not os.path.exists('svgs_temp'):
        os.makedirs('svgs_temp')

    fp, svgfile = mkstemp(suffix='.svg', dir='svgs_temp')
    os.close(fp)

    try:
        ret = await convert_pdf_to_svg(pdf_path, svgfile)
        if ret != 0:
            raise RuntimeError("pdftocairo failed")

        data = process_svg_to_pd_perdata(svgfile)
        if data is None:
            raise ValueError("Failed to extract data from SVG")

        ekg_array = process_resample_data(data)
        return ekg_array
    finally:
        if os.path.exists(svgfile):
            os.remove(svgfile)

def parse_pdf_file(pdf_path):
    # Sync wrapper
    try:
        if sys.version_info >= (3, 7):
            return asyncio.run(parse_pdf_file_async(pdf_path))
        else:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(parse_pdf_file_async(pdf_path))
    except Exception as e:
        print(f"PDF Parsing Exception: {e}")
        return None

def parse_image_file(image_path):
    print(f"Opening image: {image_path}")
    img = Image.open(image_path).convert('L') # Grayscale
    img_data = np.array(img)
    
    h, w = img_data.shape
    section_h = h // 12
    ekg_array = np.zeros((2500, 12))
    
    for i in range(12):
        start_y = i * section_h
        end_y = (i+1) * section_h
        section = img_data[start_y:end_y, :]
        
        # Invert and threshold to find signal
        inverted = 255 - section
        threshold = np.max(inverted) * 0.4
        binary = (inverted > threshold).astype(float)
        
        coords = np.indices(binary.shape)
        y_coords = coords[0]
        
        weights = binary.sum(axis=0)
        weights[weights == 0] = 1
        
        y_centers = (binary * y_coords).sum(axis=0) / weights
        
        # CENTERING: Subtract baseline (median)
        baseline = np.median(y_centers)
        y_centered = baseline - y_centers # baseline - y ensures positive peaks go UP
        
        # SCALING: Normalize to MUSE-like units (approx 1000 units per mV)
        # We assume the section height corresponds to approx 3-4mV total range
        scale_factor = (3000.0 / section_h)
        y_scaled = y_centered * scale_factor
        
        x_orig = np.linspace(0, 1, w)
        x_new = np.linspace(0, 1, 2500)
        f = interp1d(x_orig, y_scaled, fill_value="extrapolate")
        ekg_array[:, i] = f(x_new)
        
    return ekg_array

def load_model(checkpoint_path, model_kwargs, binary=True):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading model from {checkpoint_path}...")

    try:
        module = Resnet1dWithTabularModule.load_from_checkpoint(
            checkpoint_path,
            map_location=device
        )
        module.to(device)
        module.eval()
        return module, device
    except Exception as e:
        print(f"Lightning checkpoint load failed ({e}), trying legacy/state_dict load...")

    try:
        module = Resnet1dWithTabularModule(model_kwargs=model_kwargs, lr=0, binary=binary)
        weights = torch.load(checkpoint_path, map_location=device)

        if isinstance(weights, dict) and "model" in weights:
            module.model.load_state_dict(weights["model"])
        else:
            module.model.load_state_dict(weights)

        module.to(device)
        module.eval()
        return module, device
    except Exception as e:
        print(f"Failed to load checkpoint: {e}")
        raise e

def predict(input_path, checkpoint_path, model_type="echonext", filter_size=16, len_tabular=7, num_classes=12):
    ekg_data = None
    input_path = Path(input_path)
    suffix = input_path.suffix.lower()

    if suffix == '.xml':
        ekg_data = parse_xml_file(str(input_path))
    elif suffix == '.pdf':
        ekg_data = parse_pdf_file(str(input_path))
    elif suffix in ['.jpg', '.jpeg', '.png']:
        ekg_data = parse_image_file(str(input_path))
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")

    if ekg_data is None:
        raise ValueError("Failed to parse file or no data extracted.")

    # Load Normalization Params
    norm_path = Path(checkpoint_path).parent / "waveform_normalization_params.json"
    if norm_path.exists():
        with open(norm_path, "r") as f:
            norm_params = json.load(f)

        mean = np.array(norm_params["mean"])
        std = np.array(norm_params["std"])
        lower = np.array(norm_params["lowerbound"])
        upper = np.array(norm_params["upperbound"])

        # Data is (2500, 12)
        for i in range(12):
             ekg_data[:, i] = np.clip(ekg_data[:, i], lower[i], upper[i])
        ekg_data = (ekg_data - mean[None, :]) / std[None, :]
        
        # DEBUG: Print stats of normalized data
        print(f"DEBUG: Normalized Data Mean: {np.mean(ekg_data):.4f}, Std: {np.std(ekg_data):.4f}")
        print(f"DEBUG: First 5 values (Lead I): {ekg_data[:5, 0]}")
    else:
        print("WARNING: Normalization params not found! Predictions may be inaccurate.")

    ekg_tensor = torch.tensor(ekg_data, dtype=torch.float32)

    if ekg_tensor.shape == (2500, 12):
        ekg_tensor = ekg_tensor.unsqueeze(0).unsqueeze(0) # (1, 1, 2500, 12)
    elif ekg_tensor.shape == (12, 2500):
         ekg_tensor = ekg_tensor.transpose(0, 1).unsqueeze(0).unsqueeze(0)
    else:
        ekg_tensor = ekg_tensor.view(1, 1, 2500, 12)

    tabular_tensor = torch.zeros((1, len_tabular), dtype=torch.float32)
    model_kwargs = {
        "len_tabular_feature_vector": len_tabular,
        "filter_size": filter_size,
        "num_classes": num_classes,
    }
    
    module, device = load_model(checkpoint_path, model_kwargs)
    ekg_tensor = ekg_tensor.to(device)
    tabular_tensor = tabular_tensor.to(device)

    with torch.no_grad():
        output = module((ekg_tensor, tabular_tensor))
        probabilities = torch.sigmoid(output).cpu().numpy()[0]
        
    results = {}
    for i, label in enumerate(LABELS):
        if i < len(probabilities):
            results[label] = float(probabilities[i])
            
    return results
