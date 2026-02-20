# HeartGuard – ECG Diagnosis System

HeartGuard is an end-to-end ECG diagnosis system that integrates **multiple AI models**, a **Flask web interface**, and an **Apache Airflow workflow** to validate, analyze, and predict cardiac conditions from different ECG data formats.

The project is designed to clearly demonstrate how ECG files flow through validation, model selection, prediction, and reporting in a scalable and debuggable architecture.

---

## 🚀 System Overview

The system consists of **three main layers**:

1. **Flask Web Interface** – User interaction and file upload  
2. **AI Models Layer** – Validation and prediction using two different models  
3. **Apache Airflow** – Orchestrates and documents the full workflow step by step  

---

## 🖥️ Flask Web Interface

The Flask interface allows doctors or users to:

- Upload ECG files in different formats:
  - `.csv`, `.mat`, `.pdf`
  - `.xml`
  - `.jpg`, `.jpeg`, `.png`
- Automatically route each file to the appropriate model
- View:
  - Validation results
  - Model predictions
  - Top diagnosis and confidence scores

### Key Route
`/new-assessment`

This route:
1. Saves uploaded files into the `uploads/` directory
2. Detects file type
3. Sends the file to the correct validation and prediction pipeline
4. Displays results in a unified UI

---

## 🧠 AI Models

### 🔹 Model 1 – ECG Signal Validation & Classification

**Purpose:**
- Validate ECG signal quality
- Predict cardiac conditions from structured ECG signals

**Used For:**
- `.csv`, `.mat`, `.pdf`
- ECG images after preprocessing

**Pipeline:**
1. **Validation**
   - Uses `universal_loader_with_validation`
   - Checks signal integrity, shape, and confidence
2. **Prediction**
   - TensorFlow/Keras model (`model.hdf5`)
   - Multi-label classification

**Output Labels:**
- `1dAVb` – First-degree AV block  
- `RBBB` – Right bundle branch block  
- `LBBB` – Left bundle branch block  
- `SB` – Sinus bradycardia  
- `AF` – Atrial fibrillation  
- `ST` – Sinus tachycardia  

**Output Includes:**
- `is_valid`
- Validation confidence & checks
- Full prediction probabilities
- Top diagnosis + confidence

---

### 🔹 Model 2 – EchoNext (Image-Based ECG Analysis)

**Purpose:**
- Detect whether an image or file represents an ECG
- Predict ECG-related conditions from images

**Used For:**
- `.jpg`, `.jpeg`, `.png`
- `.pdf`, `.xml`

**Pipeline:**
1. **ECG Detection**
   - Uses CLIP (`openai/clip-vit-base-patch32`)
   - Classifies ECG vs non-medical images
2. **Prediction**
   - Uses EchoNext MiniModel (`weights.pt`)
   - Same preprocessing as the original EchoNext project

**Output Includes:**
- `is_ecg`
- Prediction dictionary (if ECG is detected)

---

## 🔄 Apache Airflow Workflow

Airflow is used to **orchestrate and document the entire system flow**, making the project easier to debug, explain, and scale.

### DAG Purpose
- Clearly show **how the system works step by step**
- Track errors at every stage
- Separate validation, prediction, and reporting logic

### DAG Capabilities
- Receive uploaded files
- Detect file types
- Route files to the correct model
- Run validations independently
- Run predictions independently
- Combine results (for image files processed by both models)
- Generate a final execution report

---

### Example Airflow Tasks

- `receive_and_validate_upload`
- `analyze_file_type`
- `validate_for_model1`
- `validate_for_model2`
- `run_model1_predictions`
- `run_model2_predictions`
- `combine_predictions_for_images`
- `cleanup_invalid_files`
- `generate_final_report`

Each task:
- Has a **single clear responsibility**
- Pushes results via **XCom**
- Helps identify exactly where failures occur

---

## 📊 Final Report Generation

At the end of the DAG execution, Airflow generates:

- `FINAL_REPORT.json`
  - Execution summary
  - File distribution
  - Model 1 results
  - Model 2 results
  - Combined results
- `execution_summary.txt`
  - Human-readable summary of the run

---

## 🐳 Deployment & Environment

- **Docker / Astro Runtime**
- Python 3.12
- TensorFlow
- PyTorch
- Transformers (CLIP)
- Apache Airflow
- Flask

---

## 🎯 Project Goals

- Demonstrate a **real-world AI system architecture**
- Show **clear separation of concerns**
- Make debugging and explanation easy for:
  - Graduation projects
  - System architecture discussions
  - AI pipeline demonstrations

---

## 📌 Current Status

✅ Flask interface working  
✅ Two AI models integrated  
✅ Airflow DAG fully describes system workflow  
⚠️ Ongoing improvements:
- Permissions handling inside Docker
- Performance optimization
- UI enhancements

---

## 👩‍💻 Author

**HeartGuard Project**  
Software Engineering – AI & Backend Focus  

---

