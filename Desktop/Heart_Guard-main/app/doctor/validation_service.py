#E:\heartgaurd (5)\heartgaurd (2)\heartgaurd\heartgaurd\app\doctor\validation_service.py
import os
import numpy as np
from automatic_ecg_diagnosis_master.universal_processor import universal_loader_with_validation
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam

MODEL_PATH = os.path.join("model", "model.hdf5")
_prediction_model = None

def get_prediction_model():
    global _prediction_model
    if _prediction_model is None:
        if not os.path.exists(MODEL_PATH):
            print(f"Model not found at {MODEL_PATH}")
            return None
        _prediction_model = load_model(MODEL_PATH, compile=False)
        _prediction_model.compile(loss='binary_crossentropy', optimizer=Adam())
    return _prediction_model


def validate_and_predict(file_path):
    """
    1) Validate ECG
    2) If valid → predict using second model
    """
    signal, validation = universal_loader_with_validation(
        file_path,
        validate=True,
        strict=False,
        verbose=False
    )

    # Helper to convert numpy types
    def make_serializable(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return None if np.isnan(obj) or np.isinf(obj) else float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(i) for i in obj]
        else:
            return obj

    # Use .get() to avoid KeyError
    response = {
        "is_valid": bool(validation.get("is_valid", False)),
        "confidence": float(validation.get("confidence", 0.0)) if not np.isnan(validation.get("confidence", 0.0)) else 0.0,
        "reasons": validation.get("reasons", []),
        "checks": make_serializable(validation.get("checks", [])),
        "essential_checks_passed": int(validation.get("essential_checks_passed", 0)),
        "prediction": None,
        "top_diagnosis": None,
        "top_confidence": None,
        "signal": None
    }

    if not response["is_valid"] or signal is None:
        return response

    # ---------- Prediction ----------
    model = get_prediction_model()
    if model is None:
        return response

    x = np.expand_dims(signal, axis=0)  # (1, 4096, 12)
    y = model.predict(x, verbose=0)[0]

#   labels = ['1st degree AV block', 'Right bundle branch block', 'Left bundle branch block', 
 #             'Sinus bradycardia', 'Atrial fibrillation', 'Sinus tachycardia']
    labels = ['1dAVb', 'RBBB', 'LBBB', 'SB', 'AF', 'ST']
    preds = dict(zip(labels, y.tolist()))
    preds = make_serializable(preds)

    top_label = max(preds, key=preds.get)
    response["prediction"] = preds
    response["top_diagnosis"] = top_label
    response["top_confidence"] = preds[top_label]
    response["signal"] = signal.tolist()  # optional

    return response
