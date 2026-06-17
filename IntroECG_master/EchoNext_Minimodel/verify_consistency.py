import os
import sys
import json
import torch
import numpy as np
from flask_app.model_inference import predict, parse_xml_file

# Fix path
sys.path.append(os.path.join(os.getcwd(), 'flask_app'))

def check_consistency():
    filename = os.path.join("xml_input", "MUSE_example.xml")
    checkpoint_path = os.path.abspath(os.path.join('models', 'echonext_multilabel_minimodel', 'weights.pt'))
    norm_path = os.path.abspath(os.path.join('models', 'echonext_multilabel_minimodel', 'waveform_normalization_params.json'))

    with open("consistency_log.txt", "w") as log:
        def log_print(s):
            print(s)
            log.write(s + "\n")

        log_print(f"--- Checking {filename} ---")
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            log_print(f"File Size: {size} bytes")
        else:
            log_print("File not found.")
            return

        log_print(f"--- Checking Normalization Params ---")
        if os.path.exists(norm_path):
            log_print(f"Found params at {norm_path}")
            with open(norm_path, 'r') as f:
                data = json.load(f)
                log_print(f"Mean (first 5): {data['mean'][:5]}")
        else:
            log_print(f"Normalization params NOT found at {norm_path}")

        log_print(f"--- Running Prediction ---")
        try:
            results = predict(filename, checkpoint_path)
            log_print("Results:")
            for k, v in results.items():
                log_print(f"{k}: {v*100:.2f}%")
        except Exception as e:
            log_print(f"Prediction failed: {e}")
            import traceback
            traceback.print_exc(file=log)

if __name__ == "__main__":
    check_consistency()
