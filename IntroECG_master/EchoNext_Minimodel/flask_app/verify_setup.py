import sys
import os
import torch
import numpy as np

# Add parent dir for cradlenet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def verify():
    print("Verifying setup...")
    try:
        import flask
        import pandas
        import scipy
        import PIL
        import xmltodict
        import pytorch_lightning
        print("Standard dependencies: OK")
    except ImportError as e:
        print(f"Missing dependency: {e}")
        return

    try:
        from cradlenet.lightning.modules.resnet1d_with_tabular import Resnet1dWithTabularModule
        print("Cradlenet import: OK")
    except ImportError as e:
        print(f"Cradlenet import failed: {e}")
        # path debugging
        print(f"sys.path: {sys.path}")
        return

    checkpoint_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'echonext_multilabel_minimodel', 'weights.pt'))
    if not os.path.exists(checkpoint_path):
        print(f"Checkpoint not found at: {checkpoint_path}")
    else:
        print(f"Checkpoint found at: {checkpoint_path}")
        # Try loading
        try:
             # Just a structural check, deep loading might take time/gpu
             weights = torch.load(checkpoint_path, map_location='cpu')
             print("Checkpoint loadable: OK")
        except Exception as e:
             print(f"Checkpoint load error: {e}")

    print("Verification complete.")

if __name__ == "__main__":
    verify()
