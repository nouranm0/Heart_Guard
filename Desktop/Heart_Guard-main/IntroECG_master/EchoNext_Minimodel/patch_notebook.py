import json
from pathlib import Path

notebook_path = Path("ai_model.ipynb")
script_path = Path("cradlenet/scripts/inference/predict_file.py")

with open(notebook_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Read the full script from disk
with open(script_path, "r", encoding="utf-8") as f:
    full_script_content = f.readlines()

# Ensure the first line is the magic command
if not full_script_content[0].startswith("%%writefile"):
    full_script_content.insert(0, "%%writefile cradlenet/scripts/inference/predict_file.py\n")

# Update Script Generation Cell (Cell 2)
data['cells'][2]['source'] = full_script_content

# Update Upload/Run Cell to handle spaces better and show PDF support in help
for cell in data['cells']:
    if cell['cell_type'] == 'code' and 'files.upload()' in "".join(cell['source']):
        cell['source'] = [
            'from google.colab import files\n',
            'import os\n',
            'uploaded = files.upload()\n',
            'if uploaded:\n',
            '    INPUT_FILE = list(uploaded.keys())[0]\n',
            '    print(f"Selected file: {INPUT_FILE}")\n',
            '    !python "cradlenet/scripts/inference/predict_file.py" \\\n',
            '      --input_file "{INPUT_FILE}" \\\n',
            '      --checkpoint "models/echonext_multilabel_minimodel/weights.pt" \\\n',
            '      --num_classes 12\n',
            'else:\n',
            '    print("No file uploaded.")'
        ]

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Notebook updated with full PDF and Image support.")
