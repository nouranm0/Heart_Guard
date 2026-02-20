import joblib
from sklearn.impute import SimpleImputer
from pathlib import Path

def patch_pipeline(file_path):
    print(f"Loading {file_path}...")
    pipeline = joblib.load(file_path)
    
    # Check for SimpleImputer in the pipeline
    patched = False
    if hasattr(pipeline, 'steps'):
        for name, step in pipeline.steps:
            if isinstance(step, SimpleImputer):
                print(f"Found SimpleImputer in step '{name}'")
                if not hasattr(step, 'keep_empty_features'):
                    print("Adding missing 'keep_empty_features' attribute...")
                    step.keep_empty_features = False
                    patched = True
            # Recursively check nested pipelines if any (unlikely here but safe)
            elif hasattr(step, 'steps'):
                for sub_name, sub_step in step.steps:
                    if isinstance(sub_step, SimpleImputer):
                        if not hasattr(sub_step, 'keep_empty_features'):
                            sub_step.keep_empty_features = False
                            patched = True
    
    if patched:
        print(f"Saving patched pipeline to {file_path}...")
        joblib.dump(pipeline, file_path)
        print("Done.")
    else:
        print("No patching needed.")

if __name__ == "__main__":
    joblib_path = Path("models/echonext_multilabel_minimodel/tabular_transformer.joblib")
    patch_pipeline(joblib_path)
