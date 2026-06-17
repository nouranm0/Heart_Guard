"""
DAG تفصيلية لسير العمل في نظام تشخيص ECG
توضح مسار الملف من الرفع حتى النتيجة النهائية
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from datetime import timedelta
import os
import sys
import json
import shutil
from typing import Dict, List, Tuple
import mimetypes

# ----- إعداد المسارات -----
AIRFLOW_HOME = os.environ.get('AIRFLOW_HOME', '/usr/local/airflow')
PROJECT_ROOT = os.path.join(AIRFLOW_HOME, "heartguard_project")
sys.path.extend([
    PROJECT_ROOT,
    os.path.join(PROJECT_ROOT, "automatic_ecg_diagnosis_master"),
    os.path.join(PROJECT_ROOT, "IntroECG_master")
])

# ----- المجلدات -----
UPLOAD_DIR = "/usr/local/airflow/uploads"
RESULTS_DIR = "/usr/local/airflow/results"
MODEL1_RESULTS_DIR = os.path.join(RESULTS_DIR, "model1_results")
MODEL2_RESULTS_DIR = os.path.join(RESULTS_DIR, "model2_results")
ERRORS_DIR = os.path.join(RESULTS_DIR, "errors")

# ----- Default args -----
default_args = {
    'owner': 'nouran',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ===========================================
# وظائف المهام التفصيلية
# ===========================================

def setup_environment(**context) -> Dict:
    """Task 1: إعداد البيئة والمجلدات المطلوبة"""
    folders = [
        UPLOAD_DIR, RESULTS_DIR, MODEL1_RESULTS_DIR, 
        MODEL2_RESULTS_DIR, ERRORS_DIR
    ]
    
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✓ Created directory: {folder}")
    
    # تسجيل معلومات البيئة
    env_info = {
        "python_version": sys.version,
        "airflow_home": AIRFLOW_HOME,
        "project_root": PROJECT_ROOT,
        "directories_created": folders,
        "timestamp": datetime.now().isoformat()
    }
    
    # حفظ معلومات البيئة
    env_file = os.path.join(RESULTS_DIR, "environment_info.json")
    with open(env_file, "w") as f:
        json.dump(env_info, f, indent=4)
    
    return {
        "status": "success",
        "env_file": env_file,
        "directories": folders
    }

def receive_and_validate_upload(**context) -> Dict:
    """Task 2: استقبال الملف والتحقق الأساسي"""
    # محاكاة استقبال ملف (في الواقع سيكون من Flask)
    # هنا نأخذ الملفات من مجلد الرفع
    
    uploaded_files = []
    if os.path.exists(UPLOAD_DIR):
        files = os.listdir(UPLOAD_DIR)
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, file)
            if os.path.isfile(file_path):
                # التحقق الأساسي
                file_info = {
                    "filename": file,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "extension": os.path.splitext(file)[1].lower(),
                    "upload_time": datetime.now().isoformat()
                }
                uploaded_files.append(file_info)
    
    if not uploaded_files:
        raise ValueError("❌ لا توجد ملفات مرفوعة للمعالجة")
    
    print(f"✓ تم استقبال {len(uploaded_files)} ملف(ـات)")
    return {
        "total_files": len(uploaded_files),
        "files": uploaded_files,
        "upload_dir": UPLOAD_DIR
    }

def analyze_file_type(**context) -> Dict:
    """Task 3: تحليل نوع الملف وتحديد المسار"""
    files_info = context['ti'].xcom_pull(task_ids='receive_and_validate_upload')
    files = files_info["files"]
    
    categorized_files = {
        "csv_pdf_mat": [],  # للموديل الأول
        "xml": [],          # للموديل الثاني (EchoNext)
        "images": [],       # للموديلين معًا
        "unsupported": []   # غير مدعوم
    }
    
    supported_extensions = {
        "csv_pdf_mat": ['.csv', '.pdf', '.mat'],
        "xml": ['.xml'],
        "images": ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    }
    
    for file_info in files:
        ext = file_info["extension"]
        file_path = file_info["path"]
        
        # تحديد الفئة
        if ext in supported_extensions["csv_pdf_mat"]:
            category = "csv_pdf_mat"
        elif ext in supported_extensions["xml"]:
            category = "xml"
        elif ext in supported_extensions["images"]:
            # التحقق إذا كانت صورة ECG
            try:
                from PIL import Image
                img = Image.open(file_path)
                file_info["image_dimensions"] = f"{img.width}x{img.height}"
                category = "images"
            except Exception as e:
                category = "unsupported"
                file_info["error"] = str(e)
        else:
            category = "unsupported"
        
        file_info["category"] = category
        categorized_files[category].append(file_info)
    
    # حفظ نتائج التصنيف
    classification_file = os.path.join(RESULTS_DIR, "file_classification.json")
    with open(classification_file, "w") as f:
        json.dump(categorized_files, f, indent=4, default=str)
    
    print(f"✓ تصنيف الملفات:")
    for category, files_list in categorized_files.items():
        print(f"  - {category}: {len(files_list)} ملف")
    
    return categorized_files

def validate_for_model1(**context) -> Dict:
    """Task 4: التحقق والتحضير للموديل الأول"""
    from app.doctor.validation_service import universal_loader_with_validation
    
    categorized_files = context['ti'].xcom_pull(task_ids='analyze_file_type')
    files_to_process = categorized_files.get("csv_pdf_mat", []) + \
                      categorized_files.get("images", [])
    
    validation_results = []
    
    for file_info in files_to_process:
        try:
            signal, validation = universal_loader_with_validation(
                file_info["path"],
                validate=True,
                strict=False,
                verbose=True
            )
            
            result = {
                "filename": file_info["filename"],
                "is_valid": bool(validation.get("is_valid", False)),
                "confidence": float(validation.get("confidence", 0.0)),
                "reasons": validation.get("reasons", []),
                "signal_shape": signal.shape if signal is not None else None,
                "file_category": file_info["category"],
                "validation_timestamp": datetime.now().isoformat()
            }
            
            validation_results.append(result)
            
            print(f"✓ التحقق: {file_info['filename']} - {'صالح' if result['is_valid'] else 'غير صالح'}")
            
        except Exception as e:
            error_result = {
                "filename": file_info["filename"],
                "is_valid": False,
                "error": str(e),
                "validation_timestamp": datetime.now().isoformat()
            }
            validation_results.append(error_result)
            print(f"✗ خطأ في التحقق: {file_info['filename']} - {e}")
    
    # حفظ نتائج التحقق
    validation_file = os.path.join(MODEL1_RESULTS_DIR, "validation_results.json")
    with open(validation_file, "w") as f:
        json.dump(validation_results, f, indent=4, default=str)
    
    return {
        "validation_results": validation_results,
        "validation_file": validation_file,
        "total_files": len(files_to_process),
        "valid_files": [r for r in validation_results if r.get("is_valid")],
        "invalid_files": [r for r in validation_results if not r.get("is_valid")]
    }

def validate_for_model2(**context) -> Dict:
    """Task 5: التحقق والتحضير للموديل الثاني (EchoNext)"""
    from app.doctor.echonext_service import is_ecg_image
    
    categorized_files = context['ti'].xcom_pull(task_ids='analyze_file_type')
    files_to_process = categorized_files.get("xml", []) + \
                      categorized_files.get("images", [])
    
    validation_results = []
    
    for file_info in files_to_process:
        try:
            is_ecg = is_ecg_image(file_info["path"])
            
            result = {
                "filename": file_info["filename"],
                "is_ecg": is_ecg,
                "file_category": file_info["category"],
                "validation_timestamp": datetime.now().isoformat()
            }
            
            validation_results.append(result)
            
            print(f"✓ EchoNext التحقق: {file_info['filename']} - {'ECG' if is_ecg else 'ليس ECG'}")
            
        except Exception as e:
            error_result = {
                "filename": file_info["filename"],
                "is_ecg": False,
                "error": str(e),
                "validation_timestamp": datetime.now().isoformat()
            }
            validation_results.append(error_result)
            print(f"✗ خطأ في EchoNext: {file_info['filename']} - {e}")
    
    # حفظ نتائج التحقق
    validation_file = os.path.join(MODEL2_RESULTS_DIR, "echonext_validation.json")
    with open(validation_file, "w") as f:
        json.dump(validation_results, f, indent=4, default=str)
    
    return {
        "validation_results": validation_results,
        "validation_file": validation_file,
        "total_files": len(files_to_process),
        "ecg_files": [r for r in validation_results if r.get("is_ecg")],
        "non_ecg_files": [r for r in validation_results if not r.get("is_ecg")]
    }

def run_model1_predictions(**context) -> Dict:
    """Task 6: تشغيل تنبؤات الموديل الأول"""
    from app.doctor.validation_service import validate_and_predict
    
    validation_info = context['ti'].xcom_pull(task_ids='validate_for_model1')
    valid_files = validation_info.get("valid_files", [])
    
    predictions = []
    
    for file_result in valid_files:
        try:
            filename = file_result["filename"]
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # التنبؤ باستخدام الموديل الأول
            prediction_result = validate_and_predict(file_path)
            
            result = {
                "filename": filename,
                "model": "ECG_Validation_Model",
                "predictions": prediction_result.get("prediction", {}),
                "top_diagnosis": prediction_result.get("top_diagnosis"),
                "top_confidence": prediction_result.get("top_confidence"),
                "is_valid": prediction_result.get("is_valid"),
                "prediction_timestamp": datetime.now().isoformat()
            }
            
            predictions.append(result)
            
            print(f"✓ الموديل 1 تنبؤ: {filename} - التشخيص: {result['top_diagnosis']}")
            
        except Exception as e:
            error_result = {
                "filename": file_result.get("filename", "unknown"),
                "error": str(e),
                "prediction_timestamp": datetime.now().isoformat()
            }
            predictions.append(error_result)
            print(f"✗ خطأ في الموديل 1: {error_result['filename']} - {e}")
    
    # حفظ التنبؤات
    predictions_file = os.path.join(MODEL1_RESULTS_DIR, "model1_predictions.json")
    with open(predictions_file, "w") as f:
        json.dump(predictions, f, indent=4, default=str)
    
    return {
        "predictions": predictions,
        "predictions_file": predictions_file,
        "total_predictions": len(predictions)
    }

def run_model2_predictions(**context) -> Dict:
    """Task 7: تشغيل تنبؤات الموديل الثاني (EchoNext)"""
    from app.doctor.echonext_service import echonext_predict
    
    validation_info = context['ti'].xcom_pull(task_ids='validate_for_model2')
    ecg_files = validation_info.get("ecg_files", [])
    
    predictions = []
    
    for file_result in ecg_files:
        try:
            filename = file_result["filename"]
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # التنبؤ باستخدام EchoNext
            prediction_result = echonext_predict(file_path)
            
            result = {
                "filename": filename,
                "model": "EchoNext_Model",
                "is_ecg": prediction_result.get("is_ecg", False),
                "predictions": prediction_result.get("prediction", {}),
                "prediction_timestamp": datetime.now().isoformat()
            }
            
            predictions.append(result)
            
            # عرض عينات من التنبؤات
            if result["predictions"]:
                sample_preds = dict(list(result["predictions"].items())[:3])
                print(f"✓ EchoNext تنبؤ: {filename} - عينات: {sample_preds}")
            
        except Exception as e:
            error_result = {
                "filename": file_result.get("filename", "unknown"),
                "error": str(e),
                "prediction_timestamp": datetime.now().isoformat()
            }
            predictions.append(error_result)
            print(f"✗ خطأ في EchoNext: {error_result['filename']} - {e}")
    
    # حفظ التنبؤات
    predictions_file = os.path.join(MODEL2_RESULTS_DIR, "model2_predictions.json")
    with open(predictions_file, "w") as f:
        json.dump(predictions, f, indent=4, default=str)
    
    return {
        "predictions": predictions,
        "predictions_file": predictions_file,
        "total_predictions": len(predictions)
    }

def combine_predictions_for_images(**context) -> Dict:
    """Task 8: دمج تنبؤات الصور التي مرت على الموديلين"""
    model1_results = context['ti'].xcom_pull(task_ids='run_model1_predictions')
    model2_results = context['ti'].xcom_pull(task_ids='run_model2_predictions')
    
    combined_results = []
    
    # البحث عن الملفات المشتركة (الصور)
    model1_files = {r.get("filename"): r for r in model1_results.get("predictions", []) 
                   if "filename" in r and "error" not in r}
    model2_files = {r.get("filename"): r for r in model2_results.get("predictions", []) 
                   if "filename" in r and "error" not in r}
    
    # الملفات المشتركة (الصور التي مرت على الموديلين)
    common_files = set(model1_files.keys()) & set(model2_files.keys())
    
    for filename in common_files:
        try:
            model1_pred = model1_files[filename]
            model2_pred = model2_files[filename]
            
            combined_result = {
                "filename": filename,
                "file_type": "image",
                "model1_predictions": model1_pred.get("predictions", {}),
                "model1_top_diagnosis": model1_pred.get("top_diagnosis"),
                "model1_confidence": model1_pred.get("top_confidence"),
                "model2_predictions": model2_pred.get("predictions", {}),
                "combined_timestamp": datetime.now().isoformat(),
                "notes": "Image processed by both models"
            }
            
            combined_results.append(combined_result)
            
            print(f"✓ دمج نتائج: {filename} - نموذجان")
            
        except Exception as e:
            print(f"✗ خطأ في الدمج: {filename} - {e}")
    
    # حفظ النتائج المدمجة
    if combined_results:
        combined_file = os.path.join(RESULTS_DIR, "combined_predictions.json")
        with open(combined_file, "w") as f:
            json.dump(combined_results, f, indent=4, default=str)
    
    return {
        "combined_results": combined_results,
        "common_files_count": len(common_files),
        "combined_file": combined_file if combined_results else None
    }

def generate_final_report(**context) -> Dict:
    """Task 9: إنشاء التقرير النهائي"""
    # جمع النتائج من جميع المهام
def generate_final_report(**context):
    ti = context['ti']
    dag_run = context['dag_run']

    file_info = ti.xcom_pull(task_ids='receive_and_validate_upload')
    file_types = ti.xcom_pull(task_ids='analyze_file_type')
    model1_validation = ti.xcom_pull(task_ids='validate_for_model1')
    model2_validation = ti.xcom_pull(task_ids='validate_for_model2')
    model1_predictions = ti.xcom_pull(task_ids='run_model1_predictions')
    model2_predictions = ti.xcom_pull(task_ids='run_model2_predictions')
    combined_results = ti.xcom_pull(task_ids='combine_predictions_for_images')

    final_report = {
        "execution_summary": {
            "total_files_uploaded": file_info.get("total_files", 0),
            "start_time": (dag_run.start_date or datetime.now()).isoformat(),
            "end_time": datetime.now().isoformat(),
            "dag_id": dag_run.dag_id,
            "run_id": dag_run.run_id
        },
        "file_distribution": {
            "csv_pdf_mat_files": len(file_types.get("csv_pdf_mat", [])),
            "xml_files": len(file_types.get("xml", [])),
            "image_files": len(file_types.get("images", [])),
            "unsupported_files": len(file_types.get("unsupported", []))
        },
        "model1_results": {
            "valid_files": len(model1_validation.get("valid_files", [])),
            "invalid_files": len(model1_validation.get("invalid_files", [])),
            "successful_predictions": len([p for p in model1_predictions.get("predictions", []) 
                                          if "predictions" in p])
        },
        "model2_results": {
            "ecg_files": len(model2_validation.get("ecg_files", [])),
            "non_ecg_files": len(model2_validation.get("non_ecg_files", [])),
            "successful_predictions": len([p for p in model2_predictions.get("predictions", []) 
                                          if "predictions" in p])
        },
        "combined_results": {
            "files_processed_by_both_models": combined_results.get("common_files_count", 0),
            "has_combined_results": bool(combined_results.get("combined_results", []))
        },
        "system_status": "COMPLETED"
    }
    
    # حفظ التقرير النهائي
    report_file = os.path.join(RESULTS_DIR, "FINAL_REPORT.json")
    with open(report_file, "w") as f:
        json.dump(final_report, f, indent=4, default=str)
    
    # إنشاء ملخص نصي
    summary_file = os.path.join(RESULTS_DIR, "execution_summary.txt")
    with open(summary_file, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("ملخص تنفيذ نظام تشخيص ECG\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"تاريخ التنفيذ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"إجمالي الملفات المرفوعة: {final_report['execution_summary']['total_files_uploaded']}\n")
        f.write(f"الملفات الصالحة للموديل 1: {final_report['model1_results']['valid_files']}\n")
        f.write(f"الملفات الصالحة للموديل 2: {final_report['model2_results']['ecg_files']}\n")
        f.write(f"الملفات المعالجة بكلا النموذجين: {final_report['combined_results']['files_processed_by_both_models']}\n")
        f.write(f"حالة النظام: {final_report['system_status']}\n")
        f.write("\n" + "=" * 60)
    
    print("=" * 60)
    print("✓ التقرير النهائي جاهز!")
    print(f"✓ الملفات المرفوعة: {final_report['execution_summary']['total_files_uploaded']}")
    print(f"✓ تنبؤات الموديل 1: {final_report['model1_results']['successful_predictions']}")
    print(f"✓ تنبؤات الموديل 2: {final_report['model2_results']['successful_predictions']}")
    print("=" * 60)
    
    return {
        "final_report": final_report,
        "report_file": report_file,
        "summary_file": summary_file
    }

def create_visualization(**context) -> Dict:
    """Task 10: إنشاء تصور بياني لسير العمل"""
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
        
        # إنشاء مخطط تدفق العمل
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('تصور سير عمل نظام تشخيص ECG', fontsize=16, fontweight='bold')
        
        # 1. مخطط تدفق الملفات
        ax1 = axes[0, 0]
        workflow_steps = [
            'رفع الملف', 'تحليل النوع', 
            'التحقق للنموذج 1', 'التحقق للنموذج 2',
            'التنبؤ بالنموذج 1', 'التنبؤ بالنموذج 2',
            'دمج النتائج', 'التقرير النهائي'
        ]
        
        ax1.barh(range(len(workflow_steps)), [1]*len(workflow_steps), color='skyblue')
        ax1.set_yticks(range(len(workflow_steps)))
        ax1.set_yticklabels(workflow_steps, fontsize=10)
        ax1.set_title('مراحل سير العمل')
        ax1.set_xlabel('مرحلة')
        
        # 2. توزيع أنواع الملفات
        ax2 = axes[0, 1]
        file_types = context['ti'].xcom_pull(task_ids='analyze_file_type')
        labels = ['CSV/PDF/MAT', 'XML', 'صور', 'غير مدعوم']
        sizes = [
            len(file_types.get("csv_pdf_mat", [])),
            len(file_types.get("xml", [])),
            len(file_types.get("images", [])),
            len(file_types.get("unsupported", []))
        ]
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax2.set_title('توزيع أنواع الملفات')
        
        # 3. نتائج النماذج
        ax3 = axes[1, 0]
        final_report = context['ti'].xcom_pull(task_ids='generate_final_report')
        if final_report:
            model_labels = ['النموذج 1\n(صالح)', 'النموذج 1\n(التنبؤ)', 
                           'النموذج 2\n(ECG)', 'النموذج 2\n(التنبؤ)']
            model_values = [
                final_report['final_report']['model1_results']['valid_files'],
                final_report['final_report']['model1_results']['successful_predictions'],
                final_report['final_report']['model2_results']['ecg_files'],
                final_report['final_report']['model2_results']['successful_predictions']
            ]
            ax3.bar(model_labels, model_values, color=['blue', 'lightblue', 'green', 'lightgreen'])
            ax3.set_title('أداء النماذج')
            ax3.set_ylabel('عدد الملفات')
        
        # 4. مخطط تدفق النظام
        ax4 = axes[1, 1]
        G = nx.DiGraph()
        
        nodes = ['رفع\nملف', 'تحليل\nالنوع', 'النموذج 1\n(تحقق)', 
                'النموذج 2\n(تحقق)', 'النموذج 1\n(تنبؤ)', 
                'النموذج 2\n(تنبؤ)', 'دمج\nالنتائج', 'تقرير\nنهائي']
        
        for node in nodes:
            G.add_node(node)
        
        edges = [('رفع\nملف', 'تحليل\nالنوع'),
                ('تحليل\nالنوع', 'النموذج 1\n(تحقق)'),
                ('تحليل\nالنوع', 'النموذج 2\n(تحقق)'),
                ('النموذج 1\n(تحقق)', 'النموذج 1\n(تنبؤ)'),
                ('النموذج 2\n(تحقق)', 'النموذج 2\n(تنبؤ)'),
                ('النموذج 1\n(تنبؤ)', 'دمج\nالنتائج'),
                ('النموذج 2\n(تنبؤ)', 'دمج\nالنتائج'),
                ('دمج\nالنتائج', 'تقرير\nنهائي')]
        
        for edge in edges:
            G.add_edge(*edge)
        
        pos = nx.spring_layout(G, seed=42)
        nx.draw(G, pos, with_labels=True, node_color='lightblue', 
                node_size=3000, ax=ax4, font_size=9, 
                arrows=True, arrowsize=20)
        ax4.set_title('مخطط تدفق النظام')
        
        plt.tight_layout()
        
        # حفظ الملف
        viz_file = os.path.join(RESULTS_DIR, "workflow_visualization.png")
        plt.savefig(viz_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ تم إنشاء التصور البياني: {viz_file}")
        
        return {"visualization_file": viz_file}
        
    except ImportError as e:
        print(f"⚠️  لم يتم تثبيت matplotlib/nx: {e}")
        return {"visualization_file": None, "error": "Missing libraries"}
    except Exception as e:
        print(f"✗ خطأ في إنشاء التصور: {e}")
        return {"visualization_file": None, "error": str(e)}

# ===========================================
# تعريف الـ DAG
# ===========================================

with DAG(
    'ecg_detailed_workflow',
    default_args=default_args,
    description='DAG مفصلة توضح سير العمل الكامل لنظام تشخيص ECG',
    schedule=None,
    start_date=datetime(2026, 2, 6),
    catchup=False,
    tags=['ECG', 'Diagnosis', 'Medical', 'Detailed'],
    doc_md="""
    # DAG مفصلة لنظام تشخيص ECG
    
    ## نظرة عامة
    هذه DAG توضح سير العمل الكامل لنظام تشخيص ECG باستخدام نموذجين مختلفين.
    
    ## مسار العمل
    1. **إعداد البيئة** - إنشاء المجلدات المطلوبة
    2. **استقبال الملفات** - التحقق من الملفات المرفوعة
    3. **تحليل النوع** - تصنيف الملفات حسب الصيغة
    4. **التحقق للنموذج 1** - تحضير الملفات للنموذج الأول
    5. **التحقق للنموذج 2** - تحضير الملفات للنموذج الثاني (EchoNext)
    6. **التنبؤ بالنموذج 1** - تشغيل النموذج الأول
    7. **التنبؤ بالنموذج 2** - تشغيل النموذج الثاني
    8. **دمج النتائج** - دمج تنبؤات الصور المشتركة
    9. **التقرير النهائي** - إنشاء ملخص التنفيذ
    10. **التصور البياني** - إنشاء رسومات توضيحية
    
    ## أنواع الملفات المدعومة
    - **النموذج 1**: CSV, PDF, MAT, صور (JPG, PNG, etc.)
    - **النموذج 2**: XML, صور (JPG, PNG, etc.)
    
    ## المخرجات
    - نتائج التنبؤ لكل نموذج
    - تقرير تنفيذ مفصل
    - رسومات توضيحية لسير العمل
    """
) as dag:
    
    # ===========================================
    # تعريف المهام
    # ===========================================
    
    # المهمة 1: إعداد البيئة
    setup_env_task = PythonOperator(
        task_id='setup_environment',
        python_callable=setup_environment,
    )
    
    # المهمة 2: استقبال الملفات
    receive_files_task = PythonOperator(
        task_id='receive_and_validate_upload',
        python_callable=receive_and_validate_upload,
    )
    
    # المهمة 3: تحليل نوع الملف
    analyze_type_task = PythonOperator(
        task_id='analyze_file_type',
        python_callable=analyze_file_type,
    )
    
    # المهمة 4: التحقق للنموذج 1
    validate_model1_task = PythonOperator(
        task_id='validate_for_model1',
        python_callable=validate_for_model1,
    )
    
    # المهمة 5: التحقق للنموذج 2
    validate_model2_task = PythonOperator(
        task_id='validate_for_model2',
        python_callable=validate_for_model2,
    )
    
    # المهمة 6: التنبؤ بالنموذج 1
    predict_model1_task = PythonOperator(
        task_id='run_model1_predictions',
        python_callable=run_model1_predictions,
    )
    
    # المهمة 7: التنبؤ بالنموذج 2
    predict_model2_task = PythonOperator(
        task_id='run_model2_predictions',
        python_callable=run_model2_predictions,
    )
    
    # المهمة 8: دمج النتائج
    combine_results_task = PythonOperator(
        task_id='combine_predictions_for_images',
        python_callable=combine_predictions_for_images,
    )
    
    # المهمة 9: التقرير النهائي
    final_report_task = PythonOperator(
        task_id='generate_final_report',
        python_callable=generate_final_report,
    )
    
    # المهمة 10: التصور البياني
    visualization_task = PythonOperator(
        task_id='create_visualization',
        python_callable=create_visualization,
    )
    
    # ===========================================
    # تحديد التبعيات بين المهام
    # ===========================================
    
    setup_env_task >> receive_files_task >> analyze_type_task
    
    analyze_type_task >> validate_model1_task
    analyze_type_task >> validate_model2_task
    
    validate_model1_task >> predict_model1_task
    validate_model2_task >> predict_model2_task
    
    predict_model1_task >> combine_results_task
    predict_model2_task >> combine_results_task
    
    combine_results_task >> final_report_task >> visualization_task

# ===========================================
# دالة مساعدة لاختبار DAG محليًا
# ===========================================
def test_dag_locally():
    """دالة لاختبار DAG محليًا بدون Airflow"""
    print("بدء اختبار DAG محليًا...")
    
    # محاكاة context
    class MockTI:
        def xcom_pull(self, task_ids=None, key=None):
            return {}
    
    class MockContext:
        def __init__(self):
            self.ti = MockTI()
            self.execution_date = datetime.now()
            self.run_id = "local_test"
            self.dag = type('obj', (object,), {'dag_id': 'ecg_detailed_workflow'})
    
    context = MockContext()
    
    # اختبار كل وظيفة
    functions = [
        setup_environment,
        receive_and_validate_upload,
        analyze_file_type
    ]
    
    for func in functions:
        try:
            print(f"\nاختبار: {func.__name__}")
            result = func(context)
            print(f"✓ نجاح: {result.get('status', 'OK')}")
        except Exception as e:
            print(f"✗ فشل: {e}")

if __name__ == "__main__":
    test_dag_locally()