import os
from model_inference import predict

BASE_DIR = os.path.dirname(__file__)

CHECKPOINT_PATH = os.path.join(
    BASE_DIR,
    "models",
    "echonext_multilabel_minimodel",
    "weights.pt"
)

def run_echonext(filepath):
    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError("EchoNext weights not found")

    preds = predict(filepath, CHECKPOINT_PATH)
    return preds
