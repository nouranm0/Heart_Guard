# dags/ecg_full_project_debug_detailed.py
import os
import json
from airflow import DAG
from datetime import datetime
from airflow.providers.standard.operators.python import PythonOperator

DEFAULT_ARGS = {
    "owner": "heartgaurd",
    "retries": 1
}

UPLOAD_DIR = "/usr/local/airflow/uploads"
RESULTS_DIR = "/usr/local/airflow/results"

with DAG(
    dag_id="ecg_full_project_debug_detailed",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 2, 6),
    schedule=None,
    catchup=False,
    tags=["ECG", "Debug"]
) as dag:

    # -------------------- Task 1: Ensure Directories --------------------
    def ensure_directories():
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(RESULTS_DIR, exist_ok=True)
        return {"uploads": UPLOAD_DIR, "results": RESULTS_DIR}

    t1 = PythonOperator(
        task_id="ensure_directories",
        python_callable=ensure_directories
    )

    # -------------------- Task 2: List Uploaded Files --------------------
    def list_upload_files(**context):
        files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)]
        context['ti'].xcom_push(key="all_files", value=files)
        return files

    t2 = PythonOperator(
        task_id="list_upload_files",
        python_callable=list_upload_files,
    )

    # -------------------- Task 3: Split Files by Type --------------------
    def split_by_filetype(**context):
        all_files = context['ti'].xcom_pull(key="all_files", task_ids="list_upload_files")
        ecg_files, echonext_files, dual_files = [], [], []

        for f in all_files:
            ext = f.rsplit('.', 1)[-1].lower()
            if ext in ["csv", "mat", "pdf"]:
                ecg_files.append(f)
            elif ext == "xml":
                echonext_files.append(f)
            elif ext in ["jpg", "jpeg", "png", "pdf"]:
                dual_files.append(f)

        context['ti'].xcom_push(key="ecg_files", value=ecg_files + dual_files)
        context['ti'].xcom_push(key="echonext_files", value=echonext_files + dual_files)
        return {"ecg": ecg_files + dual_files, "echonext": echonext_files + dual_files}

    t3 = PythonOperator(
        task_id="split_by_filetype",
        python_callable=split_by_filetype,
    )

    # -------------------- Task 4: Validate ECG Files --------------------
    def validate_ecg_files(**context):
        from app.doctor.validation_service import validate_and_predict
        ecg_files = context['ti'].xcom_pull(key="ecg_files", task_ids="split_by_filetype")
        results = {}
        invalid_files = []

        for f in ecg_files:
            try:
                res = validate_and_predict(f)
                results[f] = res
                if not res.get("is_valid", False):
                    invalid_files.append(f)
            except Exception as e:
                results[f] = {"error": str(e)}
                invalid_files.append(f)

        context['ti'].xcom_push(key="ecg_validation", value=results)
        context['ti'].xcom_push(key="invalid_ecg_files", value=invalid_files)
        return results

    t4 = PythonOperator(
        task_id="validate_ecg_files",
        python_callable=validate_ecg_files,
    )

    # -------------------- Task 5: Validate EchoNext Files --------------------
    def validate_echonext_files(**context):
        from app.doctor.echonext_service import echonext_predict
        echonext_files = context['ti'].xcom_pull(key="echonext_files", task_ids="split_by_filetype")
        results = {}
        invalid_files = []

        for f in echonext_files:
            try:
                res = echonext_predict(f)
                results[f] = res
                if not res.get("is_ecg", False):
                    invalid_files.append(f)
            except Exception as e:
                results[f] = {"error": str(e)}
                invalid_files.append(f)

        context['ti'].xcom_push(key="echonext_validation", value=results)
        context['ti'].xcom_push(key="invalid_echonext_files", value=invalid_files)
        return results

    t5 = PythonOperator(
        task_id="validate_echonext_files",
        python_callable=validate_echonext_files,
    )

    # -------------------- Task 6: Aggregate All Results --------------------
    def aggregate_results(**context):
        ecg_results = context['ti'].xcom_pull(key="ecg_validation", task_ids="validate_ecg_files")
        echonext_results = context['ti'].xcom_pull(key="echonext_validation", task_ids="validate_echonext_files")
        aggregated = {**ecg_results, **echonext_results}

        output_path = os.path.join(RESULTS_DIR, "aggregated_results.json")
        with open(output_path, "w") as f:
            json.dump(aggregated, f, indent=4)

        return output_path

    t6 = PythonOperator(
        task_id="aggregate_results",
        python_callable=aggregate_results,
    )

    # -------------------- Task 7: Cleanup Invalid Files --------------------
    def cleanup_invalid_files(**context):
        invalid_ecg = context['ti'].xcom_pull(key="invalid_ecg_files", task_ids="validate_ecg_files") or []
        invalid_echo = context['ti'].xcom_pull(key="invalid_echonext_files", task_ids="validate_echonext_files") or []
        all_invalid = invalid_ecg + invalid_echo
        for f in all_invalid:
            if os.path.exists(f):
                os.remove(f)
        return all_invalid

    t7 = PythonOperator(
        task_id="cleanup_invalid_files",
        python_callable=cleanup_invalid_files,
    )

    # -------------------- Task 8: Generate Architecture Diagram --------------------
    def generate_architecture_diagram():
        import graphviz
        dot = graphviz.Digraph(comment="ECG System Architecture")
        dot.node("A", "Uploads")
        dot.node("B", "Split by Type")
        dot.node("C", "ECG Validation")
        dot.node("D", "EchoNext Validation")
        dot.node("E", "Aggregate Results")
        dot.node("F", "Cleanup Invalid Files")
        dot.edge("A", "B")
        dot.edge("B", "C")
        dot.edge("B", "D")
        dot.edge("C", "E")
        dot.edge("D", "E")
        dot.edge("E", "F")
        output_path = os.path.join(RESULTS_DIR, "architecture.gv")
        dot.render(output_path, view=False, format="png")
        return output_path

    t8 = PythonOperator(
        task_id="generate_architecture_diagram",
        python_callable=generate_architecture_diagram
    )

    # -------------------- DAG Dependencies --------------------
    t1 >> t2 >> t3
    t3 >> [t4, t5]
    [t4, t5] >> t6 >> t7 >> t8
