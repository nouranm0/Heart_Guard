import numpy as np
import os

# Lazy load tensorflow to avoid startup overhead
tf = None
model = None

def init_model():
    global tf, model
    if model is None:
        import tensorflow as tf
        from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2
        model = MobileNetV2(weights='imagenet')

def is_likely_document(image_path):
    """
    Uses MobileNetV2 (Generic or Custom) to check if the image looks like a document/ECG.
    """
    try:
        init_model()
        from tensorflow.keras.preprocessing import image
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions
        from tensorflow.keras.models import load_model
        
        # Check for custom trained validator
        custom_model_path = os.path.join('model', 'custom_validator.h5')
        if os.path.exists(custom_model_path):
            print(f"Using Custom Validator Model: {custom_model_path}")
            # Load custom model (lazy load could be better but for now load here)
            # Note: Ideally cache this globally like 'model'
            global custom_model
            if 'custom_model' not in globals() or custom_model is None:
                custom_model = load_model(custom_model_path)
                
            img = image.load_img(image_path, target_size=(224, 224))
            x = image.img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x = x / 255.0 # Custom model uses rescale=1./255
            
            score = custom_model.predict(x, verbose=0)[0][0]
            print(f"Custom Model Score: {score:.4f}")
            
            if score > 0.5:
                return True, f"Custom AI Approved ({score:.1%})"
            else:
                return False, f"Custom AI Rejected ({score:.1%})"

        # Fallback to Generic MobileNetV2
        img = image.load_img(image_path, target_size=(224, 224))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        
        preds = model.predict(x, verbose=0)
        decoded = decode_predictions(preds, top=5)[0]
        
        # Labels that suggest a document, chart, screen, or grid pattern
        DOCUMENT_LABELS = [
            'web_site', 'crossword_puzzle', 'jigsaw_puzzle', 'envelope', 
            'menu', 'packet', 'carton', 'rule', 'scale', 'oscilloscope', 
            'digital_clock', 'analog_clock', 'scoreboard', 'binder',
            'notebook', 'paper_towel', 'toilet_tissue', 'window_screen',
            'comic_book', 'book_jacket'
        ]
        
        top_labels = [label for (_, label, _) in decoded]
        top_probs = [prob for (_, _, prob) in decoded]
        
        print(f"AI Classification: {list(zip(top_labels, top_probs))}")
        
        # Check if any top prediction is in our 'document' list
        for label, prob in zip(top_labels, top_probs):
            if label in DOCUMENT_LABELS:
                return True, f"Detected {label} pattern"
                
        # If the top confidence is very high (>50%) for something NOT in the list (e.g. 'tabby'), reject
        if top_probs[0] > 0.4:
            return False, f"Detected {top_labels[0]} (not ECG-like)"
            
        # Ambiguous case - let it pass to heuristic validation
        return True, "Ambiguous AI classification"
        
    except Exception as e:
        print(f"AI Validator Error: {e}")
        return True, "AI check failed" # Fail safely
