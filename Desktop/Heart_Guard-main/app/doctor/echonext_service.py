#E:\heartgaurd (5)\heartgaurd (2)\heartgaurd\heartgaurd/app/doctor/echonext_service.py
import os
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
from IntroECG_master.EchoNext_Minimodel.flask_app.model_inference import predict
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

CHECKPOINT_PATH = os.path.join("model", "weights.pt")


def is_ecg_image(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()

    if ext in ['pdf', 'xml']:
        return True

    # لو صورة
    image = Image.open(filepath).convert("RGB")
    inputs = clip_processor(
        text=["ECG medical waveform", "non medical image"],
        images=image,
        return_tensors="pt",
        padding=True
    )
    outputs = clip_model(**inputs)
    probs = outputs.logits_per_image.softmax(dim=1)
    return probs[0][0].item() > 0.7


def echonext_predict(filepath):
    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(f"EchoNext model not found at {CHECKPOINT_PATH}")

    # 1️⃣ تحقق من صلاحية الملف
    if not is_ecg_image(filepath):
        return {"is_ecg": False, "prediction": None}

    # 2️⃣ استدعاء الموديل القديم بنفس طريقة preprocessing
    try:
        print(f"[DEBUG] Predicting file: {filepath}")
        preds = predict(filepath, CHECKPOINT_PATH)  # نفس المشروع القديم
        print("EchoNext preds:", preds)
        print("Unique values:", set(preds.values()))

        print(f"[DEBUG] Raw predictions: {preds}")

        # 3️⃣ التحقق من أن النواتج مختلفة لكل ملف
        if not preds:
            print("[WARNING] Predictions are empty!")

        return {"is_ecg": True, "prediction": preds}

    except Exception as e:
        print(f"[ERROR] echonext_predict failed for {filepath}: {e}")
        return {"is_ecg": True, "prediction": None}
    
    
