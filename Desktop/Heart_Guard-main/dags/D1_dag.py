from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import sys
import json
import shutil

# ----- Paths -----
AIRFLOW_HOME = os.environ.get('AIRFLOW_HOME', '/usr/local/airflow')
UPLOAD_DIR = os.path.join(AIRFLOW_HOME, "uploads")
RESULTS_DIR = os.path.join(AIRFLOW_HOME, "results")
sys.path.append(os.path.join(AIRFLOW_HOME, "automatic_ecg_diagnosis_master"))

# ----- Default args -----
default_args = {
    'owner': 'nouran',
    'depends_on_past': False,
    'retries': 1,
}

# -------- Task Functions --------
def ensure_directories():
    """Make sure uploads and results folders exist"""
    for folder in [UPLOAD_DIR, RESULTS_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    return {"uploads": UPLOAD_DIR, "results": RESULTS_DIR}

def list_upload_files():
    """List all files in the uploads folder"""
    files = []
    if os.path.exists(UPLOAD_DIR):
        files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)]
        files = [f for f in files if os.path.isfile(f)]
    if not files:
        raise FileNotFoundError(f"No files found in {UPLOAD_DIR}")
    return files

def validate_files(**context):
    """Check if uploaded files are readable"""
    files = context['ti'].xcom_pull(task_ids='list_upload_files')
    valid_files = []
    invalid_files = []
    for f in files:
        try:
            if os.path.getsize(f) > 0:
                valid_files.append(f)
            else:
                invalid_files.append(f)
        except Exception:
            invalid_files.append(f)
    # Push to XCom
    return {"valid_files": valid_files, "invalid_files": invalid_files}

def run_prediction(**context):
    """Run validate_and_predict on each valid ECG file"""
    from app.doctor.validation_service import validate_and_predict
    xcom_files = context['ti'].xcom_pull(task_ids='validate_files')
    valid_files = xcom_files.get("valid_files", [])
    results = {}
    errors = {}
    for f in valid_files:
        try:
            results[os.path.basename(f)] = validate_and_predict(f)
        except Exception as e:
            errors[os.path.basename(f)] = str(e)
    # Save errors to results folder
    if errors:
        error_file = os.path.join(RESULTS_DIR, "prediction_errors.json")
        with open(error_file, "w") as ef:
            json.dump(errors, ef, indent=4)
    return results

def save_results(**context):
    """Save prediction results to JSON"""
    results = context['ti'].xcom_pull(task_ids='run_prediction') or {}
    output_file = os.path.join(RESULTS_DIR, "aggregated_results.json")
    with open(output_file, "w") as fp:
        json.dump(results, fp, indent=4)
    return output_file

def generate_architecture_diagram(**context):
    """Generate a DAG diagram even if predictions failed"""
    from graphviz import Digraph
    dot = Digraph(comment='ECG Project Architecture')
    dot.node('A', 'Check Uploads')
    dot.node('B', 'Validate Files')
    dot.node('C', 'Run Predictions')
    dot.node('D', 'Save Results')
    dot.node('E', 'Generate Diagram')
    dot.edges(['AB', 'BC', 'CD', 'DE'])
    diagram_path = os.path.join(RESULTS_DIR, 'architecture.gv')
    dot.save(diagram_path)
    return diagram_path

def cleanup_invalid_files(**context):
    """Optionally move invalid files to a subfolder for inspection"""
    xcom_files = context['ti'].xcom_pull(task_ids='validate_files')
    invalid_files = xcom_files.get("invalid_files", [])
    if invalid_files:
        invalid_dir = os.path.join(UPLOAD_DIR, "invalid_files")
        os.makedirs(invalid_dir, exist_ok=True)
        for f in invalid_files:
            shutil.move(f, os.path.join(invalid_dir, os.path.basename(f)))
    return invalid_files

# -------- DAG Definition --------
with DAG(
    'ecg_FULL_PROJECT_DEBUG',
    default_args=default_args,
    schedule=None,
    start_date=datetime(2026, 2, 6),
    catchup=False,
    description="ECG project with detailed tasks and error tracking"
) as dag:

    t0_ensure_dirs = PythonOperator(
        task_id='ensure_directories',
        python_callable=ensure_directories
    )

    t1_list_files = PythonOperator(
        task_id='list_upload_files',
        python_callable=list_upload_files
    )

    t2_validate = PythonOperator(
        task_id='validate_files',
        python_callable=validate_files,
    )

    t3_cleanup = PythonOperator(
        task_id='cleanup_invalid_files',
        python_callable=cleanup_invalid_files,
    )

    t4_predict = PythonOperator(
        task_id='run_prediction',
        python_callable=run_prediction,
    )

    t5_save = PythonOperator(
        task_id='save_results',
        python_callable=save_results,
    )

    t6_diagram = PythonOperator(
        task_id='generate_architecture_diagram',
        python_callable=generate_architecture_diagram,
    )

    # -------- Task Dependencies --------
    t0_ensure_dirs >> t1_list_files >> t2_validate
    t2_validate >> t3_cleanup
    t2_validate >> t4_predict >> t5_save >> t6_diagram
