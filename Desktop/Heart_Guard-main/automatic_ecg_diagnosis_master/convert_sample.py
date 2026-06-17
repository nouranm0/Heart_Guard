import scipy.io
import h5py
import numpy as np
import os

import argparse

def convert_mat_to_hdf5(mat_path, hdf5_path):
    print(f"Loading {mat_path}...")
    try:
        data = scipy.io.loadmat(mat_path)
    except Exception as e:
        print(f"Error loading {mat_path}: {e}")
        return False
    
    if 'feats' not in data:
        print(f"Error: 'feats' key not found in {mat_path}. Keys present: {list(data.keys())}")
        return False

    feats = data['feats']
    signal = feats.T
    signal = np.expand_dims(signal, axis=0)
    
    print(f"Signal shape: {signal.shape}")
    
    with h5py.File(hdf5_path, 'w') as f:
        f.create_dataset('tracings', data=signal, dtype='float32')
        
    print(f"Saved to {hdf5_path}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert CODE-15% .mat to HDF5')
    parser.add_argument('input', help='Input .mat file')
    parser.add_argument('--output', default='sample.hdf5', help='Output .hdf5 file')
    args = parser.parse_args()
    
    convert_mat_to_hdf5(args.input, args.output)
