from flask import Flask, request, jsonify, render_template_string
import os
import tempfile
import numpy as np
from werkzeug.utils import secure_filename
from universal_processor import universal_loader_with_validation

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'xml', 'mat', 'csv', 'dat', 'hea'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template_string('''
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>ECG Validator API</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; background: #f9f9f9; }
          .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
          h1 { color: #333; }
          .result { margin-top: 20px; padding: 15px; border-radius: 4px; }
          .valid { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
          .invalid { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
          pre { background: #f1f1f1; padding: 10px; border-radius: 4px; overflow-x: auto; }
          button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
          button:hover { background: #0056b3; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>ECG Validation API</h1>
          <p>Upload a file to check if it contains valid ECG signals.</p>
          <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Validate File</button>
          </form>
          <div id="result"></div>
        </div>

        <script>
          document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = 'Validating...';
            resultDiv.className = '';
            
            try {
              const response = await fetch('/validate', {
                method: 'POST',
                body: formData
              });
              const data = await response.json();
              
             let html = '';

if (!data.is_valid) {
  // ❌ Fake / Invalid
  html = `
    <div class="result invalid">
                                  <h1>Invalid</h1>
      <h3>Failed to extract data from SVG</h3>
    </div>
  `;
} else {
  // ✅ Valid ECG
  html = `<div class="result valid">`;
  html += `<h3>✓ Valid ECG</h3>`;

  if (data.top_diagnosis) {
    html += `<hr style="margin: 20px 0; border: 0; border-top: 1px solid #ccc;">`;
    html += `<h2 style="color: #0056b3;">Diagnosis: ${data.top_diagnosis}</h2>`;
    html += `<p><strong>Probability:</strong> ${(data.top_confidence * 100).toFixed(1)}%</p>`;
    html += `<h4>Full Report:</h4><pre>${JSON.stringify(data.prediction, null, 2)}</pre>`;
  }

  html += `</div>`;
}

resultDiv.innerHTML = html;

              
              resultDiv.innerHTML = html;
            } catch (err) {
              resultDiv.innerHTML = `<div class="result invalid">Error: ${err.message}</div>`;
            }
          };
        </script>
      </body>
    </html>
    ''')

# Global model variable
model = None

def get_prediction_model():
    global model
    if model is None:
        print("Loading diagnosis model...")
        import tensorflow as tf
        from tensorflow.keras.models import load_model
        from tensorflow.keras.optimizers import Adam
        
        model_path = os.path.join("model", "model.hdf5")
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}")
            return None
            
        model = load_model(model_path, compile=False)
        model.compile(loss='binary_crossentropy', optimizer=Adam())
    return model

@app.route('/validate', methods=['POST'])
def validate_ecg():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    # Always allow the file - universal_loader will sniff the content
    if file:
        filename = secure_filename(file.filename)
        if not filename:
             filename = "uploaded_file"
             
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            file.save(temp_path)
            
            # Run validation
            signal, validation = universal_loader_with_validation(
                temp_path, 
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

            # Prepare initial response
            response = {
                'filename': filename,
                'is_valid': bool(validation['is_valid']),
                'confidence': float(validation['confidence']) if not np.isnan(validation['confidence']) else 0.0,
                'reasons': validation['reasons'],
                'checks': make_serializable(validation['checks']),
                'essential_checks_passed': int(validation.get('essential_checks_passed', 0))
            }
            
            # Run Prediction if Valid
            if validation['is_valid'] and signal is not None:
                try:
                    pred_model = get_prediction_model()
                    if pred_model:
                        # Prepare input: (1, 4096, 12)
                        x = np.expand_dims(signal, axis=0)
                        
                        # Predict
                        y_score = pred_model.predict(x, verbose=0)[0] # Get first sample
                        
                        labels = ['1dAVb', 'RBBB', 'LBBB', 'SB', 'AF', 'ST']
                        prediction_results = {}
                        for label, score in zip(labels, y_score):
                            prediction_results[label] = float(score)
                            
                        # Sort by confidence
                        sorted_preds = sorted(prediction_results.items(), key=lambda item: item[1], reverse=True)
                        top_pred = sorted_preds[0]
                        
                        response['prediction'] = prediction_results
                        response['top_diagnosis'] = top_pred[0]
                        response['top_confidence'] = top_pred[1]
                except Exception as e:
                    print(f"Prediction Error: {e}")
                    response['prediction_error'] = str(e)
            
            if signal is None:
                pass

            # Clean up logic
            if os.path.exists(temp_path):
                import time
                for i in range(3):
                    try:
                        os.remove(temp_path)
                        break
                    except PermissionError:
                        time.sleep(0.1)
            
            return jsonify(response)
            
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            print(f"API Error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'File upload failed'}), 400

if __name__ == '__main__':
    print("Starting ECG Diagnosis API on http://localhost:5000")
    print("POST /validate to validate and predict.")
    app.run(debug=True, host='0.0.0.0', port=5000)
