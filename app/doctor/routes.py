#E:\heartgaurd (5)\heartgaurd (2)\heartgaurd\heartgaurd\app\doctor\routes.py
from flask import Blueprint, render_template, request
import os
from .validation_service import validate_and_predict
from .echonext_service import echonext_predict

ECHONEXT_MODEL = "model/weights.pt"
doctor_bp = Blueprint('doctor', __name__)


@doctor_bp.route('/')
def splash():
    return render_template('splash.html')


@doctor_bp.route('/intro')
def intro():
    return render_template('intro.html')


@doctor_bp.route('/model')
def model_page():
    return render_template('model.html')

@doctor_bp.route('/new-assessment', methods=['GET', 'POST'])
def new_assessment():
    validation_result = {}
    all_results = []
    top_diagnosis = None
    top_confidence = None

    # مجلد الحفظ النهائي
    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)  # لو المجلد مش موجود، يتعمل

    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            return render_template("new_assessment.html")

        ext = file.filename.rsplit(".", 1)[-1].lower()
        # الحفظ في مجلد uploads
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(file_path)

        try:
            if ext in ["csv", "pdf", "mat"]:
                validation_result = validate_and_predict(file_path) or {}
                if validation_result.get("prediction"):
                    all_results = [(k, v) for k, v in validation_result["prediction"].items()]
                    top_diagnosis = validation_result.get("top_diagnosis")
                    top_confidence = validation_result.get("top_confidence")

            elif ext == "xml":
                echonext_results = echonext_predict(file_path)
                if echonext_results and echonext_results.get("is_ecg"):
                    all_results = [(k, v) for k, v in echonext_results.get("prediction").items()]

            elif ext in ["jpg", "jpeg", "png", "pdf"]:
                validation_result = validate_and_predict(file_path) or {}
                if validation_result.get("prediction"):
                    all_results = [(k, v) for k, v in validation_result["prediction"].items()]
                    top_diagnosis = validation_result.get("top_diagnosis")
                    top_confidence = validation_result.get("top_confidence")

                echonext_results = echonext_predict(file_path)
                if echonext_results and echonext_results.get("is_ecg"):
                    for k, v in echonext_results.get("prediction").items():
                        all_results.append((f"{k}", v/10))

        except Exception as e:
            print(f"Error in new_assessment: {e}")
            import traceback
            traceback.print_exc()

    return render_template(
        "new_assessment.html",
        results=all_results,
        top_diagnosis=top_diagnosis,
        top_confidence=top_confidence,
        validation=validation_result
    )
