# How to Train Your Custom ECG Validator AI

You can train a custom AI model to recognize your specific type of ECG images and reject everything else.

## 1. Prepare Your Data
Create a folder named `data` in the project root, and inside it create `train` with two subfolders:

```
data/
  train/
    valid/      <-- Put your REAL ECG images/PDFs here (aim for 50+)
    invalid/    <-- Put RANDOM images here (cats, landscapes, screenshots) (aim for 50+)
```

## 2. Run Training
Execute the training script:

```bash
python train_validator.py
```

This will:
1.  Load your images.
2.  Train a MobileNetV2 model to distinguish Valid vs Invalid.
3.  Save the model to `model/custom_validator.h5`.

## 3. Verify
After training, simply restart your API server:

```bash
python api_server.py
```

Pass a file to the validator. You should see logs indicating it is using the **Custom Validator Model**.

## Troubleshooting
- **Not enough data:** If you have fewer than 10 images, training might fail or overfit.
- **Acccuracy:** If the model rejects real ECGs, add those specific "failed" images to the `valid` folder and retrain.
