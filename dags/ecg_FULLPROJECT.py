from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import sys
import json

# ----- Paths -----
AIRFLOW_HOME = os.environ.get('AIRFLOW_HOME', '/usr/local/airflow')
sys.path.append(AIRFLOW_HOME)
sys.path.append(os.path.join(AIRFLOW_HOME, "automatic_ecg_diagnosis_master"))

# ----- Import prediction service -----

UPLOAD_DIR = os.path.join(AIRFLOW_HOME, "results")

# ----- Default args -----
default_args = {
    'owner': 'nouran',
    'depends_on_past': False,
}

# -------- Task Functions --------
def check_upload_files():
    """List all files in the uploads folder"""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)]
    # Ensure list of strings, no None values
    files = [f for f in files if f is not None]
    return files

def run_validate_predict(**context):
    from app.doctor.validation_service import validate_and_predict
    """Run validation and prediction on uploaded ECG files"""
    files = context['ti'].xcom_pull(task_ids='t1_upload_check') or []
    if not files:
        return {"error": "No files uploaded"}

    results = {}
    for f in files:
        if f is None or not isinstance(f, str):
            continue  # skip invalid entries
        try:
            results[os.path.basename(f)] = validate_and_predict(f)
        except Exception as e:
            results[os.path.basename(f)] = {"error": str(e)}
    return results

def aggregate_results(**context):
    """Aggregate results and save to JSON"""
    echo_results = context['ti'].xcom_pull(task_ids='t2_validate_predict') or {}
    aggregated = {f: echo_results.get(f) for f in echo_results if f is not None}

    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    output_file = os.path.join(UPLOAD_DIR, "aggregated_results.json")
    with open(output_file, "w") as fp:
        json.dump(aggregated, fp, indent=4)
    return aggregated

def generate_architecture_diagram():
    """Generate a simple DAG diagram using graphviz"""
    from graphviz import Digraph

    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    dot = Digraph(comment='ECG Project Architecture')
    dot.node('A', 'Upload Files')
    dot.node('B', 'Validate & Predict')
    dot.node('C', 'Aggregate Results')
    dot.node('D', 'View/Download Results')
    dot.edges(['AB', 'BC', 'CD'])

    diagram_path = os.path.join(UPLOAD_DIR, 'architecture.gv')
    #dot.render(diagram_path, view=False)
    dot.save(diagram_path)
    return diagram_path

# -------- DAG Definition --------
with DAG(
    'ecg_FULL_PROJECT',
    default_args=default_args,
    schedule=None,
    start_date=datetime(2026, 2, 6),
    catchup=False,
) as dag:

    t1 = PythonOperator(
        task_id='t1_upload_check',
        python_callable=check_upload_files
    )

    t2 = PythonOperator(
        task_id='t2_validate_predict',
        python_callable=run_validate_predict,
    )

    t3 = PythonOperator(
        task_id='t3_aggregate_results',
        python_callable=aggregate_results,
    )

    t4 = PythonOperator(
        task_id='t4_generate_architecture',
        python_callable=generate_architecture_diagram
    )

    t1 >> t2 >> t3 >> t4
