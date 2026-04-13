import os
import scipy.io
import h5py
import numpy as np
import pandas as pd
import argparse
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam

from universal_processor import universal_loader

def batch_process(input_path, model_path, output_csv):
    # Supported extensions
    extensions = ['.mat', '.csv', '.xml', '.dat', '.hea', '.jpg', '.jpeg', '.png', '.pdf']
    
    # 1. Determine if input is a file or a directory
    if os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        if ext in extensions:
            mat_files = [os.path.basename(input_path)]
            input_dir = os.path.dirname(input_path) or '.'
        else:
            print(f"Error: {input_path} format not supported.")
            return
    elif os.path.isdir(input_path):
        input_dir = input_path
        mat_files = [f for f in os.listdir(input_path) if os.path.splitext(f)[1].lower() in extensions]
    else:
        print(f"Error: {input_path} not found.")
        return

    if not mat_files:
        print("No supported ECG files found.")
        return

    print(f"Found {len(mat_files)} files. Processing...")

    signals = []
    processed_filenames = []

    for filename in mat_files:
        path = os.path.join(input_dir, filename)
        signal = universal_loader(path)
        if signal is not None:
            signals.append(signal)
            processed_filenames.append(filename)
        else:
            print(f"Skipping {filename}: Could not load or extract signal.")

    if not signals:
        print("No valid signals loaded.")
        return

    # 2. Stack into (N, 4096, 12)
    x = np.array(signals)
    print(f"Input tensor shape: {x.shape}")

    # 3. Load Model and Predict
    print(f"Loading model from {model_path}...")
    model = load_model(model_path, compile=False)
    model.compile(loss='binary_crossentropy', optimizer=Adam())
    
    print("Running predictions...")
    y_score = model.predict(x, verbose=1)

    # 4. Generate CSV
    labels = ['1dAVb', 'RBBB', 'LBBB', 'SB', 'AF', 'ST']
    results_df = pd.DataFrame(y_score, columns=labels)
    results_df.insert(0, 'filename', processed_filenames)

    # Help print results
    def print_results(df):
        print("\n" + "="*50)
        print("PREDICTION RESULTS DETAIL")
        print("="*50)
        
        labels = ['1dAVb', 'RBBB', 'LBBB', 'SB', 'AF', 'ST']
        for _, row in df.iterrows():
            print(f"\nResults for {row['filename']}:")
            scores = [row[l] for l in labels]
            for label in labels:
                print(f"{label}: {row[label]:.4f}")
            
            # Find the max
            max_idx = np.argmax(scores)
            max_label = labels[max_idx]
            max_val = scores[max_idx]
            
            print(f"--> Top Prediction: {max_label} ({max_val:.4f})")
        print("\n" + "="*50)

    try:
        results_df.to_csv(output_csv, index=False)
        print(f"Done! Results saved to {output_csv}")
        print_results(results_df)
        
    except PermissionError:
        print(f"Error: Could not save to {output_csv}. Please make sure the file is not open in Excel or another program.")
        print_results(results_df)
    except Exception as e:
        print(f"Error saving CSV: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Batch process ECG MAT files')
    parser.add_argument('--input', default='.', help='Directory or single .mat file to process')
    parser.add_argument('--model', default='model/model.hdf5', help='Path to the model file')
    parser.add_argument('--output', default='batch_results.csv', help='Output CSV file')
    
    args = parser.parse_args()
    batch_process(args.input, args.model, args.output)
