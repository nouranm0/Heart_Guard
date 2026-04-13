#E:\heartgaurd (2)\heartgaurd\heartgaurd\IntroECG_master\EchoNext_Minimodel\flask_app\app.py
import os
import secrets
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from model_inference import predict
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

# تحميل موديل CLIP
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configuration 
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xml', 'pdf', 'png', 'jpg', 'jpeg'}
CHECKPOINT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'echonext_multilabel_minimodel', 'weights.pt'))

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CHECKPOINT_PATH'] = CHECKPOINT_PATH

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_ecg(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    
    if ext in ['pdf', 'xml']:
        # PDF/XML ممكن نقولهم صالحة مباشرة مع تحذير
        flash("تم رفع ملف PDF/XML، سيتم تحليله فقط إذا كان يحتوي على بيانات ECG صالحة")
        return True

    # لو صورة
    try:
        image = Image.open(filepath).convert("RGB")
        inputs = clip_processor(
            text=["ECG medical waveform", "non medical image"],
            images=image,
            return_tensors="pt",
            padding=True
        )
        outputs = clip_model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)
        if probs[0][0].item() > 0.7:
            return True
        else:
            return False
    except Exception as e:
        flash(f"خطأ أثناء التحقق من الصورة: {str(e)}")
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                checkpoint = app.config['CHECKPOINT_PATH']
                if not os.path.exists(checkpoint):
                    flash(f"Error: Model checkpoint not found at {checkpoint}.")
                    return redirect(url_for('index'))

                # 1️⃣ فلترة الصورة/الملف
                if not is_ecg(filepath):
                    flash("الصورة ليست ECG. من فضلك ارفعي صورة رسم قلب.")
                    return redirect(url_for('index'))

                # 2️⃣ لو صالح، نكمل التحليل
                results = predict(filepath, checkpoint)
                return render_template('index.html', results=results, filename=filename)

            except Exception as e:
                print(f"ERROR processing file {filename}: {str(e)}")
                import traceback
                traceback.print_exc()
                flash(f"Error processing file: {str(e)}")
                return redirect(url_for('index'))
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
