import os
import sys
import traceback
from flask_app.model_inference import predict

# Fix path to allow importing from flask_app
sys.path.append(os.path.join(os.getcwd(), 'flask_app'))

def test_file(filename):
    print(f"Testing {filename}...")
    filepath = os.path.join(os.getcwd(), filename)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    checkpoint_path = os.path.abspath(os.path.join(os.getcwd(), 'models', 'echonext_multilabel_minimodel', 'weights.pt'))
    
    try:
        results = predict(filepath, checkpoint_path)
        print(f"Success! Results: {results}")
    except Exception as e:
        with open("debug_log.txt", "w") as f:
            f.write(f"Failed to process {filename}.\n")
            f.write(f"Error: {str(e)}\n")
            traceback.print_exc(file=f)
        print(f"Failed to process {filename}. See debug_log.txt")

if __name__ == "__main__":
    print("--- Starting Debug ---")
    # Test cases based on available files
    # test_file("Healthy_ECG.xml") # Found to be empty
    test_file("test_normal.jpg")
    # test_file("Test_ECG.pdf") # Skip PDF as we know pdftocairo is missing
    
    # Try an XML from xml_input explicitly
    test_file(os.path.join("xml_input", "MUSE_example.xml"))
