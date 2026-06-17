import os
import scipy.io

files = [f for f in os.listdir('.') if f.endswith('.mat')]
for f in files:
    try:
        data = scipy.io.loadmat(f)
        if 'feats' in data:
            print(f"{f}: {data['feats'].shape}")
        else:
            print(f"{f}: 'feats' not found. Keys: {list(data.keys())}")
    except Exception as e:
        print(f"{f}: Error {e}")
